from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from backend.auth import get_current_user, verify_token
from backend.models.db import create_interview, get_resume, complete_interview, supabase
from backend.services.cache import cache_key, cache_get, cache_set
from backend.services.speech import analyse_speech
from backend.middleware.rate_limit import rate_limit
from ai.agents.state import InterviewState
from ai.agents.planner import planner_agent
from ai.agents.retriever import retriever_agent
from ai.agents.generator import question_generator
from ai.agents.evaluator import evaluator_agent
from ai.agents.coach import coach_agent

router = APIRouter()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _total_questions(state: dict) -> int:
    return sum(c["question_count"] for c in state["interview_plan"])


def _answered(state: dict) -> int:
    return len(state["evaluations"])


def _next_question(state: dict) -> dict:
    return state["questions"][-1]


async def _load_state(interview_id: str) -> dict:
    """Load session from cache or raise 404."""
    state = await cache_get(cache_key("session", interview_id))
    if not state:
        raise HTTPException(
            404,
            "Interview session not found or expired. Please start a new interview.",
        )
    return state


async def _save_state(interview_id: str, state: dict, ttl: int = 7200) -> None:
    await cache_set(cache_key("session", interview_id), state, ttl=ttl)


def _guard_evaluations(state: dict) -> None:
    """Ensure evaluator_agent actually appended a result."""
    if len(state["evaluations"]) < len(state["answers"]):
        raise HTTPException(500, "Evaluator failed to produce a result. Please retry.")


# ---------------------------------------------------------------------------
# POST /start
# ---------------------------------------------------------------------------

@router.post("/start")
async def start_interview(body: dict, user: dict = Depends(get_current_user)):
    # Dev shortcut — no resume_id needed
    if "resume_id" not in body:
        return {
            "interview_id": "test_interview_123",
            "status": "started",
            "first_question": {"question": "Tell me about yourself"},
        }

    await rate_limit(user["id"], "interview_start")

    for field in ("resume_id", "job_role", "interview_mode"):
        if field not in body:
            raise HTTPException(400, f"Missing required field: {field}")

    resume = await get_resume(body["resume_id"])
    if not resume or resume["user_id"] != user["id"]:
        raise HTTPException(404, "Resume not found")

    interview_id = await create_interview(
        user_id=user["id"],
        resume_id=body["resume_id"],
        job_role=body["job_role"],
        mode=body["interview_mode"],
    )

    state = InterviewState(
        user_id=user["id"],
        interview_id=interview_id,
        resume_id=body["resume_id"],
        job_role=body["job_role"],
        jd_text=body.get("jd_text", ""),
        interview_mode=body["interview_mode"],
        difficulty_profile=body.get("difficulty", "intermediate"),
        interview_plan=[],
        weak_topics=[],
        strong_topics=[],
        session_topic_scores={},
        questions=[],
        answers=[],
        evaluations=[],
        speech_metrics=[],
        retrieved_chunks=[],
        current_index=0,
        report=None,
    )

    state = await planner_agent(state)
    state = await retriever_agent(state)
    state = await question_generator(state)

    if not state.get("questions"):
        raise HTTPException(500, "Question generator returned no questions.")

    await _save_state(interview_id, state)

    q = _next_question(state)
    total = _total_questions(state)

    return {
        "interview_id":    interview_id,
        "question_number": 1,
        "total_questions": total,
        "question":        q["question"],
        "category":        q["category"],
        "difficulty":      q["difficulty"],
        "why_asked":       q.get("why_asked", ""),
    }


# ---------------------------------------------------------------------------
# GET /history  — MUST be before /{interview_id} to avoid route shadowing
# ---------------------------------------------------------------------------

@router.get("/history")
async def interview_history(user: dict = Depends(get_current_user)):
    result = (
        supabase.table("interviews")
        .select("id, job_role, interview_mode, status, started_at, completed_at")
        .eq("user_id", user["id"])
        .order("created_at", desc=True)
        .execute()
    )
    return {"interviews": result.data or []}


