"""
Embedding service – generates vector embeddings for code chunks.

Uses the free `sentence-transformers/all-MiniLM-L6-v2` model by default
(384-dimensional vectors). Can be swapped to OpenAI by setting OPENAI_API_KEY.
"""

import logging
from typing import List

from app.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Generate vector embeddings using a free HuggingFace model."""

    _model = None  # lazy-loaded singleton

    @classmethod
    def _get_model(cls):
        """Lazy-load the sentence-transformers model."""
        if cls._model is None:
            from sentence_transformers import SentenceTransformer

            logger.info(
                "Loading embedding model: %s", settings.EMBEDDING_MODEL
            )
            cls._model = SentenceTransformer(settings.EMBEDDING_MODEL)
            logger.info("Embedding model loaded successfully")
        return cls._model

    @classmethod
    def generate_embedding(cls, text: str) -> List[float]:
        """Generate a single embedding vector."""
        model = cls._get_model()
        embedding = model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    @classmethod
    def generate_embeddings_batch(
        cls,
        texts: List[str],
        batch_size: int = 64,
    ) -> List[List[float]]:
        """Generate embeddings for a batch of texts."""
        model = cls._get_model()
        logger.info("Generating embeddings for %d texts", len(texts))

        all_embeddings: List[List[float]] = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            embeddings = model.encode(
                batch, normalize_embeddings=True, show_progress_bar=False
            )
            all_embeddings.extend(embeddings.tolist())

            logger.debug(
                "Embedded batch %d/%d",
                i // batch_size + 1,
                (len(texts) + batch_size - 1) // batch_size,
            )

        return all_embeddings

    @classmethod
    def dimension(cls) -> int:
        """Return the embedding dimension."""
        return settings.EMBEDDING_DIMENSION
