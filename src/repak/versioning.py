"""Version scheme: 0.N where N is an integer 1..99.

Sequence: 0.1, 0.2, ... 0.9, 0.10, 0.11, ... 0.99 (99 uploads per package).
"""

from __future__ import annotations

import re
from typing import Iterable, Optional

_VERSION_RE = re.compile(r"^0\.(\d+)$")

MIN_MINOR = 1
MAX_MINOR = 99


class VersionExhausted(RuntimeError):
    """Raised when the 0.99 ceiling has been reached for a package."""


def next_version(existing: Optional[Iterable[str]]) -> str:
    """Return the next ``0.N`` version string.

    ``None`` or an empty iterable means the package does not exist yet, so
    versioning starts at ``0.1``. Otherwise the next version is one greater
    than the highest ``0.N`` already published; non-conforming version
    strings are ignored.
    """
    if not existing:
        return f"0.{MIN_MINOR}"

    minors = [
        int(m.group(1))
        for m in (_VERSION_RE.match(v.strip()) for v in existing)
        if m is not None
    ]
    if not minors:
        return f"0.{MIN_MINOR}"

    current = max(minors)
    nxt = current + 1
    if nxt > MAX_MINOR:
        raise VersionExhausted(
            f"package has reached the maximum version 0.{MAX_MINOR}; "
            "no further uploads are possible under this package name"
        )
    return f"0.{nxt}"
