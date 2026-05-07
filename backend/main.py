from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Counter, Histogram
from contextlib import asynccontextmanager
from backend.services.cache import get_redis
from backend.routes import resume, interview, user, admin

interviews_started = Counter(
    'intervue_interviews_started_total', 'Interviews started',
    ['mode', 'difficulty'])
llm_tokens_used = Counter(
    'intervue_llm_tokens_total', 'LLM tokens consumed',
    ['model', 'agent'])
answer_score_hist = Histogram(
    'intervue_answer_score', 'Answer score distribution',
    buckets=[10,20,30,40,50,60,70,80,90,100])

@asynccontextmanager
async def lifespan(app: FastAPI):
    r = await get_redis()
    await r.ping()   # Fail fast on startup if Redis unavailable
    yield
    await r.close()

app = FastAPI(title='Intervue.AI API', version='3.0', lifespan=lifespan)
app.add_middleware(CORSMiddleware,
    allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])
Instrumentator().instrument(app).expose(app, endpoint='/metrics')

app.include_router(resume.router,    prefix='/resume')
app.include_router(interview.router, prefix='/interview')
app.include_router(user.router,      prefix='/user')
app.include_router(admin.router,     prefix='/admin')

@app.get('/health')
async def health():
    r = await get_redis()
    await r.ping()
    return {'status': 'ok', 'redis': 'connected'}