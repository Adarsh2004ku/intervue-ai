from fastapi import APIRouter, Depends, HTTPException
from backend.auth import get_current_user
from backend.models.db import supabase

router = APIRouter()

ADMIN_EMAILS = {'adarsh@intervue.ai'}  # Add your admin email here

def require_admin(user: dict = Depends(get_current_user)):
    if user['email'] not in ADMIN_EMAILS:
        raise HTTPException(403, 'Admin access required')
    return user

@router.get('/stats')
async def platform_stats(admin = Depends(require_admin)):
    '''Overall platform statistics.'''
    users_count      = supabase.table('users').select('id', count='exact').execute()
    interviews_count = supabase.table('interviews').select('id', count='exact').execute()
    total_tokens     = supabase.table('interviews').select('total_tokens').execute()
    tokens_sum = sum(r['total_tokens'] for r in total_tokens.data or [])
    return {
        'total_users':      users_count.count,
        'total_interviews': interviews_count.count,
        'total_tokens':     tokens_sum,
    }

@router.get('/costs')
async def cost_report(admin = Depends(require_admin)):
    '''AI cost breakdown by model and agent.'''
    result = supabase.table('ai_costs').select('model, agent_name, cost_inr').execute()
    breakdown = {}
    for row in result.data or []:
        key = f"{row['model']} / {row['agent_name']}"
        breakdown[key] = breakdown.get(key, 0) + row['cost_inr']
    return {'cost_breakdown_inr': breakdown,
            'total_inr': sum(breakdown.values())}

@router.delete('/user/{user_id}')
async def delete_user(user_id: str, admin = Depends(require_admin)):
    supabase.table('users').delete().eq('id', user_id).execute()
    return {'deleted': user_id}