"""Self-contained extractor embedded into every repak-generated wheel.

This module ships *inside* the synthetic wheel as ``<pkg>/_unpak.py`` and is
wired to the ``unpak-{name}`` console script. It must depend only on the
Python standard library: repak is not installed on the destination side.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import os
import sys
import tarfile
from importlib import resources
from pathlib import Path

PAYLOAD = "payload.tar.gz"
CHECKSUM = "payload.sha256"


def _read_resource(name: str) -> bytes:
    return resources.files(__package__).joinpath(name).read_bytes()


def _safe_members(tar: tarfile.TarFile, dest: Path):
    """Yield only members that extract safely under ``dest``.

    Rejects absolute paths and ``..`` traversal; restricts to regular files
    and directories (mirrors the intent of tarfile's ``data`` filter while
    remaining compatible with Python 3.9).
    """
    dest = dest.resolve()
    for member in tar.getmembers():
        name = member.name
        if name.startswith("/") or os.path.isabs(name):
            raise ValueError(f"unsafe absolute path in archive: {name!r}")
        target = (dest / name).resolve()
        if target != dest and dest not in target.parents:
            raise ValueError(f"unsafe path traversal in archive: {name!r}")
        if member.isdir() or member.isreg():
            yield member
        else:
            raise ValueError(
                f"archive contains unsupported entry {name!r} "
                f"(type {member.type!r})"
            )


def _extract(data: bytes, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        members = list(_safe_members(tar, dest))
        for member in members:
            out = dest / member.name
            if member.isdir():
                out.mkdir(parents=True, exist_ok=True)
                continue
            out.parent.mkdir(parents=True, exist_ok=True)
            src = tar.extractfile(member)
            if src is None:
                continue
            with open(out, "wb") as fh:
                fh.write(src.read())
            os.chmod(out, member.mode & 0o777)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog=f"unpak ({__package__})",
        description="Verify and extract a repak-transported directory.",
    )
    parser.add_argument(
        "target",
        help="Destination folder; created if missing. Existing unrelated "
        "files are left untouched (overwrite/merge).",
    )
    args = parser.parse_args(argv)

    data = _read_resource(PAYLOAD)
    expected = _read_resource(CHECKSUM).decode("ascii").strip()
    actual = hashlib.sha256(data).hexdigest()
    if actual != expected:
        sys.stderr.write(
            "ERROR: checksum verification failed; the payload is corrupt "
            "and nothing was written.\n"
            f"  expected: {expected}\n"
            f"  actual:   {actual}\n"
        )
        return 1

    dest = Path(args.target)
    _extract(data, dest)
    sys.stdout.write(
        f"Verified SHA-256 and extracted contents to {dest.resolve()}\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
