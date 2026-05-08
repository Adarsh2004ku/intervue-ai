from fastapi import APIRouter, Depends, HTTPException
from backend.auth import get_current_user
from backend.models.db import supabase
from backend.services.cache import cache_key, cache_get

router = APIRouter()


@router.get("/{interview_id}")
async def get_report(interview_id: str, user: dict = Depends(get_current_user)):
    """
    Fetch the final report for a completed interview.
    Checks the cache first, falls back to the database.
    """
    # Cache check
    state = await cache_get(cache_key("session", interview_id))
    if state and state.get("report"):
        if state.get("user_id") and state["user_id"] != user["id"]:
            raise HTTPException(403, "Access denied.")
        return {"report": state["report"]}

    # DB fallback
    result = (
        supabase.table("reports")
        .select("*")
        .eq("interview_id", interview_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(404, "Report not found. The interview may not be completed yet.")

    # Ownership check
    interview = (
        supabase.table("interviews")
        .select("user_id")
        .eq("id", interview_id)
        .single()
        .execute()
    )
    if interview.data and interview.data["user_id"] != user["id"]:
        raise HTTPException(403, "Access denied.")

    return result.data