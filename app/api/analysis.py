"""
Analysis & health endpoints.

GET /repositories/{id}/analysis    – Get analysis job status
GET /repositories/{id}/statistics  – Get code statistics
GET /health                        – Service health check
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.analysis_job import AnalysisJob
from app.models.code_chunk import CodeChunk
from app.models.question import Question
from app.models.repository import Repository
from app.schemas.analysis import (
    AnalysisStatusResponse,
    CodeStatistics,
    HealthResponse,
    RepositoryStatisticsResponse,
    UsageStatistics,
)

router = APIRouter(tags=["Analysis"])


# ─── GET /repositories/{id}/analysis ────────────────────

@router.get(
    "/repositories/{repo_id}/analysis",
    response_model=AnalysisStatusResponse,
    summary="Get analysis job status for a repository",
)
async def get_analysis_status(
    repo_id: int,
    db: AsyncSession = Depends(get_db),
) -> AnalysisStatusResponse:
    # Fetch the latest job for this repo
    result = await db.execute(
        select(AnalysisJob)
        .where(AnalysisJob.repository_id == repo_id)
        .order_by(AnalysisJob.created_at.desc())
        .limit(1)
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "No analysis job found for this repository",
                "repository_id": repo_id,
            },
        )

    return AnalysisStatusResponse(
        repository_id=repo_id,
        status=job.status,
        job_id=job.task_id,
        progress_percentage=job.progress_percentage,
        error_message=job.error_message,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )


# ─── GET /repositories/{id}/statistics ──────────────────

@router.get(
    "/repositories/{repo_id}/statistics",
    response_model=RepositoryStatisticsResponse,
    summary="Get code statistics for a repository",
)
async def get_statistics(
    repo_id: int,
    db: AsyncSession = Depends(get_db),
) -> RepositoryStatisticsResponse:
    # Verify repo exists
    result = await db.execute(
        select(Repository).where(Repository.id == repo_id)
    )
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Repository not found", "repository_id": repo_id},
        )

    # Count functions and classes
    func_count = (
        await db.execute(
            select(sa_func.count())
            .select_from(CodeChunk)
            .where(
                CodeChunk.repository_id == repo_id,
                CodeChunk.chunk_type == "function",
            )
        )
    ).scalar() or 0

    class_count = (
        await db.execute(
            select(sa_func.count())
            .select_from(CodeChunk)
            .where(
                CodeChunk.repository_id == repo_id,
                CodeChunk.chunk_type == "class",
            )
        )
    ).scalar() or 0

    # Question usage stats
    q_count = (
        await db.execute(
            select(sa_func.count())
            .select_from(Question)
            .where(Question.repository_id == repo_id)
        )
    ).scalar() or 0

    avg_time = (
        await db.execute(
            select(sa_func.avg(Question.processing_time_ms)).where(
                Question.repository_id == repo_id
            )
        )
    ).scalar()

    return RepositoryStatisticsResponse(
        repository_id=repo_id,
        code_statistics=CodeStatistics(
            total_files=repo.total_files,
            total_lines=repo.total_lines,
            total_functions=func_count,
            total_classes=class_count,
            languages={},
        ),
        usage_statistics=UsageStatistics(
            total_questions_asked=q_count,
            average_response_time_ms=float(avg_time) if avg_time else None,
        ),
    )


# ─── GET /health ────────────────────────────────────────

@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service health check",
)
async def health_check(
    db: AsyncSession = Depends(get_db),
) -> HealthResponse:
    # Check database connectivity
    db_status = "connected"
    try:
        await db.execute(select(sa_func.now()))
    except Exception:
        db_status = "disconnected"

    return HealthResponse(
        status="healthy" if db_status == "connected" else "degraded",
        timestamp=datetime.now(timezone.utc),
        services={
            "database": db_status,
            "redis": "connected",  # TODO: actual ping
            "ai_service": "available",
        },
        version=settings.APP_VERSION,
    )
