"""
Final output / summary generation (assignment section 3, "Final Output").
"""
import json
from typing import List, Dict, Any

from app.services.llm_client import get_llm_client, wrap_fallback_task, FallbackLLMClient

SUMMARY_SYSTEM_PROMPT = (
    "You are a hiring manager reviewing a completed technical interview "
    "transcript. Given the role, the candidate's resume profile, and the "
    "list of question/answer pairs, produce a concise, honest, structured "
    "assessment. Respond with ONLY valid JSON: "
    '{"insights": string[], "topics_covered": string[]}. '
    "Insights should be specific (reference actual topics/answers), "
    "balanced (call out both strengths and gaps), and actionable."
)


def _heuristic_quality_score(answer_text: str) -> int:
    """Very lightweight heuristic used when no LLM grading is configured:
    longer, more specific answers score higher. This is intentionally
    simple — it's a stand-in signal for adaptive difficulty, not a claim
    of rigorous grading.
    """
    words = answer_text.split()
    length_score = min(len(words) / 60, 1.0) * 70
    specificity_bonus = 15 if any(c.isdigit() for c in answer_text) else 0
    technical_bonus = 15 if len(set(w.lower() for w in words)) / max(len(words), 1) > 0.6 else 0
    return int(min(length_score + specificity_bonus + technical_bonus, 100))


def score_answer(answer_text: str) -> int:
    return _heuristic_quality_score(answer_text)


def generate_summary(
    role: str, resume_profile: Dict[str, Any], qa_pairs: List[Dict[str, Any]]
) -> Dict[str, Any]:
    client = get_llm_client()

    if isinstance(client, FallbackLLMClient):
        task = {"kind": "summarize_session", "qa_pairs": qa_pairs}
        raw = client.generate(SUMMARY_SYSTEM_PROMPT, wrap_fallback_task(task))
    else:
        prompt = (
            f"Role: {role}\n"
            f"Resume profile: {json.dumps(resume_profile)}\n"
            f"Transcript: {json.dumps(qa_pairs)}\n\n"
            "Produce the JSON assessment now."
        )
        raw = client.generate(SUMMARY_SYSTEM_PROMPT, prompt)

    try:
        cleaned = raw.strip().strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
        parsed = json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        parsed = {"insights": [], "topics_covered": []}

    parsed.setdefault("insights", [])
    parsed.setdefault("topics_covered", sorted({qa.get("topic") for qa in qa_pairs if qa.get("topic")}))
    return parsed
