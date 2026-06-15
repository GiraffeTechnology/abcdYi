from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
def health_check():
    return {"status": "ok", "product": "Giraffe Agent v1.0 Apparel & Textile"}
