import PyPDF2 , io ,json,hashlib
from docx import Document as DocxDocument
from langchain_google_genai import ChatGoogleGenerativeAI
from backend.services.cache import cache_get,cache_set,cache_key
from dotenv import load_dotenv
import os
load_dotenv()

llm = ChatGoogleGenerativeAI(
    model = "gemini-3-flash-preview",
    temperature=0,
    google_api_key=os.getenv("GOOGLE_API_KEY")
    )


PARSE_PROMPT = '''
You are a resume parser. Extract structured information from this resume.
Return ONLY valid JSON with these exact keys:
{{
  "full_name": string,
  "email": string or null,
  "phone": string or null,
  "skills": [string],
  "experience": [{{
    "title": string,
    "company": string,
    "duration": string,
    "bullets": [string]
  }}],
  "education": [{{
    "degree": string,
    "institution": string,
    "year": string
  }}],
  "projects": [{{
    "name": string,
    "tech_stack": [string],
    "description": string
  }}],
  "total_years_experience": number
}}
 
Resume text:
{resume_text}
 
Return ONLY the JSON object. No markdown, no explanation.
'''

async def extract_text(file_bytes: bytes, filename: str) -> str:
    """
    Extract raw text from PDF, Docx or plain text files
    """

    ext = filename.lower().split('.')[-1]

    if ext == 'pdf': #for pdf
        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        return "\n".join(
            page.extract_text()  or "" for page in reader.pages
        )
    elif ext == "docx": # dor docx file
        doc = DocxDocument(io.BytesIO(file_bytes))
        return "\n".join(
            para.text for para in doc.paragraphs if para.text.strip()
        )
    else : #plain text or unsupported formats, try to decode as utf-8
        return file_bytes.decode('utf-8', errors='ignore')
    
async def parse_resume(raw_text:str)->dict:
    """
    Parse raw resume text into structured json.cached 24h
    """
    # cached key based on hash -same resume-same result
    text_hash = hashlib.sha256(raw_text.encode()).hexdigest()[:16]
    cache_key = f"resume_parse:{text_hash}"

    cached = await cache_get(cache_key)
    if cached:
        print(f"Cache hit : resume parse {text_hash}")
        return cached

    print(f'Cache Miss : Calling Gemini to parse resume ...')
    prompt = PARSE_PROMPT.format(resume_text = raw_text[:5000])
    response = await llm.ainvoke(prompt)


    #strip markdown fences if present
    content = response.content

    if isinstance(content, list):

        cleaned_parts = []

        for part in content:

            # Gemini structured dict response
            if isinstance(part, dict) and "text" in part:
                cleaned_parts.append(part["text"])

            # object with .text attribute
            elif hasattr(part, "text"):
                cleaned_parts.append(part.text)

            else:
                cleaned_parts.append(str(part))

        content = "".join(cleaned_parts)
    content = content.strip()

    if content.startswith('```'):

        content = content.replace(
            '```json',
            ''
        ).replace(
            '```',
            ''
        ).strip()
    
    print("\n=== GEMINI RESPONSE ===")
    print(content)
    print("=======================\n")

    parsed = json.loads(content)
    await cache_set(cache_key,parsed,ttl = 86400) # 24hours
    return parsed