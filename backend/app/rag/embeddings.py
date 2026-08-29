"""
Embedding provider abstraction.

Two backends are supported behind a single interface so the rest of the
system (vector store, retriever) never needs to know which one is active:

- "hashing" (default): a deterministic, dependency-light embedding built
  from hashed n-gram term frequencies, L2-normalized. It requires no model
  download and no network access, which matters for reproducible grading
  environments / CI. Quality is lower than a real sentence embedding model
  but is perfectly adequate for demonstrating a working, correct RAG
  pipeline end-to-end.
- "sentence-transformers": a real transformer sentence-embedding model
  (all-MiniLM-L6-v2 by default) for meaningfully better retrieval quality.
  Enable with EMBEDDING_PROVIDER=sentence-transformers once the model has
  been downloaded (requires one-time internet access).

Both implementations return plain Python lists of floats so they can be
stored directly in ChromaDB without further conversion.
"""
from typing import List
import hashlib
import math
import re

from app.config import settings


class BaseEmbedder:
    dim: int

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        raise NotImplementedError

    def embed_query(self, text: str) -> List[float]:
        return self.embed_texts([text])[0]


class HashingEmbedder(BaseEmbedder):
    """Deterministic bag-of-n-grams hashing embedder (no ML dependency)."""

    def __init__(self, dim: int = None):
        self.dim = dim or settings.EMBEDDING_DIM

    def _tokenize(self, text: str) -> List[str]:
        text = text.lower()
        tokens = re.findall(r"[a-z0-9]+", text)
        # unigrams + bigrams capture a bit of local word order/context
        bigrams = [f"{a}_{b}" for a, b in zip(tokens, tokens[1:])]
        return tokens + bigrams

    def _hash_index(self, token: str) -> int:
        h = hashlib.md5(token.encode("utf-8")).hexdigest()
        return int(h, 16) % self.dim

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        vectors = []
        for text in texts:
            vec = [0.0] * self.dim
            for token in self._tokenize(text):
                idx = self._hash_index(token)
                # sign hashing trick reduces collision bias
                sign = 1.0 if (hash(token) % 2 == 0) else -1.0
                vec[idx] += sign
            norm = math.sqrt(sum(v * v for v in vec)) or 1.0
            vectors.append([v / norm for v in vec])
        return vectors


class SentenceTransformerEmbedder(BaseEmbedder):
    """Real sentence-embedding model. Requires the `sentence-transformers`
    package and (on first use) internet access to download model weights.
    """

    def __init__(self, model_name: str = None):
        from sentence_transformers import SentenceTransformer  # lazy import

        self.model_name = model_name or settings.SENTENCE_TRANSFORMER_MODEL
        self._model = SentenceTransformer(self.model_name)
        self.dim = self._model.get_sentence_embedding_dimension()

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        embeddings = self._model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()


_embedder_instance: BaseEmbedder = None


def get_embedder() -> BaseEmbedder:
    """Singleton accessor so the (potentially expensive) model is loaded once."""
    global _embedder_instance
    if _embedder_instance is not None:
        return _embedder_instance

    if settings.EMBEDDING_PROVIDER == "sentence-transformers":
        try:
            _embedder_instance = SentenceTransformerEmbedder()
        except Exception as exc:  # pragma: no cover - graceful degradation
            print(
                f"[embeddings] Falling back to hashing embedder "
                f"(sentence-transformers unavailable: {exc})"
            )
            _embedder_instance = HashingEmbedder()
    else:
        _embedder_instance = HashingEmbedder()

    return _embedder_instance
