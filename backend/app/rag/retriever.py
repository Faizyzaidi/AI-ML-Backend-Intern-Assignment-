"""
Retrieval layer: turns (role, resume profile) into a set of targeted
queries, then pulls the most relevant knowledge-base chunks for each.

This is what implements assignment section 7.2 (dynamic query
construction from resume + role, not a static role-name lookup).
"""
from typing import List, Dict, Any

from app.config import settings
from app.rag.vector_store import get_vector_store


def build_queries(role: str, resume_profile: Dict[str, Any], n: int) -> List[str]:
    """Construct a diverse set of retrieval queries from the role and the
    candidate's extracted resume signal.

    Strategy: combine (a) core-role fundamentals queries that ensure
    baseline topic coverage regardless of resume content, with (b)
    resume-driven queries built from the candidate's specific skills/
    technologies/domains, so the interview is meaningfully personalized
    rather than generic.
    """
    skills = resume_profile.get("skills", [])
    technologies = resume_profile.get("technologies", [])
    domains = resume_profile.get("domains", [])

    queries: List[str] = []

    # Resume-driven queries first — these personalize the interview.
    for item in technologies[:4]:
        queries.append(f"{role} fundamentals and best practices related to {item}")
    for item in skills[:4]:
        queries.append(f"{role} interview topic: {item} concepts and applications")
    for item in domains[:2]:
        queries.append(f"{role} domain knowledge in {item}")

    # Always ensure some core/fundamental coverage even if the resume is
    # thin or the candidate lists nothing recognizable.
    core_queries = [
        f"core theoretical concepts every {role} should understand",
        f"common {role} system design and architecture considerations",
        f"practical/applied {role} problem-solving scenario",
    ]
    queries.extend(core_queries)

    # De-duplicate while preserving order, then trim to n.
    seen = set()
    unique_queries = []
    for q in queries:
        if q not in seen:
            seen.add(q)
            unique_queries.append(q)

    return unique_queries[:n]


def retrieve_context_for_queries(
    role: str, queries: List[str], top_k: int = None
) -> List[Dict[str, Any]]:
    """For each query, retrieve top-k chunks. Returns a list of
    {query, chunks: [...]} preserving traceability of query -> chunks.
    """
    top_k = top_k or settings.RETRIEVAL_TOP_K
    store = get_vector_store()

    results = []
    for query in queries:
        hits = store.query(role=role, query_text=query, top_k=top_k)
        results.append({"query": query, "chunks": hits})
    return results
