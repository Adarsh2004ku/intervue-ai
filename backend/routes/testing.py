from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def testing_home():
    return {
        "message": "testing routes working",
    }


@router.get("/ping")
async def ping():
    return {
        "status": "ok",
    }


@router.get("/llm")
async def test_llm():
    return {
        "message": "LLM route working",
    }


@router.get("/redis")
async def test_redis():
    return {
        "message": "Redis route working",
    }


@router.get("/supabase")
async def test_supabase():
    return {
        "message": "Supabase route working",
    }
