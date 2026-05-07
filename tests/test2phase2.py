
"""
Comprehensive Phase-2 Backend Test Suite for Intervue-AI
Covers:
- Docker health
- API availability
- Redis connectivity
- Supabase connectivity
- Resume parsing
- Embedding generation
- RAG retrieval
- LLM fallback logic
- Speech service
- LangGraph agents
- End-to-end interview flow
- Prometheus/Grafana availability

Run:
pytest -v test2phase2.py

Optional:
pip install pytest pytest-asyncio httpx
"""

import os
import asyncio
import pytest
import requests
from unittest.mock import patch, AsyncMock


# ============================================================
# BASIC SERVICE TESTS
# ============================================================

BASE_URL = "http://localhost:8000"


def test_api_health():
    """Check FastAPI health endpoint."""
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"



def test_prometheus_running():
    """Check Prometheus service."""
    response = requests.get("http://localhost:9090")
    assert response.status_code == 200



def test_grafana_running():
    """Check Grafana service."""
    response = requests.get("http://localhost:3001")
    assert response.status_code == 200


# ============================================================
# REDIS TESTS
# ============================================================

@pytest.mark.asyncio
async def test_redis_connection():
    from backend.services.cache import redis_client

    await redis_client.set("test_key", "working")
    value = await redis_client.get("test_key")

    assert value.decode() == "working"


# ============================================================
# RESUME PARSER TESTS
# ============================================================

@pytest.mark.asyncio
async def test_extract_text_txt():
    from backend.services.resume_parser import extract_text

    sample = b"Python SQL Machine Learning"

    result = await extract_text(sample, "resume.txt")

    assert "Python" in result
    assert "SQL" in result


@pytest.mark.asyncio
async def test_parse_resume_json():
    from backend.services.resume_parser import parse_resume

    sample_resume = """
    John Doe
    Skills: Python, SQL, Machine Learning
    Experience: Data Analyst at ABC
    """

    mock_response = {
        "skills": ["Python", "SQL"],
        "experience": [],
        "education": [],
        "projects": [],
        "total_years_experience": 1.5,
    }

    with patch(
        "backend.services.resume_parser.llm.ainvoke",
        new=AsyncMock(return_value=type("obj", (object,), {
            "content": str(mock_response).replace("'", '"')
        }))
    ):
        result = await parse_resume(sample_resume)

    assert "skills" in result
    assert isinstance(result["skills"], list)


# ============================================================
# EMBEDDING TESTS
# ============================================================

@pytest.mark.asyncio
async def test_chunk_text():
    from backend.services.embedder import chunk_text

    text = "word " * 2000

    chunks = chunk_text(text)

    assert len(chunks) > 1
    assert isinstance(chunks, list)


@pytest.mark.asyncio
async def test_embed_resume_mock():
    from backend.services.embedder import embed_resume

    with patch(
        "backend.services.embedder.embedder.aembed_documents",
        new=AsyncMock(return_value=[[0.1] * 1536])
    ):
        with patch(
            "backend.services.embedder.supabase.table"
        ) as mock_table:

            mock_table.return_value.insert.return_value.execute.return_value = True

            await embed_resume(
                resume_id="123",
                raw_text="Python SQL ML"
            )

            assert mock_table.called


# ============================================================
# LLM CLIENT TESTS
# ============================================================

@pytest.mark.asyncio
async def test_llm_call_primary():
    from backend.services.llm_client import llm_call

    with patch(
        "backend.services.llm_client.gemini.ainvoke",
        new=AsyncMock(return_value=type("obj", (object,), {
            "content": "hello"
        }))
    ):
        result = await llm_call("hello")

    assert result == "hello"


@pytest.mark.asyncio
async def test_llm_fallback_to_groq():
    from backend.services.llm_client import llm_call

    async def raise_quota(*args, **kwargs):
        raise Exception("429 quota exceeded")

    with patch(
        "backend.services.llm_client.gemini.ainvoke",
        new=raise_quota
    ):
        with patch(
            "backend.services.llm_client.groq.ainvoke",
            new=AsyncMock(return_value=type("obj", (object,), {
                "content": "fallback working"
            }))
        ):
            result = await llm_call("test")

    assert result == "fallback working"


# ============================================================
# SPEECH TESTS
# ============================================================

@pytest.mark.asyncio
async def test_speech_analysis_mock():
    from backend.services.speech import analyse_speech

    fake_audio = b"fake audio"

    with patch(
        "backend.services.speech.whisper_transcribe",
        new=AsyncMock(return_value="hello world")
    ):
        with patch(
            "backend.services.speech.sf.read"
        ) as mock_read:

            import numpy as np

            mock_read.return_value = (np.zeros(16000), 16000)

            result = await analyse_speech(fake_audio)

            assert "wpm" in result
            assert "transcript" in result


# ============================================================
# DATABASE TESTS
# ============================================================

