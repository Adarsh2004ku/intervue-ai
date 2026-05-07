from fastapi import APIRouter

router = APIRouter()


@router.get("/summary")
async def metrics_summary():
    return {
        "prometheus": "/metrics",
        "status": "enabled",
    }
