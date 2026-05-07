from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from backend.auth import get_current_user
from backend.models.db import save_resume, get_resume, supabase
from backend.services.resume_parser import extract_text, parse_resume
from backend.services.embedder import embed_resume
from backend.middleware.rate_limit import rate_limit

router = APIRouter()

@router.post('/upload')
async def upload_resume(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user)
):
    await rate_limit(user['id'], 'resume_upload')

    file_bytes = await file.read()
    raw_text   = await extract_text(file_bytes, file.filename)
    parsed     = await parse_resume(raw_text)
    resume_id  = await save_resume(user['id'], raw_text, parsed)

    await embed_resume(resume_id, raw_text)

    return {'resume_id': resume_id, 'skills': parsed.get('skills', [])}

@router.get('/{resume_id}')
async def get_resume_detail(resume_id: str, user: dict = Depends(get_current_user)):
    resume = await get_resume(resume_id)
    if not resume:
        raise HTTPException(404, 'Resume not found')
    if resume['user_id'] != user['id']:
        raise HTTPException(403, 'Access denied')
    return resume

@router.get('/')
async def list_resumes(user: dict = Depends(get_current_user)):
    result = supabase.table('resumes') \
        .select('id, created_at, parsed_json') \
        .eq('user_id', user['id']) \
        .execute()
    return {'resumes': result.data or []}

@router.delete('/{resume_id}')
async def delete_resume(resume_id: str, user: dict = Depends(get_current_user)):
    resume = await get_resume(resume_id)
    if not resume:
        raise HTTPException(404, 'Resume not found')
    if resume['user_id'] != user['id']:
        raise HTTPException(403, 'Access denied')
    supabase.table('resumes').delete().eq('id', resume_id).execute()
    return {'deleted': resume_id}