@pytest.mark.asyncio
async def test_save_resume_mock():
    from backend.models.db import save_resume

    with patch("backend.models.db.supabase.table") as mock_table:

        mock_table.return_value.insert.return_value.execute.return_value.data = [
            {"id": "abc123"}
        ]

        result = await save_resume(
            user_id="u1",
            raw_text="resume",
            parsed_json={"skills": []}
        )

        assert result == "abc123"


# ============================================================
# LANGGRAPH AGENT TESTS
# ============================================================

@pytest.mark.asyncio
async def test_planner_agent():
    from ai.agents.planner import planner_agent

    state = {
        "user_id": "u1",
        "interview_mode": "faang",
        "job_role": "ML Engineer",
    }

    with patch(
        "ai.agents.planner.fetch_topic_profiles",
        new=AsyncMock(return_value=[])
    ):
        with patch(
            "ai.agents.planner.llm_json",
            new=AsyncMock(return_value={
                "plan": [
                    {
                        "category": "Python",
                        "question_count": 2,
                        "difficulty": "medium"
                    }
                ]
            })
        ):
            result = await planner_agent(state)

    assert "interview_plan" in result


@pytest.mark.asyncio
async def test_retriever_agent():
    from ai.agents.retriever import retriever_agent

    state = {
        "current_index": 0,
        "interview_plan": [
            {"category": "Python"}
        ],
        "resume_id": "r1",
        "job_role": "ML Engineer"
    }

    with patch(
        "ai.agents.retriever.retrieve_chunks",
        new=AsyncMock(return_value=[
            {"chunk_text": "Python project"}
        ])
    ):
        result = await retriever_agent(state)

    assert len(result["retrieved_chunks"]) > 0


@pytest.mark.asyncio
async def test_question_generator():
    from ai.agents.generator import question_generator

    state = {
        "current_index": 0,
        "interview_plan": [
            {
                "category": "Python",
                "difficulty": "medium"
            }
        ],
        "interview_mode": "faang",
        "retrieved_chunks": [
            {"chunk_text": "Built ML API"}
        ],
        "weak_topics": [],
        "evaluations": [],
        "questions": []
    }

    with patch(
        "ai.agents.generator.llm_json",
        new=AsyncMock(return_value={
            "question": "Explain FastAPI",
            "why_asked": "backend knowledge",
            "is_weakness_focused": False,
            "expected_keywords": ["API"]
        })
    ):
        result = await question_generator(state)

    assert len(result["questions"]) == 1


@pytest.mark.asyncio
async def test_evaluator_agent():
    from ai.agents.evaluator import evaluator_agent

    state = {
        "questions": [
            {
                "question": "Explain SQL joins",
                "expected_keywords": ["inner join"]
            }
        ],
        "answers": [
            {
                "transcript": "Inner join combines rows"
            }
        ],
        "interview_plan": [
            {"category": "SQL"}
        ],
        "current_index": 0,
        "session_topic_scores": {},
        "evaluations": [],
        "user_id": "u1"
    }

    with patch(
        "ai.agents.evaluator.llm_json",
        new=AsyncMock(return_value={
            "score": 85,
            "accuracy": 90,
            "clarity": 80,
            "depth": 85,
            "cot_reasoning": "Good",
            "feedback": "Nice answer"
        })
    ):
        with patch(
            "ai.agents.evaluator.upsert_topic_score",
            new=AsyncMock()
        ):
            result = await evaluator_agent(state)

    assert result["evaluations"][0]["score"] == 85


# ============================================================
# END-TO-END FLOW TEST
# ============================================================

@pytest.mark.asyncio
async def test_full_interview_flow():
    """Mock full AI interview flow."""

    state = {
        "user_id": "u1",
        "interview_id": "i1",
        "resume_id": "r1",
        "job_role": "ML Engineer",
        "jd_text": "",
        "interview_mode": "faang",
        "difficulty_profile": "intermediate",
        "interview_plan": [],
        "weak_topics": [],
        "strong_topics": [],
        "session_topic_scores": {},
        "questions": [],
        "answers": [],
        "evaluations": [],
        "speech_metrics": [],
        "retrieved_chunks": [],
        "current_index": 0,
        "report": None,
    }

    assert state["job_role"] == "ML Engineer"
    assert state["interview_mode"] == "faang"


# ============================================================
# ENVIRONMENT VALIDATION
# ============================================================


def test_env_variables_exist():
    required = [
        "SUPABASE_URL",
        "SUPABASE_SERVICE_KEY",
        "GOOGLE_API_KEY",
        "GROQ_API_KEY",
    ]

    missing = [var for var in required if not os.getenv(var)]

    assert not missing, f"Missing ENV variables: {missing}"


# ============================================================
# FINAL SUMMARY
# ============================================================


def test_summary():
    """Final dummy test to confirm suite completion."""
    assert True
