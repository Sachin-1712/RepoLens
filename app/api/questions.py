"""
Question / QA endpoints.

POST   /repositories/{id}/questions  – Ask a question about a repo
GET    /repositories/{id}/questions  – Get question history for a repo
GET    /questions/{id}               – Get a single question with full answer
DELETE /questions/{id}               – Delete a question
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.question import Question
from app.models.repository import Repository
from app.schemas.question import (
    QuestionCreate,
    QuestionDeleteResponse,
    QuestionListResponse,
    QuestionResponse,
    SourceReference,
)

router = APIRouter(tags=["Questions"])


# ─── helpers ─────────────────────────────────────────────

def _to_response(q: Question) -> QuestionResponse:
    """Map ORM question → Pydantic response."""
    sources = []
    if q.sources:
        for s in q.sources:
            sources.append(SourceReference(
                file=s.get("file", ""),
                line_start=s.get("line_start", 0),
                line_end=s.get("line_end", 0),
                relevance_score=s.get("relevance_score", 0.0),
                snippet=s.get("snippet"),
            ))

    return QuestionResponse(
        question_id=q.id,
        repository_id=q.repository_id,
        question=q.question_text,
        answer=q.answer_text,
        confidence_score=q.confidence_score,
        sources=sources,
        model_used=q.model_used,
        processing_time_ms=q.processing_time_ms,
        created_at=q.created_at,
    )


# ─── POST /repositories/{repo_id}/questions ─────────────

@router.post(
    "/repositories/{repo_id}/questions",
    response_model=QuestionResponse,
    summary="Ask a question about a repository",
)
async def ask_question(
    repo_id: int,
    payload: QuestionCreate,
    db: AsyncSession = Depends(get_db),
) -> QuestionResponse:
    # Verify repository exists and is ready
    result = await db.execute(
        select(Repository).where(Repository.id == repo_id)
    )
    repo = result.scalar_one_or_none()

    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Repository not found", "repository_id": repo_id},
        )

    if repo.status != "ready":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Repository not ready for questions",
                "status": repo.status,
                "message": "Please wait for analysis to complete",
            },
        )

    from app.services.qa_engine import QAEngine
    
    qa_engine = QAEngine(db)
    qa_result = await qa_engine.answer(repo_id, payload.question)

    new_question = Question(
        repository_id=repo_id,
        question_text=payload.question,
        answer_text=qa_result["answer"] or "LLM generation failed.",
        confidence_score=qa_result["confidence_score"],
        sources=qa_result["sources"],
        model_used=qa_result["model_used"],
        processing_time_ms=qa_result["processing_time_ms"],
    )
    db.add(new_question)
    await db.commit()
    await db.refresh(new_question)

    if qa_result.get("error"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "Local LLM is unavailable (running in lightweight mode).",
                "sources_retrieved": qa_result["sources"],
            }
        )

    return _to_response(new_question)


# ─── GET /repositories/{repo_id}/questions ───────────────

@router.get(
    "/repositories/{repo_id}/questions",
    response_model=QuestionListResponse,
    summary="List question history for a repository",
)
async def list_questions(
    repo_id: int,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> QuestionListResponse:
    base = select(Question).where(Question.repository_id == repo_id)

    total = (
        await db.execute(
            select(sa_func.count()).select_from(base.subquery())
        )
    ).scalar() or 0

    result = await db.execute(
        base.order_by(Question.created_at.desc()).offset(offset).limit(limit)
    )
    questions = result.scalars().all()

    return QuestionListResponse(
        total=total,
        limit=limit,
        offset=offset,
        questions=[_to_response(q) for q in questions],
    )


# ─── GET /questions/{question_id} ────────────────────────

@router.get(
    "/questions/{question_id}",
    response_model=QuestionResponse,
    summary="Get a single question with full answer",
)
async def get_question(
    question_id: int,
    db: AsyncSession = Depends(get_db),
) -> QuestionResponse:
    result = await db.execute(
        select(Question).where(Question.id == question_id)
    )
    question = result.scalar_one_or_none()

    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Question not found", "question_id": question_id},
        )

    return _to_response(question)


# ─── DELETE /questions/{question_id} ─────────────────────

@router.delete(
    "/questions/{question_id}",
    response_model=QuestionDeleteResponse,
    summary="Delete a question",
)
async def delete_question(
    question_id: int,
    db: AsyncSession = Depends(get_db),
) -> QuestionDeleteResponse:
    result = await db.execute(
        select(Question).where(Question.id == question_id)
    )
    question = result.scalar_one_or_none()

    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Question not found", "question_id": question_id},
        )

    await db.delete(question)

    return QuestionDeleteResponse(
        message="Question deleted successfully",
        question_id=question_id,
    )
