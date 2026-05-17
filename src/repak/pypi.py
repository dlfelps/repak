"""PyPI interaction: version query, repak-marker detection, twine upload."""

from __future__ import annotations

import json
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from .wheel import MARKER

PYPI_JSON_URL = "https://pypi.org/pypi/{name}/json"


@dataclass
class PackageInfo:
    exists: bool
    versions: List[str]
    is_repak: bool  # True only if an existing package carries the repak marker


class UploadError(RuntimeError):
    pass


def query(pypi_name: str, *, timeout: float = 15.0) -> PackageInfo:
    """Look up ``pypi_name`` on public PyPI.

    A 404 means the name is free. If it exists, the repak marker keyword
    distinguishes a package repak itself created from an unrelated public
    package that merely shares the name.
    """
    url = PYPI_JSON_URL.format(name=pypi_name)
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return PackageInfo(exists=False, versions=[], is_repak=False)
        raise

    versions = sorted((payload.get("releases") or {}).keys())
    info = payload.get("info") or {}
    keywords = (info.get("keywords") or "").lower()
    is_repak = MARKER in keywords
    return PackageInfo(exists=True, versions=versions, is_repak=is_repak)


def upload(wheel_path: str | Path, token: str, *, repository_url: Optional[str] = None) -> None:
    """Upload a wheel with ``twine`` using token auth.

    The token is passed via the environment (``TWINE_PASSWORD`` with
    ``TWINE_USERNAME=__token__``) so it never appears in argv or shell
    history.
    """
    env = {
        "TWINE_USERNAME": "__token__",
        "TWINE_PASSWORD": token,
    }
    import os

    full_env = {**os.environ, **env}
    cmd = [sys.executable, "-m", "twine", "upload", str(wheel_path)]
    if repository_url:
        cmd[4:4] = ["--repository-url", repository_url]
    result = subprocess.run(cmd, env=full_env, capture_output=True, text=True)
    if result.returncode != 0:
        raise UploadError(
            "twine upload failed:\n"
            f"{result.stdout}\n{result.stderr}".strip()
        )
