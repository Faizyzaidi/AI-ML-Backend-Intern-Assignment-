"""
Vector store wrapper around ChromaDB.

Design decision: one Chroma **collection per role** (e.g., "backend-engineer",
"ai-ml-engineer"). This keeps retrieval scoped to the relevant knowledge base
by construction (no cross-role leakage), keeps ingestion idempotent per role,
and lets new roles be added without touching existing collections.
"""
from typing import List, Dict, Any
import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import settings
from app.rag.embeddings import get_embedder


def _slugify(role: str) -> str:
    return role.strip().lower().replace(" ", "-").replace("/", "-")


class VectorStore:
    def __init__(self):
        import os

        os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
        self._client = chromadb.PersistentClient(
            path=settings.VECTOR_STORE_DIR,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._embedder = get_embedder()

    def _collection(self, role: str):
        name = f"role_{_slugify(role)}"
        # embedding_function=None because we pass precomputed embeddings
        return self._client.get_or_create_collection(name=name)

    def collection_count(self, role: str) -> int:
        try:
            return self._collection(role).count()
        except Exception:
            return 0

    def list_roles(self) -> List[str]:
        return [
            c.name.replace("role_", "", 1)
            for c in self._client.list_collections()
        ]

    def upsert_chunks(
        self,
        role: str,
        chunk_texts: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str],
    ):
        """Embed and store chunks. Idempotent: re-running ingestion with the
        same deterministic ids overwrites existing entries rather than
        duplicating them.
        """
        collection = self._collection(role)
        embeddings = self._embedder.embed_texts(chunk_texts)
        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=chunk_texts,
            metadatas=metadatas,
        )

    def query(self, role: str, query_text: str, top_k: int = 4) -> List[Dict[str, Any]]:
        collection = self._collection(role)
        if collection.count() == 0:
            return []
        query_embedding = self._embedder.embed_query(query_text)
        result = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, collection.count()),
        )
        hits = []
        docs = result.get("documents", [[]])[0]
        metas = result.get("metadatas", [[]])[0]
        ids = result.get("ids", [[]])[0]
        distances = result.get("distances", [[]])[0]
        for doc, meta, _id, dist in zip(docs, metas, ids, distances):
            hits.append(
                {
                    "id": _id,
                    "text": doc,
                    "metadata": meta,
                    "distance": dist,
                }
            )
        return hits


_store_instance: VectorStore = None


def get_vector_store() -> VectorStore:
    global _store_instance
    if _store_instance is None:
        _store_instance = VectorStore()
    return _store_instance
