"""Hand-built synthetic wheel: a transport container, not a real package."""

from __future__ import annotations

import base64
import hashlib
import zipfile
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Dict

from . import naming
from .archive import Archive
from .unpak_template import CHECKSUM, PAYLOAD

MARKER = "repak-transport-container"

# PyPI's default per-file upload limit.
MAX_WHEEL_BYTES = 100 * 1024 * 1024


class WheelTooLarge(RuntimeError):
    def __init__(self, size: int):
        self.size = size
        super().__init__(
            f"generated wheel is {size / (1024 * 1024):.2f} MiB, which "
            f"exceeds PyPI's {MAX_WHEEL_BYTES // (1024 * 1024)} MiB per-file "
            "limit. Reduce the directory size and try again."
        )


@dataclass
class BuiltWheel:
    path: Path
    size: int
    filename: str


def _record_hash(data: bytes) -> str:
    digest = hashlib.sha256(data).digest()
    b64 = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return f"sha256={b64}"


def _unpak_source() -> str:
    return resources.files("repak").joinpath("unpak_template.py").read_text(
        encoding="utf-8"
    )


def build_wheel(
    folder_name: str,
    version: str,
    archive: Archive,
    out_dir: str | Path,
) -> BuiltWheel:
    """Write ``repak_{name}-{version}-py3-none-any.whl`` into ``out_dir``."""
    pkg = naming.module_name(folder_name)
    dist_name = naming.pypi_name(folder_name)
    script = naming.console_script(folder_name)
    dist_info = f"{pkg}-{version}.dist-info"

    metadata = (
        "Metadata-Version: 2.1\n"
        f"Name: {dist_name}\n"
        f"Version: {version}\n"
        "Summary: Directory payload transported by repak.\n"
        f"Keywords: {MARKER}\n"
    )
    wheel_meta = (
        "Wheel-Version: 1.0\n"
        "Generator: repak\n"
        "Root-Is-Purelib: true\n"
        "Tag: py3-none-any\n"
    )
    entry_points = f"[console_scripts]\n{script} = {pkg}._unpak:main\n"

    files: Dict[str, bytes] = {
        f"{pkg}/__init__.py": b"",
        f"{pkg}/_unpak.py": _unpak_source().encode("utf-8"),
        f"{pkg}/{PAYLOAD}": archive.data,
        f"{pkg}/{CHECKSUM}": archive.sha256.encode("ascii") + b"\n",
        f"{dist_info}/METADATA": metadata.encode("utf-8"),
        f"{dist_info}/WHEEL": wheel_meta.encode("utf-8"),
        f"{dist_info}/entry_points.txt": entry_points.encode("utf-8"),
    }

    record_lines = [
        f"{name},{_record_hash(data)},{len(data)}"
        for name, data in files.items()
    ]
    record_path = f"{dist_info}/RECORD"
    record_lines.append(f"{record_path},,")
    files[record_path] = ("\n".join(record_lines) + "\n").encode("utf-8")

    filename = f"{pkg}-{version}-py3-none-any.whl"
    out_path = Path(out_dir) / filename
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in files.items():
            zf.writestr(name, data)

    size = out_path.stat().st_size
    if size > MAX_WHEEL_BYTES:
        out_path.unlink(missing_ok=True)
        raise WheelTooLarge(size)

    return BuiltWheel(path=out_path, size=size, filename=filename)
