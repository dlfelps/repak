"""repak command-line entry point (upload side)."""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

from . import naming, pypi, snippet, versioning
from .archive import build_archive
from .wheel import WheelTooLarge, build_wheel

TOKEN_ENV_VARS = ("PYPI_TOKEN", "TWINE_PASSWORD")


def _get_token() -> str:
    for var in TOKEN_ENV_VARS:
        val = os.environ.get(var)
        if val:
            return val
    raise SystemExit(
        "ERROR: no PyPI token found. Set the PYPI_TOKEN environment variable "
        "to a PyPI API token (passed via the environment, never as a flag, "
        "so it stays out of shell history and process listings)."
    )


def _confirm(prompt: str, assume_yes: bool) -> bool:
    if assume_yes:
        return True
    try:
        answer = input(f"{prompt} [y/N] ").strip().lower()
    except EOFError:
        return False
    return answer in ("y", "yes")


def _parse_args(argv):
    parser = argparse.ArgumentParser(
        prog="repak",
        description="Package a local directory as a synthetic PyPI wheel and "
        "upload it to public PyPI for transport into an isolated mirror.",
    )
    parser.add_argument(
        "--path",
        default=".",
        help="Directory to package (default: current directory).",
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip confirmation prompts (for non-interactive use).",
    )
    parser.add_argument(
        "--repository-url",
        default=None,
        help="Upload target for twine (default: public PyPI). Set this to a "
        "private index URL to keep bundles off public PyPI.",
    )
    parser.add_argument(
        "--index-url",
        default=snippet.DEFAULT_INDEX_URL,
        help="Simple-index base URL baked into the generated Docker snippets "
        f"(default: {snippet.DEFAULT_INDEX_URL}). Point this at your private "
        "mirror's simple index when using --repository-url.",
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = _parse_args(argv)

    source = Path(args.path).resolve()
    if not source.is_dir():
        sys.stderr.write(f"ERROR: {source} is not a directory.\n")
        return 1

    try:
        pypi_name = naming.pypi_name(source.name)
    except naming.NameError_ as exc:
        sys.stderr.write(f"ERROR: {exc}\n")
        return 1

    token = _get_token()

    info = pypi.query(pypi_name)
    if info.exists and not info.is_repak:
        sys.stderr.write(
            f"ERROR: '{pypi_name}' already exists on PyPI but was not created "
            "by repak (no repak marker). Refusing to collide with an "
            "unrelated package. Rename the source folder and retry.\n"
        )
        return 1

    version = versioning.next_version(info.versions if info.exists else None)

    if not info.exists:
        print(f"Creating new package {pypi_name} at version {version}")
    else:
        latest = info.versions[-1] if info.versions else "?"
        print(
            f"Warning: {pypi_name} already exists at version {latest}\n"
            f"This upload will create version {version}."
        )
        if not _confirm("Proceed?", args.yes):
            print("Aborted.")
            return 1

    archive = build_archive(source)
    print(
        f"Archived contents of {source} "
        f"({archive.size / (1024 * 1024):.2f} MiB compressed, "
        f"sha256 {archive.sha256[:16]}...)"
    )

    with tempfile.TemporaryDirectory() as tmp:
        try:
            wheel = build_wheel(source.name, version, archive, tmp)
        except WheelTooLarge as exc:
            sys.stderr.write(f"ERROR: {exc}\n")
            return 1

        print(
            f"Built wheel {wheel.filename} "
            f"({wheel.size / (1024 * 1024):.2f} MiB)"
        )
        target = args.repository_url or "public PyPI"
        if not _confirm(f"Upload {wheel.filename} to {target}?", args.yes):
            print("Aborted.")
            return 1

        try:
            pypi.upload(wheel.path, token, repository_url=args.repository_url)
        except pypi.UploadError as exc:
            sys.stderr.write(f"ERROR: {exc}\n")
            return 1

    pkg = naming.module_name(source.name)
    script = naming.console_script(source.name)
    pip = snippet.pip_consumer(
        pypi_name, script, version, index_url=args.index_url
    )
    pinned = snippet.pinned_run(
        pypi_name, pkg, version, archive.sha256, index_url=args.index_url
    )
    latest = snippet.latest_run(pypi_name, pkg, index_url=args.index_url)

    print(
        f"\nUploaded {pypi_name} {version} to {target}.\n"
        "\nConsume it one of two ways "
        "(replace /your/destination with your target path):\n"
        "\n=== With pip (no Docker, no clone) ===\n"
        f"{pip}\n"
        "\n=== Without pip (Docker base image with no Python) ===\n"
        "\n  --- Pinned (recommended for production) ---\n"
        f"{pinned}\n"
        "\n  --- Always latest (every rebuild pulls newest) ---\n"
        f"{latest}\n"
        "\nThe Docker snippets require curl and unzip in your base image.\n"
        "  Alpine: RUN apk add -q curl unzip\n"
        "  Debian: RUN apt-get install -y --no-install-recommends curl unzip"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
