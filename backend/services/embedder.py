import json,os,hashlib
from typing import List
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from supabase import create_client
from backend.services.cache import cache_get,cache_set
from dotenv import load_dotenv
load_dotenv()

embedder  = GoogleGenerativeAIEmbeddings(
    model='models/embedding-001',
    google_api_key=os.getenv('GOOGLE_API_KEY')
)

supabase  = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_KEY')
)

def chunk_text(text: str,chunk_size= 500,overlap :int = 50 )->List[str]:
    """
    Split text intooverlapping word-level Chunks
    """
    words = text.split()
    chunks = []
    step = []
    step = chunk_size - overlap
    for i in range(0,len(words),step):
        chunk = ' '.join(words[ i : i+ chunk_size])
        if chunk.strip():
            chunks.append(chunk)
    return chunks

async def embed_resume(resume_id : str, raw_text:str)->int:
    """
    Chunk raw_text, embed each chunk, store in pgvector.
    Returns number of chunks stored.
    """
    chunks = chunk_text(raw_text)

    # Embed all chunks in one batch call (more efficient than one-by-one)

    vectors = await embedder.aembed_documents(chunks)
    rows = [
        {
            'resume_id' : resume_id,
            'chunk_text': chunk,
            'section_tag' : detect_section(chunk),
            'embedding' : vector
        }
        for chunk,vector in zip(chunks,vectors)
    ]
    supabase.table('resume_chunks').insert(rows).execute()
    print(f"stored{len(rows)} vectors in pgvector")
    return len(rows)


def detect_section(chunk_text : str) -> str:
    """
    Simple heuristic to tag which resume sections a chunk belongs to 
    """
    text_lower = chunk_text.lower()

    if any(w in text_lower for w in 
           [ 'experience','worked','engineer','developer','intern']):
        return 'experience'
    
    if any(w in text_lower for w in 
           ['skill','python','java','react','sql','docker']):
        return 'skills'
    
    if any(w in text_lower for w in ['education','university','college','degree','gpa']):
        return 'education'
    
    if any(w in text_lower for w in ['project','built','created','developed']):
        return 'projects'
    return 'general'


async def retrieve_chunks( resume_id : str,query:str,top_k : int = 5)->List[dict]:
    """
    Retrieve top-k most relevant resume chunks for a query.
    using pgvector cosine similarity via supabase RPC.
    Result cached 2h per query.
    """
    cache_key = f'retrival : {hashlib.sha256((resume_id+ query).encode()).hexdigest()[:12]}'
    cached = await cache_get(cache_key)
    if cached:
        return cached
    query_vector = await embedder.aembed_query(query)

    result = supabase.rpc('match_resume_chunks',{
        'resume_id_arg':   resume_id,
        'query_embedding': query_vector,
        'match_count':     top_k
    }).execute()

    chunks = result.data or []
    await cache_set(cache_key,chunks,ttl = 7200) #2h
    return chunks