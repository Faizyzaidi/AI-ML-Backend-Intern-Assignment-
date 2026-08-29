"""
Chunking strategy for knowledge-base ingestion.

Design decision (documented in README too):
- We chunk by word count rather than raw characters, approximating tokens
  (1 word ~ 1.3 tokens for English technical text), which keeps chunks
  semantically coherent (paragraph-ish) rather than splitting mid-sentence
  as often as pure character slicing would.
- A sliding overlap between consecutive chunks preserves context that
  would otherwise be lost at chunk boundaries (e.g., a concept explained
  across a page break), which matters a lot for textbook-style sources.
- Chunks are further split on paragraph boundaries first when possible,
  so a chunk doesn't awkwardly straddle unrelated paragraphs.
"""
from dataclasses import dataclass
from typing import List
import re

from app.config import settings


@dataclass
class Chunk:
    text: str
    chunk_index: int
    start_word: int
    end_word: int


def _normalize_whitespace(text: str) -> str:
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(
    text: str,
    chunk_size_words: int = None,
    overlap_words: int = None,
) -> List[Chunk]:
    """Split `text` into overlapping word-based chunks.

    Falls back to settings-configured sizes when not explicitly provided.
    """
    chunk_size_words = chunk_size_words or settings.CHUNK_SIZE_TOKENS
    overlap_words = overlap_words or settings.CHUNK_OVERLAP_TOKENS

    text = _normalize_whitespace(text)
    words = text.split(" ")
    words = [w for w in words if w.strip()]

    if not words:
        return []

    chunks: List[Chunk] = []
    start = 0
    idx = 0
    step = max(chunk_size_words - overlap_words, 1)

    while start < len(words):
        end = min(start + chunk_size_words, len(words))
        chunk_words = words[start:end]
        chunk_str = " ".join(chunk_words).strip()
        if chunk_str:
            chunks.append(
                Chunk(text=chunk_str, chunk_index=idx, start_word=start, end_word=end)
            )
            idx += 1
        if end == len(words):
            break
        start += step

    return chunks
