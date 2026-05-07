from backend.models.db import fetch_topic_profiles
from backend.services.llm_client import llm_json

async def planner_agent(State : InterviewState) -> InterviewState:

    profiles = await fetch_topic_profiles(state['user_id'])

    #split into weak (score <75) and strong score>75

    weak = [p['topic'] for p in profiles if p['avg_score'] < 75]
    strong = [p['topic'] for p in profiles if p['avg_score'] >=75]

    prompt = f"""
    user_weak_topics : {weak}
    user_strong_topics : {strong}
    Interview_mode : {state['interview_mode']}
    job_role : {state['job_role']}

    Create an adaptive interview plan.

    Rules:

    - Focus on evaluating real-world job readiness.
    - 60% questions should target weak topics (if available).
    - 25% questions should cover important untested concepts related to the job role.
    - 15% questions should validate strong topics.
    - Total interview should contain 8-10 questions.
    - Questions should progressively increase in difficulty.
    - Include conceptual, practical, debugging, and scenario-based questions.
    - Avoid repeating the same topic too frequently.
    - Prioritize technologies relevant to the job role.
    - Questions should simulate real technical interviews.
    - Difficulty values must only be:
    - easy
    - medium
    - hard

    Return JSON: {{"plan": [{{"category": str,
    "question_count": int, "difficulty": str}}]}}
    ONLY return JSON.
    """

    plan_json = await llm_json(prompt)
    state['interview_plan'] = plan_json['plan']
    state['weak_topics'] = weak
    state['current_index'] = 0
    state['session_topic_score'] = {}

    return state