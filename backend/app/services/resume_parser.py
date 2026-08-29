"""
Resume parsing & structured profile extraction (assignment section 7.4).

Two stages:
1. Text extraction from the uploaded PDF/text file.
2. Structured extraction of skills / technologies / domains / experience
   level, either via the configured LLM (higher recall, handles synonyms
   and phrasing the keyword bank wouldn't) or via the fallback keyword-bank
   extractor when no LLM key is configured.
"""
import io
import json
from typing import Dict, Any

from pypdf import PdfReader

from app.services.llm_client import get_llm_client, wrap_fallback_task, FallbackLLMClient


def extract_text_from_upload(filename: str, file_bytes: bytes) -> str:
    if filename.lower().endswith(".pdf"):
        reader = PdfReader(io.BytesIO(file_bytes))
        pages = []
        for page in reader.pages:
            try:
                pages.append(page.extract_text() or "")
            except Exception:
                continue
        return "\n".join(pages).strip()
    # Treat anything else as plain text.
    return file_bytes.decode("utf-8", errors="ignore").strip()


EXTRACTION_SYSTEM_PROMPT = (
    "You are an expert technical recruiter. Extract a structured profile "
    "from the candidate's resume text. Respond with ONLY valid JSON, no "
    "commentary, matching this schema exactly: "
    '{"skills": string[], "technologies": string[], "domains": string[], '
    '"experience_level": "junior"|"mid"|"senior"}'
)


def extract_resume_profile(resume_text: str) -> Dict[str, Any]:
    client = get_llm_client()

    if isinstance(client, FallbackLLMClient):
        task = {"kind": "extract_resume", "resume_text": resume_text[:8000]}
        raw = client.generate(EXTRACTION_SYSTEM_PROMPT, wrap_fallback_task(task))
    else:
        prompt = (
            f"Resume text:\n---\n{resume_text[:8000]}\n---\n"
            "Return ONLY the JSON object described in the system prompt."
        )
        raw = client.generate(EXTRACTION_SYSTEM_PROMPT, prompt)

    try:
        # Real LLMs occasionally wrap JSON in prose/backticks; strip those.
        cleaned = raw.strip().strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
        profile = json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        # Last-resort safety net so a malformed LLM response never 500s.
        profile = {
            "skills": [],
            "technologies": [],
            "domains": [],
            "experience_level": "unknown",
        }

    profile.setdefault("skills", [])
    profile.setdefault("technologies", [])
    profile.setdefault("domains", [])
    profile.setdefault("experience_level", "unknown")
    return profile
