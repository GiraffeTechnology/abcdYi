import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db, get_current_user
from src.qc.schemas import QCStandardOut, QCRecordCreate, QCRecordOut
from src.qc.service import (
    create_qc_standard, record_qc_result,
    mark_qc_pass, mark_qc_fail, get_qc_records_for_order,
)
from src.merchandiser.qc.qc_reference_store import (
    add_reference_image, get_reference_images, QCReferenceImage,
)
from src.merchandiser.qc.qc_process_card import (
    create_process_card, get_process_card, QCProcessCard,
)
from src.merchandiser.qc.qc_comparison_engine import (
    compare_media_against_standard, QCComparisonReport,
)
from src.merchandiser.qc.qc_result_store import save_qc_report, get_qc_reports_for_project
from src.merchandiser.b_side.b_qc_review import receive_buyer_qc_decision

# NOTE: the /qc/{project_id}/* routes below are an internal MVP surface for the
# file-based (actor/m-side) QC pipeline in src/merchandiser/qc — they intentionally
# have no Depends(get_current_user)/tenant scoping, unlike the DB-backed,
# tenant-scoped /orders/{order_id}/qc-* routes further down this file.
router = APIRouter()


class ReferenceImageListResponse(BaseModel):
    reference_images: list[QCReferenceImage]


class QCReportListResponse(BaseModel):
    reports: list[dict]


class BuyerQCDecisionResponse(BaseModel):
    project_id: str
    milestone_id: str
    buyer_actor_id: str
    decision: str
    notes: str


class AddReferenceImageBody(BaseModel):
    image_path: str
    uploaded_by_actor_id: str
    milestone_type: str | None = None
    description: str | None = None


class CreateProcessCardBody(BaseModel):
    category: str
    material_spec: str | None = None
    color_spec: str | None = None
    size_spec: str | None = None
    finish_spec: str | None = None
    defect_criteria: str | None = None
    supplier_notes: str | None = None
    unit_price: float | None = None
    supplier_contact: str | None = None
    contract_terms: str | None = None


class CompareQCBody(BaseModel):
    production_images: list[str] = Field(default_factory=list)
    standard_images: list[str] | None = None
    milestone_id: str = "MILESTONE-UNSPECIFIED"
    milestone_type: str | None = None
    order_requirements: str | None = None
    process_card_notes: str | None = None
    provider_name: str | None = None
    video_frames: list[str] | None = None


class BuyerQCDecisionBody(BaseModel):
    milestone_id: str
    buyer_actor_id: str
    decision: str
    notes: str = ""


@router.get("/qc/health")
def qc_health():
    return {"status": "ok"}


@router.post("/qc/{project_id}/reference-images", response_model=QCReferenceImage)
def add_reference_image_route(project_id: str, body: AddReferenceImageBody):
    return add_reference_image(
        project_id=project_id,
        image_path=body.image_path,
        uploaded_by_actor_id=body.uploaded_by_actor_id,
        milestone_type=body.milestone_type,
        description=body.description,
    )


@router.get("/qc/{project_id}/reference-images", response_model=ReferenceImageListResponse)
def list_reference_images_route(project_id: str, milestone_type: str | None = None):
    refs = get_reference_images(project_id, milestone_type=milestone_type)
    return ReferenceImageListResponse(reference_images=refs)


@router.post("/qc/{project_id}/process-card", response_model=QCProcessCard)
def create_process_card_route(project_id: str, body: CreateProcessCardBody):
    return create_process_card(project_id=project_id, **body.model_dump())


@router.get("/qc/{project_id}/process-card", response_model=QCProcessCard)
def get_process_card_route(project_id: str):
    card = get_process_card(project_id)
    if card is None:
        raise HTTPException(status_code=404, detail="No process card found for this project")
    return card


@router.post("/qc/{project_id}/compare", response_model=QCComparisonReport)
def compare_qc_route(project_id: str, body: CompareQCBody):
    report = compare_media_against_standard(
        project_id=project_id,
        milestone_id=body.milestone_id,
        production_images=body.production_images,
        standard_images=body.standard_images,
        milestone_type=body.milestone_type,
        order_requirements=body.order_requirements,
        process_card_notes=body.process_card_notes,
        provider_name=body.provider_name,
        video_frames=body.video_frames,
    )
    save_qc_report(report, project_id=project_id, milestone_id=body.milestone_id)
    return report


@router.get("/qc/{project_id}/reports", response_model=QCReportListResponse)
def list_qc_reports_route(project_id: str):
    return QCReportListResponse(reports=get_qc_reports_for_project(project_id))


@router.post("/qc/{project_id}/buyer-decision", response_model=BuyerQCDecisionResponse)
def buyer_qc_decision_route(project_id: str, body: BuyerQCDecisionBody):
    return receive_buyer_qc_decision(
        project_id=project_id,
        milestone_id=body.milestone_id,
        buyer_actor_id=body.buyer_actor_id,
        decision=body.decision,
        notes=body.notes,
    )


class QCStandardCreateBody(BaseModel):
    form_version_id: uuid.UUID


class MarkFailBody(BaseModel):
    responsible_participant_id: uuid.UUID


@router.post("/orders/{order_id}/qc-standards", status_code=status.HTTP_201_CREATED, response_model=QCStandardOut)
async def create_qc_standard_route(
    order_id: uuid.UUID,
    body: QCStandardCreateBody,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    std = await create_qc_standard(
        db=db,
        order_id=order_id,
        form_version_id=body.form_version_id,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
    )
    await db.commit()
    await db.refresh(std)
    return std


@router.post("/orders/{order_id}/qc-records", status_code=status.HTTP_201_CREATED)
async def record_qc(
    order_id: uuid.UUID,
    body: QCRecordCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    record = await record_qc_result(
        db=db,
        order_id=order_id,
        qc_data=body.model_dump(),
        inspector_participant_id=body.inspector_participant_id,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
    )
    await db.commit()
    await db.refresh(record)
    return QCRecordOut.model_validate(record)


@router.get("/orders/{order_id}/qc-records", response_model=list[QCRecordOut])
async def list_qc_records(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await get_qc_records_for_order(db, order_id)


@router.post("/qc-records/{qc_record_id}/mark-pass", response_model=QCRecordOut)
async def mark_pass(
    qc_record_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    record = await mark_qc_pass(db, qc_record_id, current_user.id)
    await db.commit()
    await db.refresh(record)
    return record


@router.post("/qc-records/{qc_record_id}/mark-fail", response_model=QCRecordOut)
async def mark_fail(
    qc_record_id: uuid.UUID,
    body: MarkFailBody,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    record = await mark_qc_fail(db, qc_record_id, body.responsible_participant_id, current_user.id)
    await db.commit()
    await db.refresh(record)
    return record
