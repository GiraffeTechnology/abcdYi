import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.qc import QCStandard
from src.db.models.dynamic_form import DynamicOrderFormVersion
from src.execution_graph.writer import emit_event
from src.execution_graph.event_types import QC_STANDARD_CREATED


async def create_qc_standard_from_form(
    db: AsyncSession,
    order_id: uuid.UUID,
    form_version_id: uuid.UUID,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> QCStandard:
    """Extract QC parameters from locked form version."""
    version = await db.get(DynamicOrderFormVersion, form_version_id)
    fields = version.fields if version else {}

    qc_standard_text = fields.get("qc_standard", "")
    fabric_composition = fields.get("fabric_composition", "")
    size_range = fields.get("size_range", "")
    label_req = fields.get("label_requirement", "")
    packaging_req = fields.get("packaging_requirement", "")
    washing_req = fields.get("washing_mark_requirement", "")

    std = QCStandard(
        order_id=order_id,
        measurement_tolerance={"default_mm": 5, "notes": qc_standard_text},
        fabric_defect_limits={"pin_holes": 2, "broken_stitch": 2, "notes": fabric_composition},
        stitching_standards={"stitches_per_inch": 12},
        color_difference_tolerance={"delta_e": 2.0},
        size_deviation_limits={"chest": 1.0, "waist": 1.0, "notes": size_range},
        washing_requirements={"instructions": washing_req or "Follow care label"},
        label_requirements={"required": True, "notes": label_req or "Standard label required"},
        packaging_requirements={"notes": packaging_req or "Standard carton packaging"},
        compliance_notes=f"Auto-extracted from form version {form_version_id}",
    )
    db.add(std)
    await db.flush()

    await emit_event(
        db=db,
        event_type=QC_STANDARD_CREATED,
        payload={"qc_standard_id": str(std.id), "order_id": str(order_id)},
        tenant_id=tenant_id,
        order_id=order_id,
        triggered_by_user_id=user_id,
    )
    return std
