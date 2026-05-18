"""Version scheme: ``MAJOR.MINOR`` where MINOR is 0..99 and MAJOR is unbounded.

Sequence: 0.1, 0.2, ... 0.9, 0.10, ... 0.99, 1.0, 1.1, ... 1.99, 2.0, ...

Internally a version maps to an integer ``n = MAJOR * 100 + MINOR``. The first
upload is ``0.1`` (``n = 1``); each subsequent upload increments ``n`` by one
and rolls the minor into the major at 100. There is no upper bound.
"""

from __future__ import annotations

import re
from typing import Iterable, Optional

_VERSION_RE = re.compile(r"^(\d+)\.(\d+)$")

MIN_N = 1
_MINOR_BASE = 100


def _to_n(major: int, minor: int) -> int:
    return major * _MINOR_BASE + minor


def _to_version(n: int) -> str:
    return f"{n // _MINOR_BASE}.{n % _MINOR_BASE}"


def next_version(existing: Optional[Iterable[str]]) -> str:
    """Return the next ``MAJOR.MINOR`` version string.

    ``None`` or an empty iterable means the package does not exist yet, so
    versioning starts at ``0.1``. Otherwise the next version is one step past
    the highest already published; minor wraps into major at 100 (``0.99`` is
    followed by ``1.0``). Version strings with a minor of 100 or more, or that
    do not match ``MAJOR.MINOR``, are ignored.
    """
    if not existing:
        return _to_version(MIN_N)

    ns = []
    for v in existing:
        m = _VERSION_RE.match(v.strip())
        if m is None:
            continue
        major, minor = int(m.group(1)), int(m.group(2))
        if minor >= _MINOR_BASE:
            continue
        ns.append(_to_n(major, minor))

    if not ns:
        return _to_version(MIN_N)

    return _to_version(max(ns) + 1)
