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
    return root
