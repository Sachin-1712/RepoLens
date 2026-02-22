"""
Pydantic schemas for Repository request/response validation.
"""

from datetime import datetime
from typing import Optional, Dict, List
from pydantic import BaseModel, Field, field_validator


# ── Request Schemas ──────────────────────────────────────

class RepositoryCreate(BaseModel):
    """Schema for POST /repos – creating a new repository."""

    repo_url: str = Field(
        ...,
        description="HTTPS URL of the GitHub repository",
        examples=["https://github.com/pallets/flask"],
    )
    branch: str = Field(
        default="main",
        description="Git branch to analyse",
    )
    name: Optional[str] = Field(
        default=None,
        description="Friendly display name (auto-derived from URL if omitted)",
    )

    @field_validator("repo_url")
    @classmethod
    def validate_github_url(cls, v: str) -> str:
        if not v.startswith("https://github.com/"):
            raise ValueError(
                "Repository URL must start with https://github.com/"
            )
        # Ensure there's at least owner/repo in the path
        parts = v.replace("https://github.com/", "").strip("/").split("/")
        if len(parts) < 2:
            raise ValueError(
                "URL must be in the format https://github.com/<owner>/<repo>"
            )
        return v


class RepositoryUpdate(BaseModel):
    """Schema for PUT /repos/{id} – re-analyse or update metadata."""

    branch: Optional[str] = None
    name: Optional[str] = None
    action: Optional[str] = Field(
        default=None,
        description="Set to 'reanalyze' to trigger a new analysis job",
    )


# ── Response Schemas ─────────────────────────────────────

class RepositoryResponse(BaseModel):
    """Standard repository response."""

    id: int
    name: str
    repo_url: str
    branch: str
    status: str
    description: Optional[str] = None
    total_files: int = 0
    total_lines: int = 0
    languages: Dict[str, int] = {}
    analyzed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RepositoryCreateResponse(RepositoryResponse):
    """Extended response returned on creation, includes job info."""

    message: str = "Repository analysis job queued"
    job_id: Optional[str] = None


class RepositoryListResponse(BaseModel):
    """Paginated list of repositories."""

    total: int
    limit: int
    offset: int
    repositories: List[RepositoryResponse]


class RepositoryDeleteResponse(BaseModel):
    """Response for DELETE /repos/{id}."""

    message: str
    repository_id: int
    deleted_items: Dict[str, int] = {}
