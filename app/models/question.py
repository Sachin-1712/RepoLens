"""
SQLAlchemy model for the `questions` table.
Stores every Q&A interaction and the RAG-generated answer with source citations.
"""

from sqlalchemy import (
    Column, Integer, String, Text, Float, DateTime, JSON, ForeignKey, func
)
from sqlalchemy.orm import relationship
from app.database import Base


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(
        Integer,
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Q&A content ──────────────────────────────────────
    question_text = Column(Text, nullable=False)
    answer_text = Column(Text, nullable=True)

    # ── Quality metrics ──────────────────────────────────
    confidence_score = Column(Float, nullable=True)
    sources = Column(JSON, default=list)  # [{file, line_start, line_end, relevance}]
    model_used = Column(String(100), nullable=True)
    processing_time_ms = Column(Integer, nullable=True)

    # ── Timestamps ───────────────────────────────────────
    created_at = Column(
        DateTime, nullable=False, server_default=func.now()
    )

    # ── Relationships ────────────────────────────────────
    repository = relationship("Repository", back_populates="questions")

    def __repr__(self) -> str:
        return (
            f"<Question(id={self.id}, repo_id={self.repository_id}, "
            f"q='{self.question_text[:40]}...')>"
        )
