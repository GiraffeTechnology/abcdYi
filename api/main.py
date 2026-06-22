from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes.health import router as health_router
from api.routes.auth import router as auth_router
from api.routes.participants import router as participants_router
from api.routes.projects import router as projects_router
from api.routes.dynamic_forms import router as dynamic_forms_router
from api.routes.approval_gates import router as approval_gates_router
from api.routes.matching import router as matching_router
from api.routes.rfq import router as rfq_router
from api.routes.supplier_responses import router as supplier_responses_router
from api.routes.decision_packets import router as decision_packets_router
from api.routes.orders import router as orders_router
from api.routes.milestones import router as milestones_router
from api.routes.qc import router as qc_router
from api.routes.logistics import router as logistics_router
from api.routes.execution_graph import router as execution_graph_router
from api.routes.role_switching import router as role_switching_router
from api.routes.giraffe_jp_service_nodes import router as giraffe_jp_service_nodes_router
from api.routes.giraffe_jp_message_permissions import router as giraffe_jp_message_permissions_router
from api.routes.giraffe_jp_conversations import router as giraffe_jp_conversations_router
from api.routes.giraffe_jp_formalwear import router as giraffe_jp_formalwear_router
from src.actors.role_resolver import resolve_role_context
from src.m_side.dependencies.dependency_planner import plan_upstream_dependencies
from src.m_side.rollup.supplier_response_rollup import generate_supplier_response_rollup
from src.m_side.bridge.submit_rollup_to_b_side import submit_rollup_to_b_side

app = FastAPI(
    title="abcdYi — Giraffe Agent Apparel / Textile / Handicraft Industry Edition",
    version="1.0.0",
    description="Multi-party supply-chain coordination for apparel, textiles, and handicraft-based custom production.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(participants_router, prefix="/api/participants", tags=["participants"])
app.include_router(projects_router, prefix="/api/projects", tags=["projects"])
app.include_router(dynamic_forms_router, prefix="/api", tags=["dynamic_forms"])
app.include_router(approval_gates_router, prefix="/api", tags=["approval_gates"])
app.include_router(matching_router, prefix="/api", tags=["matching"])
app.include_router(rfq_router, prefix="/api", tags=["rfq"])
app.include_router(supplier_responses_router, prefix="/api", tags=["supplier_responses"])
app.include_router(decision_packets_router, prefix="/api", tags=["decision_packets"])
app.include_router(orders_router, prefix="/api", tags=["orders"])
app.include_router(milestones_router, prefix="/api", tags=["milestones"])
app.include_router(qc_router, prefix="/api", tags=["qc"])
app.include_router(logistics_router, prefix="/api", tags=["logistics"])
app.include_router(execution_graph_router, prefix="/api", tags=["execution_graph"])
app.include_router(role_switching_router)
app.include_router(giraffe_jp_service_nodes_router, prefix="/api/giraffe-jp", tags=["giraffe_jp_service_core"])
app.include_router(giraffe_jp_message_permissions_router, prefix="/api/giraffe-jp", tags=["giraffe_jp_message_permissions"])
app.include_router(giraffe_jp_conversations_router, prefix="/api/giraffe-jp", tags=["giraffe_jp_conversations"])
app.include_router(giraffe_jp_formalwear_router, prefix="/api/giraffe-jp", tags=["giraffe_jp_formalwear"])

# The role-switching pipeline stages reachable at /api/role-switching/run-upstream-pipeline.
ROLE_SWITCHING_PIPELINE_STAGES = [
    resolve_role_context.__name__,
    plan_upstream_dependencies.__name__,
    generate_supplier_response_rollup.__name__,
    submit_rollup_to_b_side.__name__,
]


@app.get("/api/role-switching/pipeline-stages", tags=["role-switching"])
def get_role_switching_pipeline_stages() -> dict:
    return {"stages": ROLE_SWITCHING_PIPELINE_STAGES}
