import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from api.deps import get_db, get_current_user
from src.participants import service
from src.participants.schemas import (
    ParticipantCreate, ParticipantUpdate, ParticipantOut, RoleAssign, RoleOut
)
from src.roles.constants import validate_role

router = APIRouter()


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ParticipantOut)
async def create_participant(
    data: ParticipantCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    participant = await service.create_participant(
        db, current_user.tenant_id, data, current_user.id
    )
    await db.commit()
    return ParticipantOut.model_validate(participant)


@router.get("", response_model=list[ParticipantOut])
async def list_participants(
    skip: int = 0,
    limit: int = 50,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    participants = await service.list_participants(
        db, current_user.tenant_id, skip, limit
    )
    return [ParticipantOut.model_validate(p) for p in participants]


@router.get("/{participant_id}", response_model=ParticipantOut)
async def get_participant(
    participant_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    participant = await service.get_participant(db, participant_id)
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    return ParticipantOut.model_validate(participant)


@router.patch("/{participant_id}", response_model=ParticipantOut)
async def update_participant(
    participant_id: uuid.UUID,
    data: ParticipantUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    participant = await service.update_participant(
        db, participant_id, data, current_user.id
    )
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    await db.commit()
    return ParticipantOut.model_validate(participant)


@router.post("/{participant_id}/roles", response_model=RoleOut)
async def assign_role(
    participant_id: uuid.UUID,
    data: RoleAssign,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        validate_role(data.role_name)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    role = await service.assign_role(
        db, participant_id, data.role_name, current_user.id
    )
    await db.commit()
    return RoleOut.model_validate(role)


@router.get("/{participant_id}/quality-ledger")
async def get_quality_ledger(
    participant_id: uuid.UUID,
    current_user=Depends(get_current_user),
):
    return {"participant_id": str(participant_id), "records": []}
