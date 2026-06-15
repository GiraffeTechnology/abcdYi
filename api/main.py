from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes.health import router as health_router
from api.routes.auth import router as auth_router
from api.routes.participants import router as participants_router
from api.routes.projects import router as projects_router
from api.routes.dynamic_forms import router as dynamic_forms_router

app = FastAPI(
    title="Giraffe Agent v1.0 — Apparel & Textile Industry Edition",
    version="1.0.0",
    description="Production-usable C2M apparel & textile order execution platform.",
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
