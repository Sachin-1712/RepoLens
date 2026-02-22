"""
Pydantic schemas for analysis-related responses.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel


class AnalysisStatusResponse(BaseModel):
    """Response for GET /repos/{id}/analysis."""

    repository_id: int
    status: str
    job_id: Optional[str] = None
    progress_percentage: int = 0
    current_step: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class LanguageDetail(BaseModel):
    files: int
    lines: int
    percentage: float


class CodeStatistics(BaseModel):
    total_files: int = 0
    total_lines: int = 0
    total_functions: int = 0
    total_classes: int = 0
    languages: Dict[str, LanguageDetail] = {}


class UsageStatistics(BaseModel):
    total_questions_asked: int = 0
    average_response_time_ms: Optional[float] = None


class RepositoryStatisticsResponse(BaseModel):
    """Response for GET /repos/{id}/statistics."""

    repository_id: int
    code_statistics: CodeStatistics
    usage_statistics: UsageStatistics


class HealthResponse(BaseModel):
    """Response for GET /health."""

    status: str
    timestamp: datetime
    services: Dict[str, str]
    version: str
