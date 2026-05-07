from fastapi import Depends, HTTPException, Header
from supabase import create_client
from dotenv import load_dotenv
import os, jwt

load_dotenv()

_SUPABASE_URL = os.getenv("SUPABASE_URL")
_SUPABASE_KEY = os.getenv("SUPABASE_KEY")
if not _SUPABASE_URL or not _SUPABASE_KEY:
    raise RuntimeError(
        "Missing Supabase env vars. Set SUPABASE_URL and SUPABASE_KEY "
        "(for local dev, create a .env file in the repo root)."
    )

supabase = create_client(_SUPABASE_URL, _SUPABASE_KEY)

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