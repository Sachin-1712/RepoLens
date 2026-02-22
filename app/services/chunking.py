"""
Code chunking service – splits source files into meaningful chunks
for embedding and retrieval.
"""

import ast
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class CodeChunkData:
    """Intermediate representation of a parsed code chunk."""

    file_path: str
    chunk_text: str
    chunk_type: str  # function | class | import | block
    line_start: int
    line_end: int
    language: str


class ChunkingService:
    """Parses source files and extracts semantic code chunks."""

    EXTENSION_LANG_MAP = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".jsx": "javascript",
        ".tsx": "typescript",
        ".java": "java",
        ".cpp": "cpp",
        ".c": "c",
        ".h": "c",
        ".hpp": "cpp",
        ".go": "go",
        ".rs": "rust",
        ".rb": "ruby",
        ".php": "php",
        ".swift": "swift",
        ".kt": "kotlin",
        ".scala": "scala",
        ".cs": "csharp",
    }

    CHUNK_SIZE_LINES = 50  # fallback chunk size for generic splitting

    # ── Public ───────────────────────────────────────────

    @classmethod
    def chunk_file(
        cls,
        file_path: Path,
        repo_root: Path,
    ) -> List[CodeChunkData]:
        """
        Parse a single file and return a list of code chunks.
        Uses AST-based extraction for Python; line-based splitting otherwise.
        """
        content = cls._read(file_path)
        if content is None:
            return []

        relative = str(file_path.relative_to(repo_root))
        language = cls.EXTENSION_LANG_MAP.get(file_path.suffix, "unknown")

        if language == "python":
            chunks = cls._extract_python_chunks(relative, content)
        else:
            chunks = cls._extract_generic_chunks(relative, content, language)

        logger.debug(
            "Chunked %s → %d chunks", relative, len(chunks)
        )
        return chunks

    # ── Python-specific AST parsing ──────────────────────

    @classmethod
    def _extract_python_chunks(
        cls, rel_path: str, content: str
    ) -> List[CodeChunkData]:
        chunks: List[CodeChunkData] = []
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return cls._extract_generic_chunks(rel_path, content, "python")

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                chunk_type = "function"
            elif isinstance(node, ast.ClassDef):
                chunk_type = "class"
            else:
                continue

            source = ast.get_source_segment(content, node)
            if source:
                chunks.append(
                    CodeChunkData(
                        file_path=rel_path,
                        chunk_text=source,
                        chunk_type=chunk_type,
                        line_start=node.lineno,
                        line_end=node.end_lineno or node.lineno,
                        language="python",
                    )
                )

        # If no AST nodes found, fall back to generic
        if not chunks:
            chunks = cls._extract_generic_chunks(rel_path, content, "python")

        return chunks

    # ── Generic line-based splitting ─────────────────────

    @classmethod
    def _extract_generic_chunks(
        cls, rel_path: str, content: str, language: str
    ) -> List[CodeChunkData]:
        chunks: List[CodeChunkData] = []
        lines = content.split("\n")

        for i in range(0, len(lines), cls.CHUNK_SIZE_LINES):
            block = lines[i : i + cls.CHUNK_SIZE_LINES]
            text = "\n".join(block)
            if text.strip():
                chunks.append(
                    CodeChunkData(
                        file_path=rel_path,
                        chunk_text=text,
                        chunk_type="block",
                        line_start=i + 1,
                        line_end=min(i + cls.CHUNK_SIZE_LINES, len(lines)),
                        language=language,
                    )
                )

        return chunks

    # ── Helpers ──────────────────────────────────────────

    @staticmethod
    def _read(file_path: Path) -> Optional[str]:
        try:
            return file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as exc:
            logger.warning("Cannot read %s: %s", file_path, exc)
            return None
