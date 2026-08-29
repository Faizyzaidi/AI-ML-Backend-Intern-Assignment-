"""
Knowledge-base ingestion pipeline.

Usage:
    python -m app.rag.ingest                 # ingest all roles
    python -m app.rag.ingest --role backend-engineer

Directory convention:
    backend/data/knowledge_base/<role-slug>/*.pdf   (or .txt)

Example (per assignment section 9):
    backend/data/knowledge_base/ai-ml-engineer/machine-learning-tom-mitchell.pdf
    backend/data/knowledge_base/ai-ml-engineer/hundred-page-ml-book.pdf
    backend/data/knowledge_base/data-science/intro-to-ml-with-python.pdf

Idempotency: chunk ids are deterministic (derived from role + source
filename + chunk index), so re-running ingestion on the same files
upserts rather than duplicates. Re-running after editing a file's content
is safe; delete the collection first if you need a clean rebuild.
"""
import argparse
import hashlib
from pathlib import Path
from typing import List

from pypdf import PdfReader

from app.config import settings
from app.rag.chunking import chunk_text
from app.rag.vector_store import get_vector_store


def _read_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    pages_text = []
    for page in reader.pages:
        try:
            pages_text.append(page.extract_text() or "")
        except Exception:
            continue
    return "\n".join(pages_text)


def _read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _load_source_text(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        return _read_pdf(path)
    return _read_text_file(path)


def _deterministic_id(role: str, source_name: str, chunk_index: int) -> str:
    raw = f"{role}::{source_name}::{chunk_index}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def ingest_role(role_dir: Path):
    role = role_dir.name
    store = get_vector_store()

    source_files: List[Path] = [
        p for p in role_dir.iterdir() if p.suffix.lower() in (".pdf", ".txt")
    ]
    if not source_files:
        print(f"[ingest] No source documents found for role '{role}', skipping.")
        return

    total_chunks = 0
    for source_path in source_files:
        print(f"[ingest] Reading {source_path.name} ...")
        raw_text = _load_source_text(source_path)
        if not raw_text.strip():
            print(f"[ingest]   WARNING: no extractable text in {source_path.name}")
            continue

        chunks = chunk_text(raw_text)
        if not chunks:
            continue

        ids = [
            _deterministic_id(role, source_path.name, c.chunk_index) for c in chunks
        ]
        texts = [c.text for c in chunks]
        metadatas = [
            {
                "role": role,
                "source": source_path.name,
                "chunk_index": c.chunk_index,
            }
            for c in chunks
        ]

        store.upsert_chunks(role=role, chunk_texts=texts, metadatas=metadatas, ids=ids)
        total_chunks += len(chunks)
        print(f"[ingest]   -> {len(chunks)} chunks embedded & stored.")

    print(f"[ingest] Done. Role '{role}': {total_chunks} total chunks ingested.")


def main():
    parser = argparse.ArgumentParser(description="Ingest role-specific knowledge bases.")
    parser.add_argument(
        "--role",
        help="Only ingest this role slug (directory name under knowledge_base/).",
        default=None,
    )
    args = parser.parse_args()

    kb_root = Path(settings.KNOWLEDGE_BASE_DIR)
    if not kb_root.exists():
        print(f"[ingest] Knowledge base directory not found: {kb_root}")
        return

    role_dirs = [d for d in kb_root.iterdir() if d.is_dir()]
    if args.role:
        role_dirs = [d for d in role_dirs if d.name == args.role]
        if not role_dirs:
            print(f"[ingest] Role directory '{args.role}' not found under {kb_root}")
            return

    if not role_dirs:
        print(
            f"[ingest] No role directories found under {kb_root}. "
            "Create e.g. data/knowledge_base/ai-ml-engineer/ and add PDFs."
        )
        return

    for role_dir in role_dirs:
        ingest_role(role_dir)


if __name__ == "__main__":
    main()
