import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.db.models.giraffe_jp import GiraffeJPFormalwearOrderProfile, GiraffeJPC2B2MRoleEdge
from src.execution_graph.writer import emit_event
from src.execution_graph import event_types

FORMALWEAR_CATEGORIES = frozenset({
    "FORMAL_DRESS", "WOMENS_SUIT", "BRIDALWEAR", "LIGHT_WEDDING_DRESS", "RECEPTION_DRESS",
})

# These categories require hollow-to-hem measurement by default.
HOLLOW_TO_HEM_REQUIRED_CATEGORIES = frozenset({
    "BRIDALWEAR", "LIGHT_WEDDING_DRESS", "FORMAL_DRESS",
})

# Default C2B2M role edges for every formalwear project.
DEFAULT_C2B2M_EDGES: list[dict] = [
    {"role_from": "CUSTOMER", "role_to": "SERVICE_PLATFORM", "edge_label": "customer_to_platform"},
    {"role_from": "SERVICE_PLATFORM", "role_to": "PRODUCTION_PARTNER", "edge_label": "platform_to_production"},
    {"role_from": "SERVICE_PLATFORM", "role_to": "LOCAL_MODEL_PARTNER", "edge_label": "platform_to_local_model"},
    {"role_from": "PRODUCTION_PARTNER", "role_to": "QUALITY_REVIEWER", "edge_label": "production_to_qc"},
]


async def create_formalwear_profile(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    garment_category: str,
    hollow_to_hem_cm: float | None = None,
    model_try_on_required: bool = True,
    local_alteration_possible: bool = True,
    custom_measurements: dict | None = None,
    triggered_by_user_id: uuid.UUID | None = None,
) -> GiraffeJPFormalwearOrderProfile:
    hollow_to_hem_required = garment_category in HOLLOW_TO_HEM_REQUIRED_CATEGORIES

    profile = GiraffeJPFormalwearOrderProfile(
        tenant_id=tenant_id,
        project_id=project_id,
        garment_category=garment_category,
        hollow_to_hem_cm=hollow_to_hem_cm,
        hollow_to_hem_required=hollow_to_hem_required,
        model_try_on_required=model_try_on_required,
        local_alteration_possible=local_alteration_possible,
        custom_measurements=custom_measurements,
    )
    db.add(profile)
    await db.flush()
    await emit_event(
        db,
        event_type=event_types.FORMALWEAR_ORDER_PROFILE_CREATED,
        payload={
            "profile_id": str(profile.id),
            "garment_category": garment_category,
            "hollow_to_hem_required": hollow_to_hem_required,
        },
        tenant_id=tenant_id,
        project_id=project_id,
        triggered_by_user_id=triggered_by_user_id,
    )
    return profile


async def initialize_default_c2b2m_edges_for_project(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    triggered_by_user_id: uuid.UUID | None = None,
) -> list[GiraffeJPC2B2MRoleEdge]:
    result = await db.execute(
        select(GiraffeJPC2B2MRoleEdge).where(
            GiraffeJPC2B2MRoleEdge.tenant_id == tenant_id,
            GiraffeJPC2B2MRoleEdge.project_id == project_id,
        )
    )
    existing_keys = {(e.role_from, e.role_to) for e in result.scalars().all()}

    created: list[GiraffeJPC2B2MRoleEdge] = []
    for edge_def in DEFAULT_C2B2M_EDGES:
        key = (edge_def["role_from"], edge_def["role_to"])
        if key not in existing_keys:
            edge = GiraffeJPC2B2MRoleEdge(
                tenant_id=tenant_id,
                project_id=project_id,
                role_from=edge_def["role_from"],
                role_to=edge_def["role_to"],
                edge_label=edge_def["edge_label"],
            )
            db.add(edge)
            created.append(edge)
            await emit_event(
                db,
                event_type=event_types.C2B2M_ROLE_EDGE_CREATED,
                payload={
                    "role_from": edge_def["role_from"],
                    "role_to": edge_def["role_to"],
                    "edge_label": edge_def["edge_label"],
                },
                tenant_id=tenant_id,
                project_id=project_id,
                triggered_by_user_id=triggered_by_user_id,
            )

    await db.flush()
    await emit_event(
        db,
        event_type=event_types.C2B2M_DEFAULT_EDGES_INITIALIZED,
        payload={"project_id": str(project_id), "edges_created": len(created)},
        tenant_id=tenant_id,
        project_id=project_id,
        triggered_by_user_id=triggered_by_user_id,
    )
    return created
