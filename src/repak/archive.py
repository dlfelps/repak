"""Build a deterministic ``tar.gz`` of a directory's contents + checksum."""

from __future__ import annotations

import gzip
import hashlib
import io
import os
import tarfile
from dataclasses import dataclass
from pathlib import Path
from typing import List

VCS_DIRS = {".git", ".hg", ".svn", ".bzr"}

# Generated/transient directories that are virtually never intended to be
# shipped: virtualenvs, language package caches, and tool caches. Pruned by
# default so a stray `.venv` doesn't add tens of MB (and a self-extracting
# `python.exe` that can't overwrite itself on Windows) to every bundle.
JUNK_DIRS = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    "node_modules",
    ".venv",
    "venv",
}

# Per-file junk that shows up regardless of directory layout.
JUNK_FILES = {".DS_Store"}

_PRUNED_DIRS = VCS_DIRS | JUNK_DIRS

# Fixed timestamp so identical trees produce identical archives (helps make
# uploads/tests reproducible). 2020-01-01 UTC.
_FIXED_MTIME = 1577836800


@dataclass
class Archive:
    data: bytes
    sha256: str
    size: int  # compressed size in bytes


def _iter_files(root: Path) -> List[Path]:
    collected: List[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Prune VCS + junk directories in-place so os.walk does not descend.
        dirnames[:] = sorted(d for d in dirnames if d not in _PRUNED_DIRS)
        for name in sorted(filenames):
            if name in JUNK_FILES:
                continue
            collected.append(Path(dirpath) / name)
    return collected


def build_archive(source_dir: str | os.PathLike) -> Archive:
    """Tar (gzip) the *contents* of ``source_dir`` at the archive root.

    VCS directories are excluded. The archive and its SHA-256 are
    deterministic for a given set of file contents and relative paths.
    """
    root = Path(source_dir).resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"{root} is not a directory")

    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w") as tar:
        for path in _iter_files(root):
            rel = path.relative_to(root).as_posix()
            info = tar.gettarinfo(str(path), arcname=rel)
            info.mtime = _FIXED_MTIME
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            if info.isreg():
                with open(path, "rb") as fh:
                    tar.addfile(info, fh)
            else:
                tar.addfile(info)

    compressed = gzip.compress(raw.getvalue(), compresslevel=9, mtime=0)
    digest = hashlib.sha256(compressed).hexdigest()
    return Archive(data=compressed, sha256=digest, size=len(compressed))
