"""Embedding service — TF-IDF for batch, n-gram overlap for single queries."""

import re
import hashlib
import math
from typing import Sequence

from app.core.config import settings


class EmbeddingService:
    """Generates text embeddings for semantic search."""

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or settings.openai_api_key
        self._use_openai = bool(self._api_key)
        self.model = settings.embedding_model
        self.dimensions = settings.embedding_dimensions

    async def embed_text(self, text: str) -> list[float]:
        if self._use_openai:
            return await self._embed_openai(text)
        return _make_vector(text, self.dimensions)

    async def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        if self._use_openai:
            return await self._embed_openai_batch(texts)
        # Use TF-IDF for batch (chunks from the same document)
        return _tfidf_batch(list(texts), self.dimensions)

    async def embed_texts_batched(
        self, texts: Sequence[str], batch_size: int = 50
    ) -> list[list[float]]:
        all_embeddings: list[list[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            embeddings = await self.embed_texts(list(batch))
            all_embeddings.extend(embeddings)
        return all_embeddings

    async def _embed_openai(self, text: str) -> list[float]:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=self._api_key)
        r = await client.embeddings.create(model=self.model, input=text, dimensions=self.dimensions)
        return r.data[0].embedding

    async def _embed_openai_batch(self, texts: Sequence[str]) -> list[list[float]]:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=self._api_key)
        r = await client.embeddings.create(model=self.model, input=list(texts), dimensions=self.dimensions)
        return [d.embedding for d in sorted(r.data, key=lambda d: d.index)]


embedding_service = EmbeddingService()


# ── Local embedding functions ─────────────────────────────────

def _tokenize(text: str) -> list[str]:
    """Tokenize Chinese + English text into features."""
    text = text.lower().strip()
    tokens: list[str] = []

    # Chinese bigrams (best for semantic matching)
    chinese = []
    for c in text:
        if '一' <= c <= '鿿':
            chinese.append(c)
        elif chinese:
            # Process accumulated Chinese chars
            for i in range(len(chinese) - 1):
                tokens.append(f'c{chinese[i]}{chinese[i+1]}')
            for c in chinese:
                tokens.append(f'c{c}')
            chinese = []
    if chinese:
        for i in range(len(chinese) - 1):
            tokens.append(f'c{chinese[i]}{chinese[i+1]}')
        for c in chinese:
            tokens.append(f'c{c}')

    # English words
    words = re.findall(r'[a-z0-9]+', text)
    for w in words:
        if len(w) > 1:
            tokens.append(f'w{w}')
    # Word bigrams
    for i in range(len(words) - 1):
        tokens.append(f'b{words[i]}+{words[i+1]}')

    return tokens


def _make_vector(text: str, dims: int) -> list[float]:
    """Create a dense vector from text tokens using hashing."""
    tokens = _tokenize(text)
    if not tokens:
        return [0.0] * dims

    vector = [0.0] * dims
    # Count token frequency
    counts: dict[str, int] = {}
    for t in tokens:
        counts[t] = counts.get(t, 0) + 1

    for t, count in counts.items():
        h = int(hashlib.md5(t.encode()).hexdigest(), 16)
        # Use log-scaled count (like sublinear TF)
        vector[h % dims] += math.log(1 + count)

    # L2 normalize
    norm = math.sqrt(sum(v * v for v in vector))
    if norm > 0:
        vector = [v / norm for v in vector]

    return vector


def _tfidf_batch(texts: list[str], dims: int) -> list[list[float]]:
    """Compute TF-IDF vectors for a batch of texts."""
    import numpy as np

    # Compute document frequencies across the batch
    all_tokens = [_tokenize(t) for t in texts]
    doc_count = len(texts)

    # Compute IDF for each token
    df: dict[str, int] = {}
    for tokens in all_tokens:
        for t in set(tokens):
            df[t] = df.get(t, 0) + 1

    results: list[list[float]] = []
    for tokens in all_tokens:
        vector = [0.0] * dims
        counts: dict[str, int] = {}
        for t in tokens:
            counts[t] = counts.get(t, 0) + 1

        for t, count in counts.items():
            tf = math.log(1 + count)
            idf = math.log((doc_count + 1) / (df.get(t, 1) + 0.5))
            weight = tf * idf
            h = int(hashlib.md5(t.encode()).hexdigest(), 16)
            vector[h % dims] += weight

        norm = math.sqrt(sum(v * v for v in vector))
        if norm > 0:
            vector = [v / norm for v in vector]

        results.append(vector)

    return results
