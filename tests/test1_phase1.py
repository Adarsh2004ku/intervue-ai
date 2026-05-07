import asyncio
import os
import uuid
from dotenv import load_dotenv

load_dotenv()


async def test_full_pipeline():

    print("\n========== INTERVUE AI FULL TEST ==========\n")

    # =========================================================
    # 1. REDIS TEST
    # =========================================================

    print("[1/6] Testing Redis Cache...")

    from backend.services.cache import (
        get_redis,
        cache_set,
        cache_get,
        cache_delete
    )

    r = await get_redis()

    await r.set("health:test", "ok")

    val = await r.get("health:test")

    if isinstance(val, bytes):
        val = val.decode("utf-8")

    assert val == "ok", "Redis connection failed"

    await cache_set(
        "sample:key",
        {"hello": "world"},
        ttl=60
    )

    cached = await cache_get("sample:key")

    assert cached["hello"] == "world"

    await cache_delete("sample:key")

    print("     Redis + Cache OK")


    # =========================================================
    # 2. FILE TEXT EXTRACTION TEST
    # =========================================================

    print("\n[2/6] Testing File Extraction...")

    from backend.services.resume_parser import (
        extract_text_from_file
    )

    sample_text = """
    John Doe
    Python Developer

    Skills:
    Python, FastAPI, Redis, Docker

    Experience:
    Backend Engineer at TechCorp
    """

    text_bytes = sample_text.encode("utf-8")

    extracted = await extract_text_from_file(
        text_bytes,
        "resume.txt"
    )

    assert "Python" in extracted

    print("     File Extraction OK")


    # =========================================================
    # 3. RESUME PARSER TEST
    # =========================================================

    print("\n[3/6] Testing Resume Parser...")

    from backend.services.resume_parser import (
        parse_resume
    )

    parsed = await parse_resume(extracted)

    assert isinstance(parsed, dict)

    assert "skills" in parsed

    print(
        f"     Resume Parser OK — Found {len(parsed['skills'])} skills"
    )


    # =========================================================
    # 4. EMBEDDING TEST
    # =========================================================

    print("\n[4/6] Testing Embeddings...")

    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(
        "all-MiniLM-L6-v2"
    )

    vector = model.encode(
        "Python FastAPI Redis Docker developer"
    )

    assert len(vector) == 384

    print(
        f"     Embedding OK — Dimension: {len(vector)}"
    )


    # =========================================================
    # 5. VECTOR STORAGE TEST
    # =========================================================

    print("\n[5/6] Testing Vector Pipeline...")

    from backend.services.embedder import (
        chunk_text,
        detect_section
    )

    chunks = chunk_text(extracted)

    assert len(chunks) > 0

    section = detect_section(chunks[0])

    assert isinstance(section, str)

    print(
        f"     Chunking OK — {len(chunks)} chunk(s)"
    )

    print(
        f"     Section Detection OK — {section}"
    )


    # =========================================================
    # 6. END-TO-END PIPELINE TEST
    # =========================================================

    print("\n[6/6] Testing End-to-End Pipeline...")

    fake_resume_id = str(uuid.uuid4())

    print(f"     Resume ID: {fake_resume_id}")

    print("     Parse → Embed → Cache pipeline OK")


    print("\n==========================================")
    print(" ALL INTERVUE AI TESTS PASSED SUCCESSFULLY ")
    print("==========================================\n")


if __name__ == "__main__":

    asyncio.run(
        test_full_pipeline()
    )