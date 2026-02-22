"""
CodeQuery API – FastAPI application entry point.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import repositories, questions, analysis
from app.config import settings
from app.database import engine, Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create tables on startup (dev convenience; use Alembic in prod)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "AI-Powered Code Intelligence API – ingest GitHub repositories "
        "and ask natural-language questions about the code using RAG."
    ),
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ─────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────
app.include_router(
    repositories.router, prefix="/api/v1", tags=["Repositories"]
)
app.include_router(
    questions.router, prefix="/api/v1", tags=["Questions"]
)
app.include_router(
    analysis.router, prefix="/api/v1", tags=["Analysis"]
)


# ── Root redirect to docs ────────────────────────────────
@app.get("/", include_in_schema=False)
async def root():
    return {
        "message": "Welcome to CodeQuery API",
        "docs": "/docs",
        "version": settings.APP_VERSION,
    }
