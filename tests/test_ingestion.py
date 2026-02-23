"""
Tests for IngestionService.
"""

import tempfile
import os
from pathlib import Path
from app.services.ingestion import IngestionService

def test_discover_code_files():
    """Test discovering supported files while ignoring build directories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        
        # Supported file
        (root / "main.py").touch()
        (root / "README.md").touch()
        (root / "README").touch() # No extension, starts with README
        
        # Unsupported file
        (root / "image.png").touch()
        
        # Ignored dir
        ignored_dir = root / "node_modules"
        ignored_dir.mkdir()
        (ignored_dir / "index.js").touch()
        
        # Nested supported file
        nested = root / "src"
        nested.mkdir()
        (nested / "app.ts").touch()
        
        discovered = IngestionService.discover_code_files(str(root))
        
        names = {p.name for p in discovered}
        assert "main.py" in names
        assert "README.md" in names
        assert "README" in names
        assert "app.ts" in names
        
        assert "image.png" not in names
        assert "index.js" not in names
