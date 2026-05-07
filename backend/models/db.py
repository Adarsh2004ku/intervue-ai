import os,uuid
from supabase import create_client
from datetime import datetime

supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_KEY'))



# RESUME
async def save_resume(user_id:str,raw_text:str,parsed_json:dict)->str:
    row = {'user_id':user_id,'raw_text':raw_text,'parsed_json':parsed_json}
    result = supabase.table('resumes').insert(row).execute()

async def get_resume(resume_id:str)->dict:
    result = supabase.table('resumes').select('*').eq('id',resume_id).single().execute()
    return result.data



# TOPIC PROFILES
async def fetch_topic_profiles(user_id: str) -> list[dict]:
    result = supabase.table('user_topic_profiles') \
        .select('topic, avg_score, attempt_count') \
        .eq('user_id', user_id).execute()
    return result.data

async def upsert_topic_score(user_id: str, topic: str, new_score: int):
    '''Rolling average upsert — updates existing row or creates new one.'''
    existing = supabase.table('user_topic_profiles') \
        .select('avg_score, attempt_count') \
        .eq('user_id', user_id).eq('topic', topic).execute()
    if existing.data:
        row = existing.data[0]
        n   = row['attempt_count']
        new_avg = (row['avg_score'] * n + new_score) / (n + 1)
        supabase.table('user_topic_profiles') \
            .update({'avg_score': new_avg, 'attempt_count': n + 1,
                     'last_seen': datetime.utcnow().isoformat()}) \
            .eq('user_id', user_id).eq('topic', topic).execute()
    else:
        supabase.table('user_topic_profiles').insert({
            'user_id': user_id, 'topic': topic,
            'avg_score': new_score, 'attempt_count': 1
        }).execute()

#  Interviews 

async def create_interview(user_id: str, resume_id: str, job_role: str,
                            mode: str, company_id: str = None) -> str:
    row = {
        'user_id': user_id, 'resume_id': resume_id, 'job_role': job_role,
        'interview_mode': mode, 'company_id': company_id, 'status': 'active',
        'started_at': datetime.utcnow().isoformat()
    }
    result = supabase.table('interviews').insert(row).execute()
    return result.data[0]['id']

async def complete_interview(interview_id: str, total_tokens: int):
    supabase.table('interviews').update({
        'status': 'completed', 'total_tokens': total_tokens,
        'completed_at': datetime.utcnow().isoformat()
    }).eq('id', interview_id).execute()


# ── Reports ──
async def save_report(interview_id: str, report_data: dict) -> str:
    row = {
        'interview_id': interview_id,
        'overall_score': report_data.get('overall_score'),
        'grade': report_data.get('grade'),
        'feedback_json': report_data,
        'improvement_plan': report_data.get('overall_feedback'),
        'interview_readiness': report_data.get('interview_readiness')
    }
    result = supabase.table('reports').insert(row).execute()
    return result.data[0]['id']


# COST TRACKING

async def log_ai_cost(interview_id: str, model: str, agent: str,
                       tokens_in: int, tokens_out: int):
    cost_per_1m = {'gemini-1.5-flash': 0.01, 'llama3-8b-8192': 0.59}
    rate      = cost_per_1m.get(model, 0.01)
    cost_inr  = ((tokens_in + tokens_out) / 1_000_000) * rate * 83  # USD→INR
    supabase.table('ai_costs').insert({
        'interview_id': interview_id, 'model': model, 'agent_name': agent,
        'tokens_in': tokens_in, 'tokens_out': tokens_out, 'cost_inr': cost_inr
    }).execute()

async def count_user_interviews(user_id: str) -> int:
    result = supabase.table('interviews') \
        .select('id', count='exact').eq('user_id', user_id).execute()
    return result.count or 0
