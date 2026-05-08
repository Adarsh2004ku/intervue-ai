import base64

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.auth import verify_token
from backend.models.db import complete_interview
from backend.services.cache import cache_key, cache_get, cache_set
from backend.services.speech import analyse_speech
from ai.agents.evaluator import evaluator_agent
from ai.agents.retriever import retriever_agent
from ai.agents.generator import question_generator
from ai.agents.coach import coach_agent

router = APIRouter()


def _total_questions(state: dict) -> int:
    return sum(c["question_count"] for c in state["interview_plan"])


def _answered(state: dict) -> int:
    return len(state["evaluations"])


def _next_question(state: dict) -> dict:
    return state["questions"][-1]


@router.websocket("/ws/{interview_id}")
async def websocket_interview(websocket: WebSocket, interview_id: str):
    """
    Real-time audio interview over WebSocket.

    Client sends:
        {"type": "auth",  "token": "..."}
        {"type": "audio", "data": "<base64-encoded audio bytes>"}
        {"type": "end"}

    Server sends:
        {"type": "question",   "question": ..., "question_number": ..., "total": ...}
        {"type": "evaluation", "score": ..., "feedback": ...}
        {"type": "report",     "report": ...}
        {"type": "error",      "message": ...}
    """
    await websocket.accept()

    # --- Authentication ---
    try:
        auth_msg = await websocket.receive_json()
        user = verify_token(auth_msg["token"])
    except Exception:
        await websocket.send_json({"type": "error", "message": "Unauthorized"})
        await websocket.close()
        return

    # --- Load session ---
    session_key = cache_key("session", interview_id)
    state = await cache_get(session_key)
    if not state:
        await websocket.send_json({"type": "error", "message": "Session not found or expired."})
        await websocket.close()
        return

    total = _total_questions(state)

    # Send the current question immediately on connect
    q = _next_question(state)
    await websocket.send_json({
        "type":            "question",
        "question":        q["question"],
        "question_number": _answered(state) + 1,
        "total":           total,
    })

    try:
        while True:
            msg = await websocket.receive_json()

            if msg["type"] == "end":
                break

            if msg["type"] != "audio":
                await websocket.send_json({
                    "type":    "error",
                    "message": f"Unknown message type: {msg['type']}",
                })
                continue

            # --- Transcribe audio ---
            try:
                audio_bytes = base64.b64decode(msg["data"])
                speech      = await analyse_speech(audio_bytes)
            except Exception as e:
                await websocket.send_json({"type": "error", "message": f"Audio processing failed: {e}"})
                continue

            if not speech.get("transcript"):
                await websocket.send_json({"type": "error", "message": "Could not transcribe audio. Please retry."})
                continue

            # --- Append answer and evaluate ---
            state["speech_metrics"].append(speech)
            state["answers"].append({"transcript": speech["transcript"], "speech_json": speech})
            state = await evaluator_agent(state)

            # Guard: evaluator must have appended a result
            if len(state["evaluations"]) < len(state["answers"]):
                await websocket.send_json({"type": "error", "message": "Evaluation failed. Please retry."})
                # Roll back unevaluated entries to keep state consistent
                state["answers"].pop()
                state["speech_metrics"].pop()
                continue

            answered = _answered(state)
            state["current_index"] = answered

            await websocket.send_json({
                "type":     "evaluation",
                "score":    state["evaluations"][-1]["score"],
                "feedback": state["evaluations"][-1]["feedback"],
            })

            # --- Check if interview is complete ---
            if answered >= total:
                state = await coach_agent(state)
                await cache_set(session_key, state, ttl=7200)
                await complete_interview(interview_id)
                await websocket.send_json({"type": "report", "report": state["report"]})
                break

            # --- Generate next question ---
            state = await retriever_agent(state)
            state = await question_generator(state)
            await cache_set(session_key, state, ttl=7200)

            next_q = _next_question(state)
            await websocket.send_json({
                "type":            "question",
                "question":        next_q["question"],
                "question_number": answered + 1,
                "total":           total,
            })

    except WebSocketDisconnect:
        # Trim unevaluated answers before saving to keep answers/evaluations in sync
        eval_count              = _answered(state)
        state["answers"]        = state["answers"][:eval_count]
        state["speech_metrics"] = state["speech_metrics"][:eval_count]
        state["current_index"]  = eval_count
        await cache_set(session_key, state, ttl=7200)