from fastapi import HTTPException
from backend.services.cache import get_redis

LIMITS = {
    'interview_start': (5,  3600),
    'resume_upload':   (10, 3600),
    'report_download': (20, 3600),
}

async def rate_limit(user_id: str, action: str):
    limit, window = LIMITS.get(action, (100, 60))
    r   = await get_redis()
    key = f'ratelimit:{action}:{user_id}'
    count = await r.incr(key)
    if count == 1:
        await r.expire(key, window)
    if count > limit:
        raise HTTPException(429, f'Rate limit: {limit} {action} per {window}s')