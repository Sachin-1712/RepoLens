"""
Repository CRUD endpoints.

POST   /repos          – Create a new repository and queue analysis
GET    /repos          – List all repositories (with filters & pagination)
GET    /repos/{id}     – Get a single repository
PUT    /repos/{id}     – Update / re-analyse a repository
DELETE /repos/{id}     – Delete a repository and all associated data
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.repository import Repository
from app.models.code_chunk import CodeChunk
from app.models.question import Question
from app.schemas.repository import (
    RepositoryCreate,
    RepositoryCreateResponse,
    RepositoryDeleteResponse,
    RepositoryListResponse,
    RepositoryResponse,
    RepositoryUpdate,
)
from app.services.ingestion import IngestionService

router = APIRouter(prefix="/repositories", tags=["Repositories"])


# ─── POST /repositories ─────────────────────────────────

@router.post(
    "",
    response_model=RepositoryCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Add a new repository for analysis",
)
async def create_repository(
    payload: RepositoryCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> RepositoryCreateResponse:
    # Check for duplicates
    result = await db.execute(
        select(Repository).where(Repository.repo_url == payload.repo_url)
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "Repository already exists",
                "repository_id": existing.id,
            },
        )

    # Derive name from URL if not provided
    repo_name = payload.name or payload.repo_url.rstrip("/").split("/")[-1]

    new_repo = Repository(
        name=repo_name,
        repo_url=payload.repo_url,
        branch=payload.branch,
        status="pending",
    )
    db.add(new_repo)
    await db.flush()  # get the ID
    await db.refresh(new_repo)

    # Queue the background ingestion job
    job_id = IngestionService.queue_analysis(new_repo.id, background_tasks)

    return RepositoryCreateResponse(
        **RepositoryResponse.model_validate(new_repo).model_dump(),
        message="Repository analysis job queued",
        job_id=job_id,
    )


# ─── GET /repositories ──────────────────────────────────

@router.get(
    "",
    response_model=RepositoryListResponse,
    summary="List all repositories",
)
async def list_repositories(
    status_filter: Optional[str] = Query(
        None, alias="status", description="Filter by status"
    ),
    search: Optional[str] = Query(None, description="Search by name or URL"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> RepositoryListResponse:
    query = select(Repository)

    if status_filter:
        query = query.where(Repository.status == status_filter)
    if search:
        query = query.where(
            Repository.name.ilike(f"%{search}%")
            | Repository.repo_url.ilike(f"%{search}%")
        )

    # Count total
    count_query = select(sa_func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Fetch page
    query = query.order_by(Repository.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    repos = result.scalars().all()

    return RepositoryListResponse(
        total=total,
        limit=limit,
        offset=offset,
        repositories=[RepositoryResponse.model_validate(r) for r in repos],
    )


# ─── GET /repositories/{id} ─────────────────────────────

@router.get(
    "/{repo_id}",
    response_model=RepositoryResponse,
    summary="Get repository details",
)
async def get_repository(
    repo_id: int,
    db: AsyncSession = Depends(get_db),
) -> RepositoryResponse:
    result = await db.execute(
        select(Repository).where(Repository.id == repo_id)
    )
    repo = result.scalar_one_or_none()

    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Repository not found", "repository_id": repo_id},
        )

    return RepositoryResponse.model_validate(repo)


# ─── PUT /repositories/{id} ─────────────────────────────

@router.put(
    "/{repo_id}",
    response_model=RepositoryCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Update or re-analyse a repository",
)
async def update_repository(
    repo_id: int,
    payload: RepositoryUpdate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> RepositoryCreateResponse:
    result = await db.execute(
        select(Repository).where(Repository.id == repo_id)
    )
    repo = result.scalar_one_or_none()

    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Repository not found", "repository_id": repo_id},
        )

    if payload.name:
        repo.name = payload.name
    if payload.branch:
        repo.branch = payload.branch

    job_id = None
    message = "Repository updated"
    if payload.action == "reanalyze":
        repo.status = "pending"
        job_id = IngestionService.queue_analysis(repo.id, background_tasks)
        message = "Re-analysis job queued"

    await db.flush()
    await db.refresh(repo)

    return RepositoryCreateResponse(
        **RepositoryResponse.model_validate(repo).model_dump(),
        message=message,
        job_id=job_id,
    )


# ─── DELETE /repositories/{id} ──────────────────────────

@router.delete(
    "/{repo_id}",
    response_model=RepositoryDeleteResponse,
    summary="Delete a repository and all associated data",
)
async def delete_repository(
    repo_id: int,
    db: AsyncSession = Depends(get_db),
) -> RepositoryDeleteResponse:
    result = await db.execute(
        select(Repository).where(Repository.id == repo_id)
    )
    repo = result.scalar_one_or_none()

    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Repository not found", "repository_id": repo_id},
        )

    # Count related objects before deleting (for the response)
    chunks_count = (
        await db.execute(
            select(sa_func.count())
            .select_from(CodeChunk)
            .where(CodeChunk.repository_id == repo_id)
        )
    ).scalar() or 0

    questions_count = (
        await db.execute(
            select(sa_func.count())
            .select_from(Question)
            .where(Question.repository_id == repo_id)
        )
    ).scalar() or 0

    await db.delete(repo)

    return RepositoryDeleteResponse(
        message="Repository and all associated data deleted successfully",
        repository_id=repo_id,
        deleted_items={
            "code_chunks": chunks_count,
            "questions": questions_count,
        },
    )
