import redis.asyncio as aioredis
import json ,hashlib,os
from typing import Optional,Any
from dotenv import load_dotenv


load_dotenv()

_redis_client = None

async def get_redis() -> aioredis.Redis:
    """
    Returns singleton Redis Client. Creates connection on first call
    """
    global _redis_client
    if not _redis_client:
        _redis_client = aioredis.from_url(
            os.getenv('REDIS_URL','redis://localhost:6379'),
            encoding = 'utf-8',
            decode_responses = True
        )
    
    return _redis_client


async def cache_get(key:str) -> Optional[Any]:
    r = await get_redis()
    val = await r.get(key)
    return json.loads(val) if val else None

async def cache_set(key:str,value : Any,ttl :int = 3600):
    r = await get_redis()
    await r.setex(key, ttl, json.dumps(value, default=str))
 
async def cache_delete(key: str):
    r = await get_redis()
    await r.delete(key)


def make_key(prefix: str, *args) -> str:
    raw = ':'.join(str(a) for a in args)
    hsh = hashlib.sha256(raw.encode()).hexdigest()[:16]
    return f'{prefix}:{hsh}'
