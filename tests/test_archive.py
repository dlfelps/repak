import hashlib
import io
import tarfile

from repak.archive import build_archive


def _names(data: bytes):
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        return sorted(tar.getnames())


def test_excludes_vcs_and_keeps_contents(sample_tree):
    arc = build_archive(sample_tree)
    names = _names(arc.data)
    assert "a.txt" in names
    assert "sub/b.bin" in names
    assert "sub/nested/c.txt" in names
    assert not any(n.startswith(".git") for n in names)


def test_checksum_matches_data(sample_tree):
    arc = build_archive(sample_tree)
    assert arc.sha256 == hashlib.sha256(arc.data).hexdigest()
    assert arc.size == len(arc.data)


def test_deterministic(sample_tree):
    a = build_archive(sample_tree)
    b = build_archive(sample_tree)
    assert a.sha256 == b.sha256
    assert a.data == b.data
