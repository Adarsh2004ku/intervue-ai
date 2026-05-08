from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.services.cache import get_redis
from backend.models.db import supabase

router = APIRouter()


@router.get("/")
async def testing_home():
    return {"message": "testing routes working"}


@router.get("/ping")
async def ping():
    return {"status": "ok"}


@router.get("/llm")
async def test_llm():
    return {"message": "LLM route working"}


@router.get("/redis")
async def test_redis():
    try:
        r = await get_redis()
        await r.ping()
        return {"redis": "connected"}
    except Exception as e:
        return {"redis": "error", "detail": str(e)}


@router.get("/supabase")
async def test_supabase():
    if supabase is None:
        return {"supabase": "not configured"}
    try:
        supabase.table("users").select("id").limit(1).execute()
        return {"supabase": "connected"}
    except Exception as e:
        return {"supabase": "error", "detail": str(e)}


@router.websocket("/ws")
async def websocket_test(ws: WebSocket):
    """Echo WebSocket — sends back whatever text it receives."""
    await ws.accept()
    try:
        while True:
            data = await ws.receive_text()
            await ws.send_json({"received": data, "status": "working"})
    except WebSocketDisconnect:
        return