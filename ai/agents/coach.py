from backend.services.llm_client import llm_json
from ai.agents.state import InterviewState

async def coach_agent(state: InterviewState) -> InterviewState:
    scores = [e['score'] for e in state['evaluations']]
    overall = sum(scores) // len(scores) if scores else 0

    evals_text = '\n'.join(
        f"Q{i+1}: {state['questions'][i]['question']}\n"
        f"Score: {e['score']} | Feedback: {e['feedback']}"
        for i, e in enumerate(state['evaluations'])
    )

    prompt = f'''
    Interview Complete. Overall score: {overall}/100
    Evaluations: {evals_text}
    Speech metrics summary: {state['speech_metrics']}


    Generate a comprehensive coaching report.

    Rules:
    - Be constructive and actionable.
    - Focus on interview readiness.
    - Identify repeated weak patterns.
    - Highlight strongest technical areas.
    - Suggest practical improvement strategies.
    - Recommend realistic preparation steps.
    - Mention communication quality if relevant.
    - Mention problem-solving quality if relevant.
    - Mention technical depth if relevant.
    - Improvement plans should feel personalized.
    - Resources should include:
    - documentation
    - practice platforms
    - project ideas
    - interview prep resources
    - Week plan should progressively improve readiness.
    - Overall feedback should sound like a senior interviewer.

    Generate a comprehensive improvement plan. Return JSON:

    {{"overall_score": {overall},
    "grade": 'A/B/C/D/F',
    "interview_readiness": 'Ready / Almost Ready / Needs Work',
    "strengths": [str, ...],
    "improvement_areas": [{{"topic": str, "plan": str, "resources": [str]}}],
    "week_plan": {{"week1": str, "week2": str, "week3": str}},
    "overall_feedback": str}}
    ONLY return JSON.'''

    report = await llm_json(prompt)
    state['report'] = report
    return state