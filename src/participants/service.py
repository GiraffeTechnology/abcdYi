import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.db.models.participant import Participant, ParticipantRole, ParticipantProfile
from src.participants.schemas import ParticipantCreate, ParticipantUpdate
from src.roles.constants import validate_role
from src.execution_graph.writer import emit_event
from src.execution_graph.event_types import PARTICIPANT_REGISTERED, DYNAMIC_FORM_UPDATED


async def calculate_completeness_score(db: AsyncSession, participant: Participant) -> float:
    score = 0.0
    if participant.name:
        score += 0.2
    if participant.contact_email:
        score += 0.2
    if participant.country:
        score += 0.1

    result = await db.execute(
        select(ParticipantProfile).where(
            ParticipantProfile.participant_id == participant.id
        )
    )
    profile = result.scalar_one_or_none()
    if profile:
        score += 0.2
        if profile.product_categories:
            score += 0.1
        if profile.fabric_capabilities:
            score += 0.1
        if profile.moq:
            score += 0.05
        if profile.certifications:
            score += 0.05

    return min(score, 1.0)


async def create_participant(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    data: ParticipantCreate,
    created_by_user_id: uuid.UUID,
) -> Participant:
    participant = Participant(
        tenant_id=tenant_id,
        name=data.name,
        company_registration=data.company_registration,
        country=data.country,
        contact_email=str(data.contact_email) if data.contact_email else None,
        contact_phone=data.contact_phone,
    )
    db.add(participant)
    await db.flush()

    score = await calculate_completeness_score(db, participant)
    participant.profile_completeness_score = score

    await emit_event(
        db=db,
        event_type=PARTICIPANT_REGISTERED,
        payload={"name": participant.name, "tenant_id": str(tenant_id)},
        tenant_id=tenant_id,
        participant_id=participant.id,
        triggered_by_user_id=created_by_user_id,
    )
    return participant


async def get_participant(db: AsyncSession, participant_id: uuid.UUID) -> Participant | None:
    result = await db.execute(
        select(Participant).where(Participant.id == participant_id)
    )
    return result.scalar_one_or_none()


async def list_participants(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    skip: int = 0,
    limit: int = 50,
) -> list[Participant]:
    result = await db.execute(
        select(Participant)
        .where(Participant.tenant_id == tenant_id)
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def update_participant(
    db: AsyncSession,
    participant_id: uuid.UUID,
    data: ParticipantUpdate,
    updated_by_user_id: uuid.UUID,
) -> Participant:
    result = await db.execute(
        select(Participant).where(Participant.id == participant_id)
    )
    participant = result.scalar_one_or_none()
    if not participant:
        return None

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(participant, field, value)

    score = await calculate_completeness_score(db, participant)
    participant.profile_completeness_score = score
    await db.flush()

    await emit_event(
        db=db,
        event_type=DYNAMIC_FORM_UPDATED,
        payload={"participant_id": str(participant_id), "updates": data.model_dump(exclude_none=True)},
        tenant_id=participant.tenant_id,
        participant_id=participant.id,
        triggered_by_user_id=updated_by_user_id,
    )
    return participant


async def assign_role(
    db: AsyncSession,
    participant_id: uuid.UUID,
    role_name: str,
    assigned_by_user_id: uuid.UUID,
) -> ParticipantRole:
    validate_role(role_name)
    role = ParticipantRole(
        participant_id=participant_id,
        role_name=role_name,
    )
    db.add(role)
    await db.flush()
    return role
