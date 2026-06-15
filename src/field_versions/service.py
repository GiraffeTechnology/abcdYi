import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.models.dynamic_form import DynamicOrderFormVersion


async def create_version_snapshot(
    db: AsyncSession,
    form_id: uuid.UUID,
    version_number: int,
    fields: dict,
    ai_generated_fields: list,
    human_confirmed_fields: list,
    missing_fields: list,
    created_by: uuid.UUID | None = None,
) -> DynamicOrderFormVersion:
    """Create an immutable version snapshot."""
    version = DynamicOrderFormVersion(
        form_id=form_id,
        version_number=version_number,
        fields=fields,
        ai_generated_fields=ai_generated_fields,
        human_confirmed_fields=human_confirmed_fields,
        missing_fields=missing_fields,
        created_by=created_by,
    )
    db.add(version)
    await db.flush()
    return version
