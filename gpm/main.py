from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from gpm.api import router as gpm_router

app = FastAPI(
    title="Giraffe Pricing Model (GPM)",
    version="1.0.0",
    description=(
        "Internal pricing intelligence service. "
        "Provides process benchmarks, price deviation classification, "
        "and a buffer for incoming order data from abcdyi."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(gpm_router, prefix="/gpm/v1")


@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"status": "ok", "service": "gpm"}
