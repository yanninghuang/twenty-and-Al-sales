"""Vector store service — uses pgvector on PostgreSQL, Python cosine on SQLite."""

import json
import math

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _parse_embedding(raw) -> list[float] | None:
    """Parse embedding from DB storage (JSON string or list)."""
    if raw is None:
        return None
    if isinstance(raw, list):
        return [float(x) for x in raw]
    if isinstance(raw, str):
        try:
            return [float(x) for x in json.loads(raw)]
        except (json.JSONDecodeError, TypeError):
            # Try pgvector-style "[1,2,3]" format
            try:
                return [float(x) for x in raw.strip("[]").split(",")]
            except (ValueError, TypeError):
                return None
    return None


class VectorStore:
    """Handles vector CRUD and similarity search — SQLite and PostgreSQL compatible."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._use_sqlite = "sqlite" in str(session.bind.url) if session.bind else True

    async def search_similar(
        self,
        table_name: str,
        query_embedding: list[float],
        workspace_id: str,
        top_k: int = 5,
        additional_filters: dict | None = None,
    ) -> list[dict]:
        """Search for similar items. On SQLite, fetches all candidates and ranks in Python."""
        if self._use_sqlite:
            return await self._search_sqlite(
                table_name, query_embedding, workspace_id, top_k, additional_filters
            )
        else:
            return await self._search_pgvector(
                table_name, query_embedding, workspace_id, top_k, additional_filters
            )

    async def _search_sqlite(
        self,
        table_name: str,
        query_embedding: list[float],
        workspace_id: str,
        top_k: int = 5,
        additional_filters: dict | None = None,
    ) -> list[dict]:
        """Python-based cosine similarity search for SQLite."""
        # Fetch all records for the workspace with non-null embeddings
        where_parts = ["workspace_id = :workspace_id", "embedding IS NOT NULL"]
        params: dict = {"workspace_id": workspace_id}

        if additional_filters:
            for key, value in additional_filters.items():
                where_parts.append(f"{key} = :{key}")
                params[key] = value

        where_clause = " AND ".join(where_parts)
        query_str = f"SELECT id, content, embedding FROM {table_name} WHERE {where_clause}"

        result = await self.session.execute(text(query_str), params)
        rows = result.fetchall()

        # Rank by cosine similarity in Python
        scored: list[tuple[float, dict]] = []
        for row in rows:
            emb = _parse_embedding(row[2])
            if emb:
                sim = _cosine_similarity(query_embedding, emb)
                scored.append((sim, {"id": str(row[0]), "content": row[1], "similarity": sim}))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:top_k] if item["similarity"] > 0.05]

    async def _search_pgvector(
        self,
        table_name: str,
        query_embedding: list[float],
        workspace_id: str,
        top_k: int = 5,
        additional_filters: dict | None = None,
    ) -> list[dict]:
        """pgvector-based cosine similarity search for PostgreSQL."""
        embedding_str = f"[{','.join(map(str, query_embedding))}]"

        filter_clause = "WHERE workspace_id = :workspace_id"
        params: dict = {
            "workspace_id": workspace_id,
            "embedding": embedding_str,
            "top_k": top_k,
        }

        if additional_filters:
            for key, value in additional_filters.items():
                filter_clause += f" AND {key} = :{key}"
                params[key] = value

        query_str = f"""
            SELECT id, content,
                   1 - (embedding <=> :embedding) AS similarity
            FROM {table_name}
            {filter_clause}
            ORDER BY embedding <=> :embedding
            LIMIT :top_k
        """
        result = await self.session.execute(text(query_str), params)
        rows = result.fetchall()
        return [
            {"id": str(row[0]), "content": row[1], "similarity": float(row[2])}
            for row in rows
        ]

    async def upsert_embedding(
        self, table_name: str, record_id: str, embedding: list[float]
    ) -> None:
        """Update embedding for a record."""
        emb_str = json.dumps(embedding)
        query_str = f"UPDATE {table_name} SET embedding = :embedding WHERE id = :id"
        await self.session.execute(text(query_str), {"embedding": emb_str, "id": record_id})
        await self.session.commit()

    async def bulk_insert_chunks(
        self, table_name: str, rows: list[dict]
    ) -> None:
        """Insert multiple rows with embeddings."""
        if not rows:
            return

        for row in rows:
            columns = list(row.keys())
            placeholders = [f":{col}" for col in columns]
            params = {}
            for col in columns:
                val = row[col]
                if col == "embedding":
                    if isinstance(val, list):
                        val = json.dumps(val)
                    elif val is not None:
                        val = str(val)
                params[col] = val

            query_str = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
            await self.session.execute(text(query_str), params)

        await self.session.commit()
