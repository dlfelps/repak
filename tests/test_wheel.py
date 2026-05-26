import base64
import hashlib
import zipfile

import pytest

from repak import __version__, wheel
from repak.archive import build_archive


def _build(sample_tree, tmp_path, version="0.1"):
    arc = build_archive(sample_tree)
    return wheel.build_wheel("MyProject", version, arc, tmp_path), arc


def test_wheel_structure(sample_tree, tmp_path):
    built, arc = _build(sample_tree, tmp_path)
    assert built.filename == "repak_myproject-0.1-py3-none-any.whl"

    with zipfile.ZipFile(built.path) as zf:
        names = set(zf.namelist())
        assert "repak_myproject/_unpak.py" in names
        assert "repak_myproject/payload.tar.gz" in names
        assert "repak_myproject/payload.sha256" in names

        ep = zf.read(
            "repak_myproject-0.1.dist-info/entry_points.txt"
        ).decode()
        assert ep == "[console_scripts]\nunpak-myproject = repak_myproject._unpak:main\n"

        meta = zf.read("repak_myproject-0.1.dist-info/METADATA").decode()
        assert "Name: repak-myproject" in meta
        assert f"Keywords: {wheel.MARKER}" in meta

        wheel_meta = zf.read(
            "repak_myproject-0.1.dist-info/WHEEL"
        ).decode()
        assert f"Generator: repak ({__version__})" in wheel_meta

        payload = zf.read("repak_myproject/payload.tar.gz")
        assert payload == arc.data
        checksum = zf.read("repak_myproject/payload.sha256").decode().strip()
        assert checksum == arc.sha256


def test_record_hashes_valid(sample_tree, tmp_path):
    built, _ = _build(sample_tree, tmp_path)
    with zipfile.ZipFile(built.path) as zf:
        record = zf.read(
            "repak_myproject-0.1.dist-info/RECORD"
        ).decode().splitlines()
        entries = {}
        for line in record:
            path, h, size = line.rsplit(",", 2)
            entries[path] = (h, size)

        for path, (h, size) in entries.items():
            if path.endswith("RECORD"):
                assert h == "" and size == ""
                continue
            data = zf.read(path)
            expected = base64.urlsafe_b64encode(
                hashlib.sha256(data).digest()
            ).rstrip(b"=").decode()
            assert h == f"sha256={expected}"
            assert size == str(len(data))


def test_size_limit(monkeypatch, sample_tree, tmp_path):
    monkeypatch.setattr(wheel, "MAX_WHEEL_BYTES", 10)
    arc = build_archive(sample_tree)
    with pytest.raises(wheel.WheelTooLarge):
        wheel.build_wheel("MyProject", "0.1", arc, tmp_path)
