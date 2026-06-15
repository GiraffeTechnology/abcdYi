import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.db.models.dynamic_form import DynamicOrderForm, DynamicOrderFormVersion, ClarificationQuestion
from src.db.models.project import BuyerInquiry, Project
from src.requirement_extraction.extractor import (
    extract_requirements_from_inquiry,
    detect_missing_fields,
    generate_clarification_questions,
)
from src.field_versions.service import create_version_snapshot
from src.dynamic_forms.constants import REQUIRED_FIELDS
from src.execution_graph.writer import emit_event
from src.execution_graph.event_types import DYNAMIC_FORM_CREATED, DYNAMIC_FORM_UPDATED


async def _get_tenant_id_for_project(db: AsyncSession, project_id: uuid.UUID) -> uuid.UUID | None:
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    return project.tenant_id if project else None


async def create_dynamic_form_from_inquiry(
    db: AsyncSession,
    project_id: uuid.UUID,
    inquiry_id: uuid.UUID,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> DynamicOrderFormVersion:
    result = await db.execute(
        select(BuyerInquiry).where(BuyerInquiry.id == inquiry_id)
    )
    inquiry = result.scalar_one_or_none()
    if not inquiry:
        return None

    try:
        extracted = await extract_requirements_from_inquiry(inquiry.raw_text or "")
    except Exception:
        extracted = {"_ai_generated": True, "_error": True}

    is_stub = extracted.get("_stub", False)
    has_error = extracted.get("_error", False)

    if is_stub or has_error:
        missing = list(REQUIRED_FIELDS)
        clarifications = generate_clarification_questions({}, missing)
        ai_generated = []
    else:
        missing = detect_missing_fields(extracted)
        clarifications = generate_clarification_questions(extracted, missing)
        ai_generated = [
            k for k, v in extracted.items()
            if v is not None and not k.startswith("_")
        ]

    form = DynamicOrderForm(
        project_id=project_id,
        current_version=1,
        is_locked=False,
    )
    db.add(form)
    await db.flush()

    fields_to_store = {k: v for k, v in extracted.items() if not k.startswith("_")}
    fields_to_store["clarification_questions"] = clarifications
    fields_to_store["missing_fields"] = missing

    version = await create_version_snapshot(
        db=db,
        form_id=form.id,
        version_number=1,
        fields=fields_to_store,
        ai_generated_fields=ai_generated,
        human_confirmed_fields=[],
        missing_fields=missing,
        created_by=user_id,
    )

    await emit_event(
        db=db,
        event_type=DYNAMIC_FORM_CREATED,
        payload={
            "form_id": str(form.id),
            "inquiry_id": str(inquiry_id),
            "version": 1,
            "is_stub": is_stub,
        },
        tenant_id=tenant_id,
        project_id=project_id,
        triggered_by_user_id=user_id,
    )
    return version


async def get_current_form(
    db: AsyncSession, project_id: uuid.UUID
) -> DynamicOrderFormVersion | None:
    result = await db.execute(
        select(DynamicOrderForm).where(DynamicOrderForm.project_id == project_id)
    )
    form = result.scalar_one_or_none()
    if not form:
        return None

    ver_result = await db.execute(
        select(DynamicOrderFormVersion)
        .where(DynamicOrderFormVersion.form_id == form.id)
        .order_by(DynamicOrderFormVersion.version_number.desc())
        .limit(1)
    )
    return ver_result.scalar_one_or_none()


async def update_form_fields(
    db: AsyncSession,
    form_id: uuid.UUID,
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    field_updates: dict,
    confirmed_fields: list[str],
) -> DynamicOrderFormVersion:
    result = await db.execute(
        select(DynamicOrderForm).where(DynamicOrderForm.id == form_id)
    )
    form = result.scalar_one_or_none()
    if not form:
        return None
    if form.is_locked:
        raise ValueError("locked")

    ver_result = await db.execute(
        select(DynamicOrderFormVersion)
        .where(DynamicOrderFormVersion.form_id == form_id)
        .order_by(DynamicOrderFormVersion.version_number.desc())
        .limit(1)
    )
    current_version = ver_result.scalar_one_or_none()

    prev_fields = dict(current_version.fields) if current_version else {}
    prev_ai = list(current_version.ai_generated_fields or []) if current_version else []
    prev_human = list(current_version.human_confirmed_fields or []) if current_version else []

    merged_fields = {**prev_fields, **field_updates}

    new_ai = [f for f in prev_ai if f not in confirmed_fields]
    new_human = list(set(prev_human + confirmed_fields))

    missing = detect_missing_fields(merged_fields)
    merged_fields["missing_fields"] = missing

    new_version_number = (current_version.version_number + 1) if current_version else 1

    new_version = await create_version_snapshot(
        db=db,
        form_id=form_id,
        version_number=new_version_number,
        fields=merged_fields,
        ai_generated_fields=new_ai,
        human_confirmed_fields=new_human,
        missing_fields=missing,
        created_by=user_id,
    )

    form.current_version = new_version_number

    await emit_event(
        db=db,
        event_type=DYNAMIC_FORM_UPDATED,
        payload={
            "form_id": str(form_id),
            "version": new_version_number,
            "confirmed_fields": confirmed_fields,
        },
        tenant_id=tenant_id,
        triggered_by_user_id=user_id,
    )
    return new_version


async def lock_form(db: AsyncSession, form_id: uuid.UUID) -> DynamicOrderForm:
    result = await db.execute(
        select(DynamicOrderForm).where(DynamicOrderForm.id == form_id)
    )
    form = result.scalar_one_or_none()
    if form:
        form.is_locked = True
        await db.flush()
    return form


async def get_form_by_id(db: AsyncSession, form_id: uuid.UUID) -> DynamicOrderForm | None:
    result = await db.execute(
        select(DynamicOrderForm).where(DynamicOrderForm.id == form_id)
    )
    return result.scalar_one_or_none()


async def get_form_versions(
    db: AsyncSession, form_id: uuid.UUID
) -> list[DynamicOrderFormVersion]:
    result = await db.execute(
        select(DynamicOrderFormVersion)
        .where(DynamicOrderFormVersion.form_id == form_id)
        .order_by(DynamicOrderFormVersion.version_number.asc())
    )
    return list(result.scalars().all())


async def add_clarification_question(
    db: AsyncSession,
    form_id: uuid.UUID,
    question_text: str,
    field_reference: str | None = None,
) -> ClarificationQuestion:
    result = await db.execute(
        select(DynamicOrderForm).where(DynamicOrderForm.id == form_id)
    )
    form = result.scalar_one_or_none()
    if not form:
        return None
    if form.is_locked:
        raise ValueError("locked")

    question = ClarificationQuestion(
        form_id=form_id,
        question_text=question_text,
        field_reference=field_reference,
    )
    db.add(question)
    await db.flush()
    return question


async def generate_rfq_packet(db: AsyncSession, form_version_id: uuid.UUID) -> dict:
    result = await db.execute(
        select(DynamicOrderFormVersion).where(DynamicOrderFormVersion.id == form_version_id)
    )
    version = result.scalar_one_or_none()
    if not version:
        return {}

    fields = version.fields or {}
    packet = {k: v for k, v in fields.items() if v is not None and not k.startswith("_")}
    risk_items = [f for f in REQUIRED_FIELDS if not fields.get(f)]
    return {"rfq_fields": packet, "risk_items": risk_items}


async def generate_qc_packet(db: AsyncSession, form_version_id: uuid.UUID) -> dict:
    result = await db.execute(
        select(DynamicOrderFormVersion).where(DynamicOrderFormVersion.id == form_version_id)
    )
    version = result.scalar_one_or_none()
    if not version:
        return {}

    qc_keys = ["qc_standard", "fabric_type", "fabric_composition", "size_range",
               "label_requirement", "packaging_requirement"]
    fields = version.fields or {}
    return {k: fields.get(k) for k in qc_keys}
