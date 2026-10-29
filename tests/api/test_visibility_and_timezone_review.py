"""Synthetic regressions for authorized pagination and milestone UTC comparison."""
import uuid
from datetime import datetime, timezone, timedelta

import pytest
from sqlalchemy import select
from src.db.models import Project, ProjectMembership, User, Tenant, Milestone
from src.milestones.service import update_milestone
from src.projects.service import list_projects
from tests.api.test_provider_order_handoff import handoff, import_order


async def test_project_pagination_applies_to_visible_rows(handoff):
    client, _, sessions, owner, _ = handoff
    other = uuid.uuid4()
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    async with sessions() as db:
        db.add(User(id=other, tenant_id=owner.tenant_id, email=f'{other}@example.invalid', hashed_password='synthetic'))
        await db.flush()
        hidden = [Project(tenant_id=owner.tenant_id, title=f'Hidden {i}', created_by=other, created_at=now + timedelta(seconds=i)) for i in range(55)]
        owned = Project(tenant_id=owner.tenant_id, title='Owned', created_by=owner.id, created_at=now + timedelta(seconds=60))
        shared = Project(tenant_id=owner.tenant_id, title='Shared', created_by=other, created_at=now + timedelta(seconds=61))
        db.add_all(hidden + [owned, shared]); await db.flush()
        db.add_all([
            ProjectMembership(project_id=shared.id, user_id=owner.id, role='BUYER', granted_by=other),
            ProjectMembership(project_id=hidden[0].id, user_id=owner.id, role='BUYER', granted_by=other, revoked_at=now),
            ProjectMembership(project_id=hidden[1].id, user_id=owner.id, role='MANUFACTURER', granted_by=other),
        ])
        await db.commit()
    response = await client.get('/api/projects')
    assert response.status_code == 200, response.text
    assert [p['title'] for p in response.json()] == ['Owned', 'Shared']
    assert [p['title'] for p in (await client.get('/api/projects?skip=1&limit=1')).json()] == ['Shared']
    assert (await client.get('/api/projects?skip=2&limit=1')).json() == []


async def test_project_list_admin_stays_tenant_bound_and_inactive_denied(handoff):
    _, _, sessions, owner, _ = handoff
    foreign_tenant = uuid.uuid4()
    async with sessions() as db:
        db.add(Tenant(id=foreign_tenant, name='Foreign', slug=str(foreign_tenant)))
        await db.flush()
        db.add_all([Project(tenant_id=owner.tenant_id, title='Local', created_by=None), Project(tenant_id=foreign_tenant, title='Foreign', created_by=None)])
        user = await db.get(User, owner.id); user.is_platform_admin = True
        await db.commit()
        db.info.update(request_actor_id=owner.id, request_path='/api/projects', request_method='GET')
        assert [p.title for p in await list_projects(db, owner.tenant_id)] == ['Local']
        assert await list_projects(db, foreign_tenant) == []
        user.is_active = False; await db.flush()
        assert await list_projects(db, owner.tenant_id) == []


@pytest.mark.parametrize('prediction,expected', [
    ('2026-10-29T11:00:00+08:00', 'PENDING'),
    ('2026-10-29T09:00:00-08:00', 'DELAYED'),
    ('2026-10-29T18:00:00+08:00', 'PENDING'),
    ('2026-10-29T10:01:00', 'DELAYED'),
])
async def test_milestone_compares_instants_not_offset_wall_times(handoff, prediction, expected):
    client, _, sessions, owner, _ = handoff
    response = await import_order(client); assert response.status_code == 200
    oid = uuid.UUID(response.json()['id'])
    async with sessions() as db:
        milestone = await db.scalar(select(Milestone).where(Milestone.order_id == oid))
        milestone.planned_date = datetime(2026, 10, 29, 10, 0, tzinfo=timezone.utc)
        milestone.status = 'PENDING'; await db.commit()
        await db.refresh(milestone)
        result = await update_milestone(db, milestone.id, predicted_date=datetime.fromisoformat(prediction), tenant_id=owner.tenant_id, updated_by_user_id=owner.id)
        assert result.status == expected
        await db.commit(); await db.refresh(result)
        assert result.status == expected
