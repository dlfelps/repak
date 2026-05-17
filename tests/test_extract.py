import io
import tarfile

import pytest

from repak import unpak_template as ut


def _make_tar(entries):
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w:gz") as tar:
        for name, data in entries:
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return raw.getvalue()


def test_extract_creates_target_and_files(tmp_path):
    data = _make_tar([("a.txt", b"A"), ("d/b.txt", b"B")])
    dest = tmp_path / "out"
    ut._extract(data, dest)
    assert (dest / "a.txt").read_bytes() == b"A"
    assert (dest / "d" / "b.txt").read_bytes() == b"B"


def test_overwrite_merge_idempotent(tmp_path):
    dest = tmp_path / "out"
    dest.mkdir()
    (dest / "unrelated.txt").write_text("keep me")

    data = _make_tar([("a.txt", b"v1")])
    ut._extract(data, dest)
    ut._extract(data, dest)  # idempotent
    assert (dest / "a.txt").read_bytes() == b"v1"
    assert (dest / "unrelated.txt").read_text() == "keep me"

    data2 = _make_tar([("a.txt", b"v2")])
    ut._extract(data2, dest)  # overwrite in place
    assert (dest / "a.txt").read_bytes() == b"v2"
    assert (dest / "unrelated.txt").read_text() == "keep me"


def test_rejects_path_traversal(tmp_path):
    data = _make_tar([("../evil.txt", b"x")])
    with pytest.raises(ValueError):
        ut._extract(data, tmp_path / "out")


def test_rejects_absolute_path(tmp_path):
    data = _make_tar([("/etc/evil", b"x")])
    with pytest.raises(ValueError):
        ut._extract(data, tmp_path / "out")
