"""End-to-end: build a wheel, pip install it into a venv, run unpak."""

import subprocess
import sys
import venv
import zipfile
from pathlib import Path

import pytest

from repak.archive import build_archive
from repak.wheel import build_wheel


def _venv_bin(env_dir: Path) -> Path:
    scripts = "Scripts" if sys.platform == "win32" else "bin"
    return env_dir / scripts


@pytest.mark.slow
def test_install_and_unpak_roundtrip(sample_tree, tmp_path):
    arc = build_archive(sample_tree)
    built = build_wheel("MyProject", "0.1", arc, tmp_path)

    env_dir = tmp_path / "venv"
    venv.create(env_dir, with_pip=True)
    bin_dir = _venv_bin(env_dir)
    py = bin_dir / ("python.exe" if sys.platform == "win32" else "python")

    subprocess.run(
        [str(py), "-m", "pip", "install", "--no-index", str(built.path)],
        check=True,
        capture_output=True,
    )

    target = tmp_path / "landing"
    script = bin_dir / "unpak-myproject"
    result = subprocess.run(
        [str(script), str(target)], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert (target / "a.txt").read_text() == "hello\n"
    assert (target / "sub" / "nested" / "c.txt").read_text() == "deep\n"
    assert not (target / ".git").exists()

    # Idempotent re-run.
    r2 = subprocess.run(
        [str(script), str(target)], capture_output=True, text=True
    )
    assert r2.returncode == 0
    assert (target / "a.txt").read_text() == "hello\n"


@pytest.mark.slow
def test_tampered_payload_fails_checksum(sample_tree, tmp_path):
    arc = build_archive(sample_tree)
    built = build_wheel("MyProject", "0.1", arc, tmp_path)

    # Rewrite the wheel with a corrupted payload but original checksum.
    tampered = tmp_path / built.filename
    with zipfile.ZipFile(built.path) as zin:
        items = {n: zin.read(n) for n in zin.namelist()}
    items["repak_myproject/payload.tar.gz"] += b"corruption"
    with zipfile.ZipFile(tampered, "w") as zout:
        for n, d in items.items():
            zout.writestr(n, d)

    env_dir = tmp_path / "venv"
    venv.create(env_dir, with_pip=True)
    bin_dir = _venv_bin(env_dir)
    py = bin_dir / ("python.exe" if sys.platform == "win32" else "python")
    subprocess.run(
        [str(py), "-m", "pip", "install", "--no-index", str(tampered)],
        check=True,
        capture_output=True,
    )

    target = tmp_path / "landing"
    script = bin_dir / "unpak-myproject"
    result = subprocess.run(
        [str(script), str(target)], capture_output=True, text=True
    )
    assert result.returncode == 1
    assert "checksum verification failed" in result.stderr
    assert not target.exists() or not any(target.iterdir())
