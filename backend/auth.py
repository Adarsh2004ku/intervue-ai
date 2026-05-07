from fastapi import Depends, HTTPException, Header
from supabase import create_client
import os, jwt

supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

async def get_current_user(authorization: str = Header(...)) -> dict:
    try:
        token = authorization.replace('Bearer ', '')
        user  = supabase.auth.get_user(token)
        if not user.user:
            raise HTTPException(401, 'Invalid token')
        return {'id': user.user.id, 'email': user.user.email}
    except Exception:
        raise HTTPException(401, 'Unauthorized')

def verify_token(token: str) -> dict:
    '''Synchronous version for WebSocket connections (no Depends available).'''
    try:
        user = supabase.auth.get_user(token)
        if not user.user:
            raise Exception('invalid')
        return {'id': user.user.id, 'email': user.user.email}
    except Exception:
        raise HTTPException(401, 'Unauthorized')