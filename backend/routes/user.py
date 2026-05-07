from fastapi import APIRouter, Depends, HTTPException
from backend.auth import get_current_user
from backend.models.db import fetch_topic_profiles, supabase

router = APIRouter()

TEST_USERS = {
    "adarsh": {
        "token": "token_adarsh",
        "id": "user_1",
        "email": "adarsh@test.com"
    },

    "demo": {
        "token": "token_demo",
        "id": "user_2",
        "email": "demo@test.com"
    },

    "admin": {
        "token": "token_admin",
        "id": "admin_1",
        "email": "admin@test.com"
    }
}


@router.get("/test-users")
async def get_test_users():

    return TEST_USERS


@router.post("/test-login/{username}")
async def test_login(username: str):

    user = TEST_USERS.get(username)

    if not user:
        raise HTTPException(404, "User not found")

    return {
        "access_token": user["token"],
        "token_type": "bearer",
        "user": user
    }

@router.get('/me')
async def get_profile(user: dict = Depends(get_current_user)):
    result = supabase.table('users') \
        .select('id, email, full_name, plan, difficulty_profile, role_focus, created_at') \
        .eq('id', user['id']) \
        .single() \
        .execute()
    if not result.data:
        raise HTTPException(404, 'User not found')
    return result.data

@router.patch('/me')
async def update_profile(body: dict, user: dict = Depends(get_current_user)):
    allowed = {'full_name', 'difficulty_profile', 'role_focus'}
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        raise HTTPException(400, 'No valid fields to update')
    supabase.table('users').update(updates).eq('id', user['id']).execute()
    return {'updated': updates}

@router.get('/me/topics')
async def get_topic_profile(user: dict = Depends(get_current_user)):
    '''Weakness/strength breakdown used by the Planner agent.'''
    profiles = await fetch_topic_profiles(user['id'])
    return {
        'weak':   [p for p in profiles if p['avg_score'] < 60],
        'strong': [p for p in profiles if p['avg_score'] >= 75],
        'all':    profiles
    }

@router.get('/me/stats')
async def get_stats(user: dict = Depends(get_current_user)):
    result = supabase.table('interviews') \
        .select('id, status, reports(overall_score, grade)') \
        .eq('user_id', user['id']) \
        .execute()

    rows      = result.data or []
    completed = [r for r in rows if r['status'] == 'completed']
    scores    = [
        r['reports'][0]['overall_score']
        for r in completed
        if r.get('reports') and r['reports'][0].get('overall_score') is not None
    ]

    return {
        'total_interviews':     len(rows),
        'completed_interviews': len(completed),
        'average_score':        round(sum(scores) / len(scores), 1) if scores else None,
        'highest_score':        max(scores, default=None),
        'lowest_score':         min(scores, default=None)
    }
