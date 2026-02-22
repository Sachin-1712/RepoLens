"""
SQLAlchemy model for the `repositories` table.
Tracks every Git repository that has been submitted for analysis.
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, JSON, func
)
from sqlalchemy.orm import relationship
from app.database import Base


class Repository(Base):
    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    repo_url = Column(Text, nullable=False, unique=True)
    branch = Column(String(100), nullable=False, default="main")
    description = Column(Text, nullable=True)

    # ── Status tracking ──────────────────────────────────
    # pending → analyzing → ready | failed
    status = Column(
        String(50),
        nullable=False,
        default="pending",
        index=True,
    )

    # ── Metadata populated after analysis ────────────────
    total_files = Column(Integer, default=0)
    total_lines = Column(Integer, default=0)
    languages = Column(JSON, default=dict)

    # ── Timestamps ───────────────────────────────────────
    analyzed_at = Column(DateTime, nullable=True)
    created_at = Column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # ── Relationships ────────────────────────────────────
    code_chunks = relationship(
        "CodeChunk",
        back_populates="repository",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    questions = relationship(
        "Question",
        back_populates="repository",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    analysis_jobs = relationship(
        "AnalysisJob",
        back_populates="repository",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Repository(id={self.id}, name='{self.name}', status='{self.status}')>"
