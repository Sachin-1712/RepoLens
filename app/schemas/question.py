"""
Pydantic schemas for Question/QA request/response validation.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ── Request Schemas ──────────────────────────────────────

class QuestionCreate(BaseModel):
    """Schema for POST /repos/{id}/questions."""

    question: str = Field(
        ...,
        min_length=3,
        description="Natural language question about the repository's code",
        examples=["How is authentication implemented in this codebase?"],
    )


# ── Response Schemas ─────────────────────────────────────

class SourceReference(BaseModel):
    """A code chunk that was used to answer the question."""

    file: str
    line_start: int
    line_end: int
    relevance_score: float
    snippet: Optional[str] = None


class QuestionResponse(BaseModel):
    """Full question + answer response."""

    question_id: int
    repository_id: int
    question: str
    answer: Optional[str] = None
    confidence_score: Optional[float] = None
    sources: List[SourceReference] = []
    model_used: Optional[str] = None
    processing_time_ms: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class QuestionListResponse(BaseModel):
    """Paginated list of questions."""

    total: int
    limit: int
    offset: int
    questions: List[QuestionResponse]


class QuestionDeleteResponse(BaseModel):
    """Response for DELETE /questions/{id}."""

    message: str
    question_id: int
