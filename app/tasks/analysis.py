"""
Celery background task: full repository analysis pipeline.

Steps:
  1. Clone the repository
  2. Discover code files
  3. Parse & chunk each file
  4. Generate vector embeddings
  5. Store chunks + embeddings in PostgreSQL
  6. Update repository status → ready
"""

import logging
from datetime import datetime, timezone

from celery import Celery
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.config import settings

logger = logging.getLogger(__name__)

# ── Celery app ───────────────────────────────────────────
celery_app = Celery(
    "codequery",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    worker_prefetch_multiplier=1,  # one task at a time per worker
)

# ── Sync engine (Celery workers are synchronous) ─────────
sync_engine = create_engine(settings.DATABASE_URL_SYNC, echo=False)
SyncSessionLocal = sessionmaker(bind=sync_engine, expire_on_commit=False)


@celery_app.task(bind=True, name="analyze_repository")
def analyze_repository_task(self, repo_id: int) -> dict:
    """Celery task that runs the full analysis pipeline."""
    # Lazy imports to avoid circular deps
    from app.models.repository import Repository
    from app.models.code_chunk import CodeChunk
    from app.models.analysis_job import AnalysisJob
    from app.services.ingestion import IngestionService
    from app.services.chunking import ChunkingService
    from app.services.embedding import EmbeddingService
    from pathlib import Path

    db: Session = SyncSessionLocal()
    clone_dir: str | None = None

    try:
        # ── Fetch repo ───────────────────────────────────
        repo = db.query(Repository).filter(Repository.id == repo_id).first()
        if not repo:
            raise ValueError(f"Repository {repo_id} not found")

        # ── Create / update analysis job ─────────────────
        job = AnalysisJob(
            repository_id=repo_id,
            status="processing",
            task_id=self.request.id,
            progress_percentage=0,
            started_at=datetime.now(timezone.utc),
        )
        db.add(job)
        repo.status = "analyzing"
        db.commit()

        # ── Step 1: Clone ────────────────────────────────
        self.update_state(
            state="PROGRESS",
            meta={"step": "cloning", "progress": 10},
        )
        job.progress_percentage = 10
        db.commit()

        clone_dir = IngestionService.clone_repository(
            repo.repo_url, repo.branch
        )
        repo_root = Path(clone_dir)

        # ── Step 2: Discover files ───────────────────────
        self.update_state(
            state="PROGRESS",
            meta={"step": "discovering", "progress": 20},
        )
        job.progress_percentage = 20
        db.commit()

        code_files = IngestionService.discover_code_files(clone_dir)

        # ── Step 3: Chunk ────────────────────────────────
        self.update_state(
            state="PROGRESS",
            meta={"step": "chunking", "progress": 40},
        )
        job.progress_percentage = 40
        db.commit()

        all_chunks = []
        for fpath in code_files:
            chunks = ChunkingService.chunk_file(fpath, repo_root)
            all_chunks.extend(chunks)

        logger.info("Total chunks: %d", len(all_chunks))

        # ── Step 4: Embed ────────────────────────────────
        self.update_state(
            state="PROGRESS",
            meta={"step": "embedding", "progress": 60},
        )
        job.progress_percentage = 60
        db.commit()

        texts = [c.chunk_text for c in all_chunks]
        embeddings = EmbeddingService.generate_embeddings_batch(texts)

        # ── Step 5: Store ────────────────────────────────
        self.update_state(
            state="PROGRESS",
            meta={"step": "storing", "progress": 85},
        )
        job.progress_percentage = 85
        db.commit()

        for chunk_data, emb in zip(all_chunks, embeddings):
            db_chunk = CodeChunk(
                repository_id=repo_id,
                file_path=chunk_data.file_path,
                chunk_text=chunk_data.chunk_text,
                chunk_type=chunk_data.chunk_type,
                line_start=chunk_data.line_start,
                line_end=chunk_data.line_end,
                language=chunk_data.language,
                embedding=emb,
            )
            db.add(db_chunk)

        # ── Step 6: Finalise ─────────────────────────────
        repo.status = "ready"
        repo.total_files = len(code_files)
        repo.total_lines = sum(
            c.line_end - c.line_start + 1 for c in all_chunks
        )
        repo.analyzed_at = datetime.now(timezone.utc)

        job.status = "completed"
        job.progress_percentage = 100
        job.completed_at = datetime.now(timezone.utc)
        db.commit()

        logger.info("Analysis complete for repo %d", repo_id)
        return {"status": "completed", "repo_id": repo_id}

    except Exception as exc:
        logger.exception("Analysis failed for repo %d", repo_id)
        repo = db.query(Repository).filter(Repository.id == repo_id).first()
        if repo:
            repo.status = "failed"

        # Update job if it exists
        job_q = (
            db.query(AnalysisJob)
            .filter(AnalysisJob.repository_id == repo_id)
            .order_by(AnalysisJob.created_at.desc())
            .first()
        )
        if job_q:
            job_q.status = "failed"
            job_q.error_message = str(exc)

        db.commit()
        raise

    finally:
        db.close()
        if clone_dir:
            IngestionService.cleanup(clone_dir)
