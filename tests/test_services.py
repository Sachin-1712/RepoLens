"""
Tests for the ChunkingService.
"""

import tempfile
from pathlib import Path

from app.services.chunking import ChunkingService


def test_extract_python_chunks():
    """Python files should be chunked by function/class."""
    code = '''
def hello():
    """Say hello."""
    return "hello"

class MyClass:
    """A test class."""
    
    def method(self):
        return 42
'''
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        py_file = root / "example.py"
        py_file.write_text(code)

        chunks = ChunkingService.chunk_file(py_file, root)

    # Should find: hello function, MyClass class, method function
    assert len(chunks) >= 2
    chunk_types = {c.chunk_type for c in chunks}
    assert "function" in chunk_types
    assert "class" in chunk_types


def test_extract_generic_chunks():
    """Non-Python files should be chunked by line blocks."""
    code = "\n".join(f"line {i}" for i in range(100))

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        js_file = root / "script.js"
        js_file.write_text(code)

        chunks = ChunkingService.chunk_file(js_file, root)

    assert len(chunks) >= 2
    assert all(c.chunk_type == "block" for c in chunks)
    assert all(c.language == "javascript" for c in chunks)


def test_empty_file_produces_no_chunks():
    """Empty files should produce zero chunks."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        empty = root / "empty.py"
        empty.write_text("")

        chunks = ChunkingService.chunk_file(empty, root)

    assert chunks == []
