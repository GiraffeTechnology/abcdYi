"""Owner-managed project membership without tenant-wide role impersonation."""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from api.deps import get_current_user, get_db
from src.db.models import Project, User, Participant, ProjectMembership
from src.execution_graph.writer import emit_event
from src.permissions.project_access import bind_request_actor, INTERNAL_ROLES, EXTERNAL_ROLES

router = APIRouter(dependencies=[Depends(bind_request_actor)])


class MembershipWrite(BaseModel):
    model_config = ConfigDict(extra='forbid')
    user_id: uuid.UUID
    role: str
    participant_id: uuid.UUID | None = None


async def owner(db, project_id, actor):
    project = await db.get(Project, project_id)
    user = await db.get(User, actor.id)
    if project is None or project.tenant_id != actor.tenant_id:
        raise HTTPException(status_code=404, detail='Project not found')
    if project.created_by != actor.id and not user.is_platform_admin:
        raise HTTPException(status_code=403, detail='Only the project owner or tenant administrator may assign access')
    return project


@router.post('/projects/{project_id}/memberships')
async def assign_membership(project_id: uuid.UUID, body: MembershipWrite, db=Depends(get_db), actor=Depends(get_current_user)):
    await owner(db, project_id, actor)
    target = await db.get(User, body.user_id)
    if target is None or not target.is_active or target.tenant_id != actor.tenant_id:
        raise HTTPException(status_code=404, detail='User not found')
    role = body.role.upper()
    if role not in INTERNAL_ROLES | EXTERNAL_ROLES:
        raise HTTPException(status_code=422, detail='Unsupported project role')
    if role in EXTERNAL_ROLES and body.participant_id is None:
        raise HTTPException(status_code=422, detail='Execution collaborator requires a participant identity')
    if body.participant_id:
        participant = await db.get(Participant, body.participant_id)
        if participant is None or participant.tenant_id != actor.tenant_id:
            raise HTTPException(status_code=404, detail='Participant not found')
    grant = await db.scalar(select(ProjectMembership).where(ProjectMembership.project_id==project_id, ProjectMembership.user_id==body.user_id).with_for_update())
    before = {'role':grant.role,'revoked':bool(grant.revoked_at)} if grant else None
    if grant is None:
        grant=ProjectMembership(project_id=project_id,user_id=body.user_id,granted_by=actor.id,role=role)
        db.add(grant)
    grant.role=role;grant.participant_id=body.participant_id;grant.revoked_at=None;grant.granted_by=actor.id
    await emit_event(db,'PROJECT_ACCESS_ASSIGNED',{'user_id':str(body.user_id),'role':role,'participant_id':str(body.participant_id) if body.participant_id else None,'previous':before},tenant_id=actor.tenant_id,project_id=project_id,triggered_by_user_id=actor.id)
    await db.commit()
    return {'project_id':str(project_id),'user_id':str(body.user_id),'role':role,'active':True}


@router.delete('/projects/{project_id}/memberships/{user_id}')
async def revoke_membership(project_id: uuid.UUID,user_id: uuid.UUID,db=Depends(get_db),actor=Depends(get_current_user)):
    await owner(db,project_id,actor)
    grant=await db.scalar(select(ProjectMembership).where(ProjectMembership.project_id==project_id,ProjectMembership.user_id==user_id).with_for_update())
    if grant is None:raise HTTPException(status_code=404,detail='Membership not found')
    grant.revoked_at=datetime.now(timezone.utc)
    await emit_event(db,'PROJECT_ACCESS_REVOKED',{'user_id':str(user_id),'role':grant.role},tenant_id=actor.tenant_id,project_id=project_id,triggered_by_user_id=actor.id)
    await db.commit()
    return {'project_id':str(project_id),'user_id':str(user_id),'active':False}
