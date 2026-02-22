"""
SQLAlchemy model for the `code_chunks` table.
Stores parsed code fragments and their vector embeddings for RAG retrieval.
"""

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, CheckConstraint, func
)
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from app.database import Base
from app.config import settings


class CodeChunk(Base):
    __tablename__ = "code_chunks"

    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(
        Integer,
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Code metadata ────────────────────────────────────
    file_path = Column(Text, nullable=False)
    chunk_text = Column(Text, nullable=False)
    chunk_type = Column(
        String(50), nullable=True
    )  # function | class | import | block
    line_start = Column(Integer, nullable=True)
    line_end = Column(Integer, nullable=True)
    language = Column(String(50), nullable=True)

    # ── Vector embedding (pgvector) ──────────────────────
    embedding = Column(
        Vector(settings.EMBEDDING_DIMENSION), nullable=True
    )

    # ── Timestamps ───────────────────────────────────────
    created_at = Column(
        DateTime, nullable=False, server_default=func.now()
    )

    # ── Constraints ──────────────────────────────────────
    __table_args__ = (
        CheckConstraint(
            "line_start <= line_end",
            name="valid_lines",
        ),
    )

    # ── Relationships ────────────────────────────────────
    repository = relationship("Repository", back_populates="code_chunks")

    def __repr__(self) -> str:
        return (
            f"<CodeChunk(id={self.id}, file='{self.file_path}', "
            f"type='{self.chunk_type}')>"
        )
