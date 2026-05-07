from fastapi import APIRouter

from backend.services.cache import get_redis

router = APIRouter()


@router.get("/")
async def health():
    r = await get_redis()
    await r.ping()

    return {
        "status": "ok",
        "redis": "connected",
    }


@router.get("/ready")
async def readiness_check():
    return {
        "ready": True,
    }


@router.get("/live")
async def liveness_check():
    return {
        "alive": True,
    }
