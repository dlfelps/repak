import io
import json
import urllib.error

import pytest

from repak import pypi
from repak.wheel import MARKER


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


def _fake_urlopen(payload):
    def _open(url, timeout=0):
        return _Resp(json.dumps(payload).encode())

    return _open


def test_query_not_found(monkeypatch):
    def _raise(url, timeout=0):
        raise urllib.error.HTTPError(url, 404, "nf", {}, None)

    monkeypatch.setattr(pypi.urllib.request, "urlopen", _raise)
    info = pypi.query("repak-missing")
    assert info.exists is False and info.is_repak is False


def test_query_existing_repak(monkeypatch):
    payload = {
        "releases": {"0.1": [], "0.2": []},
        "info": {"keywords": f"foo, {MARKER}"},
    }
    monkeypatch.setattr(
        pypi.urllib.request, "urlopen", _fake_urlopen(payload)
    )
    info = pypi.query("repak-thing")
    assert info.exists and info.is_repak
    assert info.versions == ["0.1", "0.2"]


def test_query_existing_unrelated(monkeypatch):
    payload = {"releases": {"1.0": []}, "info": {"keywords": "other"}}
    monkeypatch.setattr(
        pypi.urllib.request, "urlopen", _fake_urlopen(payload)
    )
    info = pypi.query("repak-thing")
    assert info.exists and not info.is_repak


def test_upload_passes_token_via_env(monkeypatch, tmp_path):
    wheel = tmp_path / "x.whl"
    wheel.write_bytes(b"data")
    captured = {}

    class _Result:
        returncode = 0
        stdout = ""
        stderr = ""

    def _run(cmd, env=None, capture_output=False, text=False):
        captured["cmd"] = cmd
        captured["env"] = env
        return _Result()

    monkeypatch.setattr(pypi.subprocess, "run", _run)
    pypi.upload(wheel, "pypi-secret-token")

    assert "twine" in captured["cmd"]
    assert str(wheel) in captured["cmd"]
    assert "pypi-secret-token" not in captured["cmd"]
    assert captured["env"]["TWINE_USERNAME"] == "__token__"
    assert captured["env"]["TWINE_PASSWORD"] == "pypi-secret-token"


def test_upload_error(monkeypatch, tmp_path):
    wheel = tmp_path / "x.whl"
    wheel.write_bytes(b"data")

    class _Result:
        returncode = 1
        stdout = "boom"
        stderr = "fail"

    monkeypatch.setattr(
        pypi.subprocess, "run", lambda *a, **k: _Result()
    )
    with pytest.raises(pypi.UploadError):
        pypi.upload(wheel, "tok")
