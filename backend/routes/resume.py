from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from backend.auth import get_current_user
from backend.models.db import get_resume, save_resume, supabase
from backend.services.resume_parser import extract_text, parse_resume

router = APIRouter()

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
}


# ---------------------------------------------------------------------------
# POST /upload
# ---------------------------------------------------------------------------

@router.post("/upload")
async def upload_resume(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            415,
            f"Unsupported file type: {file.content_type}. Upload a PDF, DOCX, or TXT file.",
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(400, "Uploaded file is empty.")

    try:
        raw_text = await extract_text(file_bytes, file.filename or "")
        if not raw_text or not raw_text.strip():
            raise ValueError("No text extracted from file.")
        parsed    = await parse_resume(raw_text)
        resume_id = await save_resume(user["id"], raw_text, parsed)
    except HTTPException:
        raise
    except Exception as e:
        print(f"[resume/upload] Error for user {user['id']}: {e}")
        raise HTTPException(422, "Failed to process resume. Ensure the file is not password-protected or corrupted.")

    return {"resume_id": resume_id, "parsed_resume": parsed}


# ---------------------------------------------------------------------------
# GET /  — MUST be before /{resume_id} to avoid route shadowing
# ---------------------------------------------------------------------------

@router.get("/")
async def list_resumes(user: dict = Depends(get_current_user)):
    result = (
        supabase.table("resumes")
        .select("id, created_at, parsed_json")
        .eq("user_id", user["id"])
        .execute()
    )
    return {"resumes": result.data or []}


# ---------------------------------------------------------------------------
# GET /{resume_id}
# ---------------------------------------------------------------------------

@router.get("/{resume_id}")
async def get_resume_detail(resume_id: str, user: dict = Depends(get_current_user)):
    resume = await get_resume(resume_id)
    if not resume:
        raise HTTPException(404, "Resume not found.")
    if resume["user_id"] != user["id"]:
        raise HTTPException(403, "Access denied.")
    return resume


# ---------------------------------------------------------------------------
# DELETE /{resume_id}
# ---------------------------------------------------------------------------

@router.delete("/{resume_id}")
async def delete_resume(resume_id: str, user: dict = Depends(get_current_user)):
    resume = await get_resume(resume_id)
    if not resume:
        raise HTTPException(404, "Resume not found.")
    if resume["user_id"] != user["id"]:
        raise HTTPException(403, "Access denied.")
    supabase.table("resumes").delete().eq("id", resume_id).execute()
    return {"deleted": resume_id}