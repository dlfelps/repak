"""Folder name -> PyPI package name / Python module name normalization."""

from __future__ import annotations

import re

REPAK_PREFIX = "repak"


class NameError_(ValueError):
    """Raised when a folder name cannot be normalized to a valid name."""


def normalize(folder_name: str) -> str:
    """Normalize a folder basename to a PEP 503-style component.

    Lowercase, runs of non-alphanumeric characters collapse to a single
    hyphen, leading/trailing hyphens stripped.
    """
    lowered = folder_name.strip().lower()
    collapsed = re.sub(r"[^a-z0-9]+", "-", lowered)
    stripped = collapsed.strip("-")
    if not stripped:
        raise NameError_(
            f"folder name {folder_name!r} does not contain any characters "
            "usable in a PyPI package name"
        )
    return stripped


def pypi_name(folder_name: str) -> str:
    """Return the public PyPI distribution name: ``repak-{normalized}``."""
    return f"{REPAK_PREFIX}-{normalize(folder_name)}"


def module_name(folder_name: str) -> str:
    """Return the import package name: ``repak_{normalized_with_underscores}``."""
    return f"{REPAK_PREFIX}_{normalize(folder_name).replace('-', '_')}"


def console_script(folder_name: str) -> str:
    """Return the destination-side console command: ``unpak-{normalized}``."""
    return f"unpak-{normalize(folder_name)}"
