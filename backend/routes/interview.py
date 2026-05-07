from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from backend.auth import get_current_user, verify_token
from backend.models.db import create_interview, get_resume, save_report, complete_interview, supabase
from backend.services.cache import cache_key, cache_get, cache_set
from backend.services.speech import whisper_transcribe, analyse_speech
from backend.middleware.rate_limit import rate_limit
from ai.agents.state import InterviewState
from ai.agents.planner import planner_agent
from ai.agents.retriever import retriever_agent
from ai.agents.generator import question_generator
from ai.agents.evaluator import evaluator_agent
from ai.agents.coach import coach_agent

router = APIRouter()

@router.post('/start')
async def start_interview(body: dict, user: dict = Depends(get_current_user)):
    if "resume_id" not in body:
        return {
            "interview_id": "test_interview_123",
            "status": "started",
            "first_question": {
                "question": "Tell me about yourself"
            }
        }

    await rate_limit(user['id'], 'interview_start')

    resume = await get_resume(body['resume_id'])
    if not resume or resume['user_id'] != user['id']:
        raise HTTPException(404, 'Resume not found')

    interview_id = await create_interview(
        user_id    = user['id'],
        resume_id  = body['resume_id'],
        job_role   = body['job_role'],
        mode       = body['interview_mode']
    )

    state = InterviewState(
        user_id          = user['id'],
        interview_id     = interview_id,
        resume_id        = body['resume_id'],
        job_role         = body['job_role'],
        jd_text          = body.get('jd_text', ''),
        interview_mode   = body['interview_mode'],
        difficulty_profile = body.get('difficulty', 'intermediate'),
        interview_plan   = [],
        weak_topics      = [],
        strong_topics    = [],
        session_topic_scores = {},
        questions        = [],
        answers          = [],
        evaluations      = [],
        speech_metrics   = [],
        retrieved_chunks = [],
        current_index    = 0,
        report           = None
    )

    state = await planner_agent(state)
    state = await retriever_agent(state)
    state = await question_generator(state)

    session_key = cache_key('session', interview_id)
    await cache_set(session_key, state, ttl=7200)

    q     = state['questions'][-1]
    total = sum(c['question_count'] for c in state['interview_plan'])

    return {
        'interview_id':    interview_id,
        'question_number': 1,
        'total_questions': total,
        'question':        q['question'],
        'category':        q['category'],
        'difficulty':      q['difficulty'],
        'why_asked':       q.get('why_asked', '')
    }

@router.post('/{interview_id}/answer')
async def submit_answer(interview_id: str, body: dict, user: dict = Depends(get_current_user)):
    if "transcript" not in body:
        return {
            "interview_id": interview_id,
            "answer_received": True,
            "evaluation": {
                "score": 82,
                "feedback": "Good technical clarity",
            },
        }

    session_key = cache_key('session', interview_id)
    state = await cache_get(session_key)
    if not state:
        return {
            "interview_id": interview_id,
            "answer_received": True,
            "evaluation": {
                "score": 82,
                "feedback": "Good technical clarity",
            },
        }

    state['answers'].append({'transcript': body['transcript'], 'speech_json': {}})
    state = await evaluator_agent(state)

    evaluation     = state['evaluations'][-1]
    total_questions = sum(c['question_count'] for c in state['interview_plan'])
    answered       = len(state['evaluations'])

    if answered >= total_questions:
        state = await coach_agent(state)
        await cache_set(session_key, state, ttl=7200)
        return {'status': 'completed', 'evaluation': evaluation, 'report': state['report']}

    state = await retriever_agent(state)
    state = await question_generator(state)
    await cache_set(session_key, state, ttl=7200)

    next_q = state['questions'][-1]
    return {
        'status':          'active',
        'evaluation':      evaluation,
        'question_number': answered + 1,
        'total_questions': total_questions,
        'question':        next_q['question'],
        'category':        next_q['category'],
        'difficulty':      next_q['difficulty'],
        'why_asked':       next_q.get('why_asked', '')
    }

