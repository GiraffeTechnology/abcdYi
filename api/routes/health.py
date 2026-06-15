from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
def health_check():
    return {"status": "ok", "product": "abcdYi — Giraffe Agent Apparel / Textile / Handicraft Industry Edition"}
