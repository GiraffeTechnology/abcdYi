from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes.health import router as health_router

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

# Remaining routers registered in later iterations
