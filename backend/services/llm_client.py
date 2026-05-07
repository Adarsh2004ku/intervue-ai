import json,os,hashlib
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from backend.services.cache import cache_get,cache_set,cache_key

#primary Gemini(free-tier)

gemini = ChatGoogleGenerativeAI(
    model = "gemini-3-flash",
    temperature=0.3,
    google_api_key=os.getenv("GOOGLE_API_KEY")
    )

# Fallback Groq_llama(for rate limit recovery)
groq = ChatGroq(
    model="gemma2-2b-it",
    temperature=0.3,
    groq_api_key=os.getenv('GROQ_API_KEY')
)


async def llm_call(prompt:str,use_cache :bool = True) ->str:
    '''Call Gemini with automatic Groq fallback. Returns raw text.'''
    if use_cache:
        key = cache_key('llm', hashlib.sha256(prompt.encode()).hexdigest()[:20])
        cached = await cache_get(key)
        if cached:
            return cached
    
    try :
        result = await gemini.ainvoke(prompt)
        text = result.content
    except Exception as e:
        # Rate limit quota - fallback to groq
        if 'quota' in str(e).lower() or '429' in str(e):
            result = await groq.ainvoke(prompt)
            text   = result.content
        else:
           raise
    if use_cache:
        await cache_set(key,text,ttl = 3600)
    return text

async def llm_json(prompt: str) -> dict:
    '''Call LLM and parse JSON response. Strips markdown fences.'''
    raw = await llm_call(prompt)
    # Strip markdown code fences if present
    clean = raw.strip().lstrip('```json').lstrip('```').rstrip('```').strip()
    return json.loads(clean)