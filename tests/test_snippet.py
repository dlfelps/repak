"""Tests for Docker RUN snippet generation."""

from repak import snippet


PYPI_NAME = "repak-my-configs"
PKG = "repak_my_configs"
VERSION = "0.3"
SHA256 = "a" * 64


def test_pinned_run_contains_version():
    out = snippet.pinned_run(PYPI_NAME, PKG, VERSION, SHA256)
    assert VERSION in out


def test_pinned_run_contains_sha256():
    out = snippet.pinned_run(PYPI_NAME, PKG, VERSION, SHA256)
    assert SHA256 in out


def test_pinned_run_contains_pypi_name():
    out = snippet.pinned_run(PYPI_NAME, PKG, VERSION, SHA256)
    assert PYPI_NAME in out


def test_pinned_run_contains_pkg():
    out = snippet.pinned_run(PYPI_NAME, PKG, VERSION, SHA256)
    assert PKG in out


def test_pinned_run_starts_with_run():
    out = snippet.pinned_run(PYPI_NAME, PKG, VERSION, SHA256)
    assert "RUN " in out


def test_pinned_run_custom_dest():
    out = snippet.pinned_run(PYPI_NAME, PKG, VERSION, SHA256, dest="/etc/app")
    assert "/etc/app" in out
    assert snippet.DEST_PLACEHOLDER not in out


def test_pinned_run_default_dest_is_placeholder():
    out = snippet.pinned_run(PYPI_NAME, PKG, VERSION, SHA256)
    assert snippet.DEST_PLACEHOLDER in out


def test_pinned_run_no_pip():
    out = snippet.pinned_run(PYPI_NAME, PKG, VERSION, SHA256)
    assert "pip" not in out


def test_pinned_run_sha256sum_check():
    out = snippet.pinned_run(PYPI_NAME, PKG, VERSION, SHA256)
    assert "sha256sum" in out


def test_latest_run_contains_pypi_name():
    out = snippet.latest_run(PYPI_NAME, PKG)
    assert PYPI_NAME in out


def test_latest_run_contains_pkg():
    out = snippet.latest_run(PYPI_NAME, PKG)
    assert PKG in out


def test_latest_run_starts_with_run():
    out = snippet.latest_run(PYPI_NAME, PKG)
    assert "RUN " in out


def test_latest_run_custom_dest():
    out = snippet.latest_run(PYPI_NAME, PKG, dest="/etc/app")
    assert "/etc/app" in out
    assert snippet.DEST_PLACEHOLDER not in out


def test_latest_run_default_dest_is_placeholder():
    out = snippet.latest_run(PYPI_NAME, PKG)
    assert snippet.DEST_PLACEHOLDER in out


def test_latest_run_no_pip():
    out = snippet.latest_run(PYPI_NAME, PKG)
    assert "pip" not in out


def test_latest_run_sha256sum_check():
    out = snippet.latest_run(PYPI_NAME, PKG)
    assert "sha256sum" in out


def test_latest_run_no_baked_sha256():
    # Latest snippet must NOT bake in a sha256 — it reads it dynamically
    out = snippet.latest_run(PYPI_NAME, PKG)
    assert SHA256 not in out


def test_pinned_does_not_fetch_payload_sha256_file():
    # Pinned snippet verifies against the baked sha256, not the file
    out = snippet.pinned_run(PYPI_NAME, PKG, VERSION, SHA256)
    assert "payload.sha256" not in out


def test_latest_fetches_payload_sha256_file():
    # Latest snippet must read payload.sha256 from inside the wheel
    out = snippet.latest_run(PYPI_NAME, PKG)
    assert "payload.sha256" in out
