from ai.personas.interviewer_personas import PERSONAS
from backend.services.llm_client import llm_json

async def question_generator(state : InterviewState) -> InterviewState:
    idx = state['current_index']
    plan = state['interview_plan'][idx]
    persona = PERSONAS[state['interview_mode']]
    chunks = state['retrieved_chunks']
    context = '\n'.join(c['chunk_text'] for c in chunks)
    
    last_score = None
    if last_score:
        last_score = state['evaluations'][-1].get('score')
    
    prompt = f'''
    You are {persona['name']}: {persona['style']}
    Question style: {persona['question_style']}
    Topic: {plan['category']} | Difficulty: {plan['difficulty']}
    Is weak area: {plan['category'] in state['weak_topics']}
    Last answer score: {last_score} (adapt difficulty if needed)

    Candidate resume context: {context}
    Instructions:

    - Ask ONLY one interview question.
    - Question should feel realistic and conversational.
    - Prefer practical and job-relevant questions.
    - If previous answer score was low:
    - slightly reduce complexity
    - ask more guiding questions
    - If previous answer score was high:
    - increase depth and difficulty
    - If topic is a weak area:
    - probe deeper conceptually
    - test fundamentals carefully
    - Include follow-up style wording naturally.
    - Avoid textbook-style wording.
    - Keep question concise but challenging.
    - Prefer FAANG-style practical questioning.
    - Use resume context whenever relevant.


    Return ONLY valid JSON in this format:

    {{
    "question": str,
    "why_asked": str,
    "is_weakness_focused": bool,
    "expected_keywords": list
    }}

    ONLY return JSON.
    '''

    q = await llm_json(prompt)
    q['category']  = plan['category']
    q['difficulty'] = plan['difficulty']
    state['questions'].append(q)
    return state