# ---------------------------------------------------------------------------
# POST /{interview_id}/answer
# ---------------------------------------------------------------------------

@router.post("/{interview_id}/answer")
async def submit_answer(
    interview_id: str, body: dict, user: dict = Depends(get_current_user)
):
    if "transcript" not in body:
        raise HTTPException(400, "Missing required field: transcript")

    state = await _load_state(interview_id)

    state["answers"].append({"transcript": body["transcript"], "speech_json": {}})
    state = await evaluator_agent(state)
    _guard_evaluations(state)

    evaluation = state["evaluations"][-1]
    total      = _total_questions(state)
    answered   = _answered(state)
    state["current_index"] = answered

    if answered >= total:
        state = await coach_agent(state)
        await _save_state(interview_id, state)
        await complete_interview(interview_id)
        return {"status": "completed", "evaluation": evaluation, "report": state["report"]}

    state = await retriever_agent(state)
    state = await question_generator(state)
    await _save_state(interview_id, state)

    next_q = _next_question(state)
    return {
        "status":          "active",
        "evaluation":      evaluation,
        "question_number": answered + 1,
        "total_questions": total,
        "question":        next_q["question"],
        "category":        next_q["category"],
        "difficulty":      next_q["difficulty"],
        "why_asked":       next_q.get("why_asked", ""),
    }


# ---------------------------------------------------------------------------
# POST /{interview_id}/speech
# ---------------------------------------------------------------------------

@router.post("/{interview_id}/speech")
async def submit_speech_answer(
    interview_id: str,
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(400, "Uploaded audio file is empty.")

    speech = await analyse_speech(audio_bytes)
    if not speech.get("transcript"):
        raise HTTPException(422, "Could not transcribe audio. Please try again.")

    state = await _load_state(interview_id)

    state["speech_metrics"].append(speech)
    state["answers"].append({"transcript": speech["transcript"], "speech_json": speech})
    state = await evaluator_agent(state)
    _guard_evaluations(state)

    evaluation = state["evaluations"][-1]
    total      = _total_questions(state)
    answered   = _answered(state)
    state["current_index"] = answered

    if answered >= total:
        state = await coach_agent(state)
        await _save_state(interview_id, state)
        await complete_interview(interview_id)
        return {
            "status":     "completed",
            "speech":     speech,
            "evaluation": evaluation,
            "report":     state["report"],
        }

    state = await retriever_agent(state)
    state = await question_generator(state)
    await _save_state(interview_id, state)

    next_q = _next_question(state)
    return {
        "status":          "active",
        "speech":          speech,
        "evaluation":      evaluation,
        "question_number": answered + 1,
        "total_questions": total,
        "question":        next_q["question"],
        "category":        next_q["category"],
        "difficulty":      next_q["difficulty"],
        "why_asked":       next_q.get("why_asked", ""),
    }


# ---------------------------------------------------------------------------
# GET /{interview_id}/report
# ---------------------------------------------------------------------------

@router.get("/{interview_id}/report")
async def get_report(interview_id: str, user: dict = Depends(get_current_user)):
    await rate_limit(user["id"], "report_download")

    state = await cache_get(cache_key("session", interview_id))
    if state and state.get("report"):
        return {"report": state["report"]}

    result = (
        supabase.table("reports")
        .select("*")
        .eq("interview_id", interview_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(404, "Report not found. The interview may not be completed yet.")
    return {"report": result.data}


# ---------------------------------------------------------------------------
# GET /{interview_id}  — MUST be after all static routes
# ---------------------------------------------------------------------------

@router.get("/{interview_id}")
async def get_interview(interview_id: str, user: dict = Depends(get_current_user)):
    result = (
        supabase.table("interviews")
        .select("id, job_role, interview_mode, status, started_at, completed_at")
        .eq("id", interview_id)
        .eq("user_id", user["id"])
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(404, "Interview not found.")
    return result.data