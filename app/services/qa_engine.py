"""
QA Engine – Retrieval-Augmented Generation for code questions.

1. Embed the user's question
2. Find similar code chunks via pgvector cosine similarity
3. Build a prompt with retrieved context
4. Generate an answer using a free local LLM (Ollama) or OpenAI
"""

import logging
import time
from typing import Dict, List, Optional

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.code_chunk import CodeChunk
from app.services.embedding import EmbeddingService

logger = logging.getLogger(__name__)


class QAEngine:
    """RAG-based question answering over code repositories."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def answer(
        self, repo_id: int, question: str
    ) -> Dict:
        """
        Full RAG pipeline:
        question → embedding → retrieval → prompt → LLM → answer
        """
        start = time.perf_counter()

        # 1. Embed the question
        q_embedding = EmbeddingService.generate_embedding(question)

        # 2. Retrieve similar code chunks using pgvector
        relevant_chunks = await self._retrieve_chunks(
            repo_id, q_embedding, top_k=5
        )

        if not relevant_chunks:
            return {
                "answer": (
                    "I couldn't find relevant code in this repository "
                    "to answer your question."
                ),
                "confidence_score": 0.0,
                "sources": [],
                "model_used": "none",
                "processing_time_ms": int(
                    (time.perf_counter() - start) * 1000
                ),
                "error": False,
            }

        # 3. Build the context prompt
        context = self._build_context(relevant_chunks)
        prompt = self._build_prompt(question, context)

        # 4. Generate answer via LLM
        answer_text = await self._generate_answer(prompt)

        elapsed_ms = int((time.perf_counter() - start) * 1000)

        # 5. Build sources list
        sources = [
            {
                "file": chunk["file_path"],
                "line_start": chunk["line_start"],
                "line_end": chunk["line_end"],
                "relevance_score": round(chunk["similarity"], 3),
                "snippet": chunk["chunk_text"][:200],
            }
            for chunk in relevant_chunks
        ]

        return {
            "answer": answer_text,
            "confidence_score": round(
                max(c["similarity"] for c in relevant_chunks), 3
            ),
            "sources": sources,
            "model_used": settings.LLM_MODEL,
            "processing_time_ms": elapsed_ms,
            "error": answer_text is None,
        }

    # ── Retrieval via pgvector ───────────────────────────

    async def _retrieve_chunks(
        self, repo_id: int, query_embedding: List[float], top_k: int = 5
    ) -> List[Dict]:
        """Find the most similar code chunks using cosine distance."""
        embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

        sql = text(
            """
            SELECT
                id, file_path, chunk_text, chunk_type,
                line_start, line_end, language,
                1 - (embedding <=> :embedding::vector) AS similarity
            FROM code_chunks
            WHERE repository_id = :repo_id
              AND embedding IS NOT NULL
            ORDER BY embedding <=> :embedding::vector
            LIMIT :top_k
            """
        )

        result = await self.db.execute(
            sql,
            {
                "repo_id": repo_id,
                "embedding": embedding_str,
                "top_k": top_k,
            },
        )
        rows = result.fetchall()

        return [
            {
                "id": row.id,
                "file_path": row.file_path,
                "chunk_text": row.chunk_text,
                "chunk_type": row.chunk_type,
                "line_start": row.line_start,
                "line_end": row.line_end,
                "language": row.language,
                "similarity": float(row.similarity),
            }
            for row in rows
        ]

    # ── Prompt construction ──────────────────────────────

    @staticmethod
    def _build_context(chunks: List[Dict]) -> str:
        parts: List[str] = []
        for i, chunk in enumerate(chunks, 1):
            parts.append(
                f"--- Source {i}: {chunk['file_path']} "
                f"(lines {chunk['line_start']}-{chunk['line_end']}) ---\n"
                f"{chunk['chunk_text']}\n"
            )
        return "\n".join(parts)

    @staticmethod
    def _build_prompt(question: str, context: str) -> str:
        return f"""You are an expert code analyst. Answer the following question 
about a codebase using ONLY the provided source code context. 
Be specific, reference file names and line numbers when relevant.

CONTEXT:
{context}

QUESTION: {question}

ANSWER:"""

    # ── LLM call (Ollama – free & local) ─────────────────

    async def _generate_answer(self, prompt: str) -> str:
        """Call Ollama API for text generation."""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{settings.OLLAMA_BASE_URL}/api/generate",
                    json={
                        "model": settings.LLM_MODEL,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.2,
                            "num_predict": 512,
                        },
                    },
                )
                response.raise_for_status()
                return response.json().get("response", "No response generated.")
        except httpx.ConnectError as exc:
            logger.warning("LLM connection failed (likely lightweight mode): %s", exc)
            return None
        except Exception as exc:
            logger.error("LLM generation failed: %s", exc)
            return None