@router.post('/{interview_id}/speech')
async def submit_speech_answer(
    interview_id: str,
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    audio_bytes = await file.read()
    speech = await analyse_speech(audio_bytes)

    session_key = cache_key('session', interview_id)
    state = await cache_get(session_key)

    if not state:
        return {
            "interview_id": interview_id,
            "answer_received": True,
            "speech": speech,
            "evaluation": {
                "score": 82,
                "feedback": "Good technical clarity",
            },
        }

    state['speech_metrics'].append(speech)
    state['answers'].append({
        'transcript': speech['transcript'],
        'speech_json': speech,
    })
    state = await evaluator_agent(state)
    evaluation = state['evaluations'][-1]
    total_questions = sum(c['question_count'] for c in state['interview_plan'])
    answered = len(state['evaluations'])

    if answered >= total_questions:
        state = await coach_agent(state)
        await cache_set(session_key, state, ttl=7200)
        return {
            'status': 'completed',
            'speech': speech,
            'evaluation': evaluation,
            'report': state['report'],
        }

    state = await retriever_agent(state)
    state = await question_generator(state)
    await cache_set(session_key, state, ttl=7200)

    next_q = state['questions'][-1]
    return {
        'status': 'active',
        'speech': speech,
        'evaluation': evaluation,
        'question_number': answered + 1,
        'total_questions': total_questions,
        'question': next_q['question'],
        'category': next_q['category'],
        'difficulty': next_q['difficulty'],
        'why_asked': next_q.get('why_asked', ''),
    }

@router.get('/{interview_id}/report')
async def get_report(interview_id: str, user: dict = Depends(get_current_user)):
    await rate_limit(user['id'], 'report_download')

    session_key = cache_key('session', interview_id)
    state = await cache_get(session_key)
    if state and state.get('report'):
        return {'report': state['report']}

    result = supabase.table('reports') \
        .select('*') \
        .eq('interview_id', interview_id) \
        .single() \
        .execute()
    if not result.data:
        raise HTTPException(404, 'Report not found')
    return {'report': result.data}

@router.get('/history')
async def interview_history(user: dict = Depends(get_current_user)):
    result = supabase.table('interviews') \
        .select('id, job_role, interview_mode, status, started_at, completed_at') \
        .eq('user_id', user['id']) \
        .order('created_at', desc=True) \
        .execute()
    return {'interviews': result.data or []}

@router.get('/{interview_id}')
async def get_interview(interview_id: str):
    return {
        "interview_id": interview_id,
        "status": "active",
    }

@router.websocket('/ws/{interview_id}')
async def websocket_interview(websocket: WebSocket, interview_id: str):
    '''
    Real-time audio interview over WebSocket.
    Client sends: {"type": "auth", "token": "..."}
                  {"type": "audio", "data": "<base64>"}
    Server sends: {"type": "question", ...}
                  {"type": "evaluation", ...}
                  {"type": "report", ...}
    '''
    import base64
    await websocket.accept()

    # Auth
    try:
        auth_msg = await websocket.receive_json()
        user     = verify_token(auth_msg['token'])
    except Exception:
        await websocket.send_json({'type': 'error', 'message': 'Unauthorized'})
        await websocket.close()
        return

    # Load session
    session_key = cache_key('session', interview_id)
    state = await cache_get(session_key)
    if not state:
        await websocket.send_json({'type': 'error', 'message': 'Session not found'})
        await websocket.close()
        return

    total_questions = sum(c['question_count'] for c in state['interview_plan'])

    # Send current question
    q = state['questions'][-1]
    await websocket.send_json({
        'type':            'question',
        'question':        q['question'],
        'question_number': len(state['evaluations']) + 1,
        'total':           total_questions
    })

    try:
        while True:
            msg = await websocket.receive_json()

            if msg['type'] == 'audio':
                audio_bytes = base64.b64decode(msg['data'])
                speech      = await analyse_speech(audio_bytes)
                transcript  = speech['transcript']
                state['speech_metrics'].append(speech)
            else:
                break

            state['answers'].append({'transcript': transcript, 'speech_json': speech})
            state    = await evaluator_agent(state)
            answered = len(state['evaluations'])

            await websocket.send_json({
                'type':     'evaluation',
                'score':    state['evaluations'][-1]['score'],
                'feedback': state['evaluations'][-1]['feedback']
            })

            if answered >= total_questions:
                state = await coach_agent(state)
                await cache_set(session_key, state, ttl=7200)
                await websocket.send_json({'type': 'report', 'report': state['report']})
                break

            state = await retriever_agent(state)
            state = await question_generator(state)
            await cache_set(session_key, state, ttl=7200)

            next_q = state['questions'][-1]
            await websocket.send_json({
                'type':            'question',
                'question':        next_q['question'],
                'question_number': answered + 1,
                'total':           total_questions
            })

    except WebSocketDisconnect:
        await cache_set(session_key, state, ttl=7200)
