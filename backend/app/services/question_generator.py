"""
Question generation service (assignment sections 7.2 & 7.3).

Pipeline:
  role + resume_profile
    -> build_queries()                  (rag/retriever.py)
    -> retrieve_context_for_queries()   (rag/retriever.py)
    -> generate_questions_from_context()  <- this module
    -> list of {text, topic, difficulty, source_query, source_chunks}
       ready to persist as Question rows, with full provenance retained.
"""
import json
from typing import List, Dict, Any

from app.config import settings
from app.rag.retriever import build_queries, retrieve_context_for_queries
from app.services.llm_client import get_llm_client, wrap_fallback_task, FallbackLLMClient

QUESTION_GEN_SYSTEM_PROMPT = (
    "You are conducting a structured technical interview. You will be given "
    "a job role, a candidate's resume profile, and several retrieved "
    "reference-material excerpts, each tied to a specific probing query. "
    "For EACH item, write exactly ONE interview question that:\n"
    "- is grounded in the excerpt's content (do not invent facts not implied by it)\n"
    "- is relevant to the stated role\n"
    "- is influenced by the candidate's background where natural\n"
    "- avoids generic, template-sounding phrasing (no 'Tell me about yourself')\n"
    "- is labeled with a difficulty of 'conceptual', 'applied', or 'advanced'\n\n"
    "Respond with ONLY valid JSON: "
    '{"questions": [{"text": "...", "topic": "<the query it came from>", '
    '"difficulty": "conceptual|applied|advanced"}, ...]}'
)


def _format_context_for_prompt(retrieval_results: List[Dict[str, Any]]) -> str:
    blocks = []
    for i, item in enumerate(retrieval_results):
        chunk_texts = "\n".join(
            f"  - {c['text'][:500]}" for c in item["chunks"][:3]
        )
        blocks.append(f"Item {i+1} — Query: {item['query']}\nExcerpts:\n{chunk_texts}")
    return "\n\n".join(blocks)


def generate_questions(
    role: str, resume_profile: Dict[str, Any], n: int = None
) -> List[Dict[str, Any]]:
    n = n or settings.QUESTIONS_PER_SESSION

    queries = build_queries(role, resume_profile, n=n)
    retrieval_results = retrieve_context_for_queries(role, queries)

    # Drop queries that returned nothing (e.g., knowledge base not ingested
    # yet for that exact phrasing) rather than generating ungrounded questions.
    retrieval_results = [r for r in retrieval_results if r["chunks"]]

    if not retrieval_results:
        return []

    client = get_llm_client()

    if isinstance(client, FallbackLLMClient):
        task = {
            "kind": "generate_questions",
            "role": role,
            "items": [
                {
                    "query": r["query"],
                    "chunks": [{"text": c["text"]} for c in r["chunks"]],
                }
                for r in retrieval_results
            ],
        }
        raw = client.generate(QUESTION_GEN_SYSTEM_PROMPT, wrap_fallback_task(task))
    else:
        prompt = (
            f"Role: {role}\n"
            f"Candidate resume profile: {json.dumps(resume_profile)}\n\n"
            f"Retrieved context:\n{_format_context_for_prompt(retrieval_results)}\n\n"
            "Generate the questions now, one per item, per the JSON schema."
        )
        raw = client.generate(QUESTION_GEN_SYSTEM_PROMPT, prompt)

    try:
        cleaned = raw.strip().strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
        parsed = json.loads(cleaned)
        generated_questions = parsed.get("questions", [])
    except (json.JSONDecodeError, ValueError):
        generated_questions = []

    # Attach RAG provenance (source query + source chunks) to each question
    # by position, so every question is fully traceable (section 7.5).
    final_questions = []
    for i, q in enumerate(generated_questions[: len(retrieval_results)]):
        provenance = retrieval_results[i]
        final_questions.append(
            {
                "text": q.get("text", "").strip(),
                "topic": q.get("topic", provenance["query"]),
                "difficulty": q.get("difficulty", "conceptual"),
                "source_query": provenance["query"],
                "source_chunks": [
                    {
                        "source": c["metadata"].get("source"),
                        "chunk_index": c["metadata"].get("chunk_index"),
                        "snippet": c["text"][:300],
                    }
                    for c in provenance["chunks"]
                ],
            }
        )

    return [q for q in final_questions if q["text"]]
