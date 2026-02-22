"""
IngestionService – handles the git clone + analysis pipeline.

The public method `queue_analysis` dispatches the heavy work to a Celery
background worker, keeping the API responsive.
"""

import logging
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import BackgroundTasks


import git  # GitPython
from sqlalchemy.orm import Session

from app.config import settings

logger = logging.getLogger(__name__)


class IngestionService:
    """Orchestrates repository cloning, parsing, and embedding."""

    # ── Public API ───────────────────────────────────────

    @staticmethod
    def queue_analysis(repo_id: int, background_tasks: Optional['BackgroundTasks'] = None) -> Optional[str]:
        """
        Dispatch a background Celery task to analyse a repository.
        Returns the Celery task ID, or "local-task" if Celery is unavailable.
        """
        # Lightweight mode: if REDIS_URL has a specific placeholder or we just force local,
        # but the cleanest way is to try celery and fallback to background_tasks on ConnectionError
        from app.tasks.analysis import analyze_repository_task
        
        try:
            # Try to ping Celery or just call delay. 
            # If redis is down, .delay() might still just queue it locally if configured so, 
            # but usually it raises an OperationalError if it can't connect.
            # To be strictly lightweight and avoid hangs:
            import redis
            # Check redis connection directly:
            r = redis.from_url(settings.REDIS_URL, socket_connect_timeout=1)
            r.ping()
            
            result = analyze_repository_task.delay(repo_id)
            logger.info("Queued analysis for repo %s → task %s", repo_id, result.id)
            return result.id
        except Exception as exc:
            logger.info("Celery/Redis unavailable. Running ingestion in background API process: %s", exc)
            if background_tasks is not None:
                background_tasks.add_task(analyze_repository_task, repo_id)
            else:
                analyze_repository_task(repo_id)
            return "local-task"

    # ── Clone logic ──────────────────────────────────────

    @staticmethod
    def clone_repository(repo_url: str, branch: str = "main") -> str:
        """
        Clone a Git repository to a temporary directory.
        Returns the path to the cloned repo.
        """
        clone_base = settings.CLONE_DIR
        os.makedirs(clone_base, exist_ok=True)

        # Create a unique directory for this clone
        clone_dir = tempfile.mkdtemp(dir=clone_base)

        logger.info("Cloning %s (branch: %s) → %s", repo_url, branch, clone_dir)

        try:
            git.Repo.clone_from(
                repo_url,
                clone_dir,
                branch=branch,
                depth=1,  # shallow clone for speed
            )
            logger.info("Clone complete: %s", clone_dir)
            return clone_dir
        except git.exc.GitCommandError as exc:
            logger.error("Git clone failed: %s", exc)
            # Clean up on failure
            shutil.rmtree(clone_dir, ignore_errors=True)
            raise RuntimeError(f"Failed to clone repository: {exc}") from exc

    # ── Cleanup ──────────────────────────────────────────

    @staticmethod
    def cleanup(clone_dir: str) -> None:
        """Remove a cloned repo directory."""
        if clone_dir and os.path.isdir(clone_dir):
            shutil.rmtree(clone_dir, ignore_errors=True)
            logger.info("Cleaned up: %s", clone_dir)

    # ── File discovery ───────────────────────────────────

    SUPPORTED_EXTENSIONS = {
        ".py", ".js", ".ts", ".jsx", ".tsx",
        ".java", ".cpp", ".c", ".h", ".hpp",
        ".go", ".rs", ".rb", ".php", ".swift",
        ".kt", ".scala", ".cs",
    }

    IGNORED_DIRS = {
        ".git", "node_modules", "__pycache__", "venv", ".venv",
        "dist", "build", ".next", ".tox", "env", ".eggs",
    }

    @classmethod
    def discover_code_files(cls, repo_path: str) -> list[Path]:
        """Walk the repo and return paths of supported source files."""
        code_files: list[Path] = []
        root = Path(repo_path)

        for dirpath, dirnames, filenames in os.walk(root):
            # Prune ignored directories in-place
            dirnames[:] = [
                d for d in dirnames if d not in cls.IGNORED_DIRS
            ]

            for fname in filenames:
                fpath = Path(dirpath) / fname
                if fpath.suffix in cls.SUPPORTED_EXTENSIONS:
                    code_files.append(fpath)

        logger.info(
            "Discovered %d code files in %s", len(code_files), repo_path
        )
        return code_files

    # ── Read file content ────────────────────────────────

    @staticmethod
    def read_file_safe(file_path: Path) -> Optional[str]:
        """Read a file, returning None if binary or unreadable."""
        try:
            return file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as exc:
            logger.warning("Could not read %s: %s", file_path, exc)
            return None
