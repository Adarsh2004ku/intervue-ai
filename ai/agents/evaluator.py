from backend.services.llm_client import llm_json
from ai.agents.state import InterviewState

async def evaluator_agent(state : InterviewState) -> InterviewState:
    q = state['questions'][-1]
    a = state['answers'][-1]

    prompt = f"""
    Question: {q['question']}

    Expected keywords: {q.get('expected_keywords', [])}

    Candidate answer: {a['transcript']}

    Evaluate the candidate answer.
    Score on 3 dimensions (0-100 each):
    1. Accuracy
    - Is the answer technically correct?
    2. Clarity
    - Is the answer structured and easy to understand?
    3. Depth
    - Does the answer include reasoning, trade-offs, examples, edge cases, or practical insight?

    Evaluation Rules:

    - Penalize vague or generic answers.
    - Reward practical examples and real-world thinking.
    - Reward structured explanations.
    - Reward strong debugging/system thinking.
    - Penalize hallucinated or incorrect technical claims.
    - Keep feedback constructive and interview-focused.
    - Overall score should reflect combined performance.

    Return JSON: {{"score": overall_0_100, "accuracy": int,
    "clarity": int, "depth": int, "cot_reasoning": str,
    "feedback": str}}
    ONLY return JSON.
    """

    eval_result = await llm_json(prompt)
    topic = state['interview_plan']
    state['session_topic_scores'][topic] = eval_result['category']
    state['evaluations'].append(eval_result)
    state['current_index'] +=1
