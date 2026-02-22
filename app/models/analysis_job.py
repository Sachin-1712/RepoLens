"""
SQLAlchemy model for the `analysis_jobs` table.
Tracks the Celery background task progress for repository ingestion.
"""

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, func
)
from sqlalchemy.orm import relationship
from app.database import Base


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"

    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(
        Integer,
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Job tracking ─────────────────────────────────────
    # queued → processing → completed | failed
    status = Column(
        String(50), nullable=False, default="queued", index=True
    )
    task_id = Column(String(255), unique=True, nullable=True)  # Celery task ID
    progress_percentage = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)

    # ── Timestamps ───────────────────────────────────────
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(
        DateTime, nullable=False, server_default=func.now()
    )

    # ── Relationships ────────────────────────────────────
    repository = relationship("Repository", back_populates="analysis_jobs")

    def __repr__(self) -> str:
        return (
            f"<AnalysisJob(id={self.id}, repo_id={self.repository_id}, "
            f"status='{self.status}', progress={self.progress_percentage}%)>"
        )
