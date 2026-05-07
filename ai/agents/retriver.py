from backend.services.embedder import retrieve_chunks

async def retriever_agent(state: InterviewState) -> InterviewState:
    idx  = state['current_index']
    plan = state['interview_plan']
    if idx >= len(plan):
        return state

    topic = plan[idx]['category']
    chunks = await retrieve_chunks(
        resume_id=state['resume_id'],
        query=f'{topic} {state["job_role"]}',
        top_k=5
    )
    state['retrieved_chunks'] = chunks
    return state