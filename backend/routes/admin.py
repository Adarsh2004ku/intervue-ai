from fastapi import APIRouter, Depends, HTTPException
from backend.auth import get_current_user
from backend.models.db import supabase

router = APIRouter()

ADMIN_EMAILS = {"adarsh@intervue.ai", "adarsh@test.com", "admin@test.com"}


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user.get("email") not in ADMIN_EMAILS:
        raise HTTPException(403, "Admin access required")
    return user


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/health")
async def admin_health():
    return {"server": "healthy"}


@router.get("/stats")
async def platform_stats(admin: dict = Depends(require_admin)):
    if supabase is None:
        return {"users": 10, "interviews": 55, "reports": 40}

    users_count      = supabase.table("users").select("id", count="exact").execute()
    interviews_count = supabase.table("interviews").select("id", count="exact").execute()
    tokens_res       = supabase.table("interviews").select("total_tokens").execute()
    tokens_sum       = sum(r["total_tokens"] or 0 for r in tokens_res.data or [])

    return {
        "total_users":      users_count.count,
        "total_interviews": interviews_count.count,
        "total_tokens":     tokens_sum,
    }


@router.get("/costs")
async def cost_report(admin: dict = Depends(require_admin)):
    if supabase is None:
        raise HTTPException(503, "Database not available")

    result = supabase.table("ai_costs").select("model, agent_name, cost_inr").execute()
    breakdown: dict = {}
    for row in result.data or []:
        key = f"{row['model']} / {row['agent_name']}"
        breakdown[key] = breakdown.get(key, 0.0) + (row["cost_inr"] or 0.0)

    return {
        "cost_breakdown_inr": breakdown,
        "total_inr":          round(sum(breakdown.values()), 4),
    }


@router.delete("/user/{user_id}")
async def delete_user(user_id: str, admin: dict = Depends(require_admin)):
    if supabase is None:
        raise HTTPException(503, "Database not available")

    check = supabase.table("users").select("id").eq("id", user_id).single().execute()
    if not check.data:
        raise HTTPException(404, f"User '{user_id}' not found")

    supabase.table("users").delete().eq("id", user_id).execute()
    return {"deleted": user_id}