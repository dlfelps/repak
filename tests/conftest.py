from pathlib import Path

import pytest


@pytest.fixture
def sample_tree(tmp_path: Path) -> Path:
    root = tmp_path / "myproject"
    root.mkdir()
    (root / "a.txt").write_text("hello\n")
    (root / "sub").mkdir()
    (root / "sub" / "b.bin").write_bytes(b"\x00\x01\x02binary")
    (root / "sub" / "nested").mkdir()
    (root / "sub" / "nested" / "c.txt").write_text("deep\n")
    # VCS dir that must be excluded.
    git = root / ".git"
    git.mkdir()
    (git / "HEAD").write_text("ref: refs/heads/main\n")
    # Common generated/cache dirs that must also be excluded by default.
    for junk_dir in (".venv", "venv", "__pycache__", "node_modules",
                     ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox"):
        d = root / junk_dir
        d.mkdir()
        (d / "marker").write_text("junk\n")
    # Nested junk dir under a kept subtree must also be pruned.
    (root / "sub" / "__pycache__").mkdir()
    (root / "sub" / "__pycache__" / "b.cpython-312.pyc").write_bytes(b"\x00")
    # Per-file junk (.DS_Store) must be skipped.
    (root / ".DS_Store").write_bytes(b"\x00\x00")
    (root / "sub" / ".DS_Store").write_bytes(b"\x00\x00")
    return root
