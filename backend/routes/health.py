from fastapi import APIRouter, HTTPException
from backend.services.cache import get_redis

router = APIRouter()


@router.get("/")
async def health():
    """Full health check — verifies Redis is reachable."""
    try:
        r = await get_redis()
        await r.ping()
        redis_status = "connected"
    except Exception as e:
        redis_status = f"error: {str(e)}"

    return {
        "status": "ok" if redis_status == "connected" else "degraded",
        "redis":  redis_status,
    }


@router.get("/ready")
async def readiness_check():
    """Readiness probe — returns 503 if Redis is down."""
    try:
        r = await get_redis()
        await r.ping()
    except Exception as e:
        raise HTTPException(503, f"Not ready — Redis unavailable: {str(e)}")
    return {"ready": True}


@router.get("/live")
async def liveness_check():
    """Liveness probe — returns 200 as long as the process is alive."""
    return {"alive": True}