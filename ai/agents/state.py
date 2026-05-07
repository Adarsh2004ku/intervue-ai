from typing import TypedDict, List, Optional


class InterviewState(TypedDict):

    # Identity
    user_id: str
    interview_id: str
    resume_id: str

    # Job
    job_role: str
    jd_text: str

    # Config
    interview_mode: str
    difficulty_profile: str

    # Planning
    interview_plan: List[dict]
    weak_topics: List[str]
    strong_topics: List[str]
    session_topic_scores: dict

    # Conversation
    questions: List[dict]
    answers: List[dict]
    evaluations: List[dict]
    speech_metrics: List[dict]
    retrieved_chunks: List[dict]

    current_index: int

    # Final output
    report: Optional[dict]