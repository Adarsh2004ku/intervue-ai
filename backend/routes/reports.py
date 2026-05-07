from fastapi import APIRouter

router = APIRouter()


@router.get("/{interview_id}")
async def get_report(interview_id: str):
    return {
        "interview_id": interview_id,
        "overall_score": 85,
        "grade": "A",
        "strengths": [
            "Problem Solving",
            "ML Fundamentals",
        ],
        "weaknesses": [
            "System Design",
        ],
    }
