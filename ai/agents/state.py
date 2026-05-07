from typing import TypedDict,List,Optional

class InterviewState(TypedDict):

    # Session identity
    user_id : str
    interview_id : str
    resume_id : str
    job_role : str
    jb_text : str


    # Config
    interview_mode : str #faang | startur | hr 
    difficulty_profile : str # begineer | intermediate | adavanced



    # pllaning
    interview_plan : List[dict]
    weak_topics : List[str]
    strong_topics : List[str]
    session_topic_score : dict



    # conversation
    questions : List[dict]
    answers :  List[dict]
    evaluations : List[dict]
    speech_metrics : List[dict]
    retrived_chunks : List[dict]
    current_index :  List[dict]

    report : Optional[dict]



