from fastapi import APIRouter

router = APIRouter()


@router.get("/summary")
async def metrics_summary():
    """Returns the location of the Prometheus metrics endpoint."""
    return {
        "prometheus": "/metrics",
        "status":     "enabled",
    }