"""Generate dependency-free Docker RUN snippets for consuming a bundle."""

from __future__ import annotations

DEST_PLACEHOLDER = "/your/destination"
DEFAULT_INDEX_URL = "https://pypi.org/simple"


def _index(index_url: str, pypi_name: str) -> str:
    return f"{index_url.rstrip('/')}/{pypi_name}/"


def pip_consumer(
    pypi_name: str,
    console_script: str,
    version: str,
    dest: str = DEST_PLACEHOLDER,
    index_url: str = DEFAULT_INDEX_URL,
) -> str:
    """Return the no-Docker consumer commands: pip install then unpak.

    Needs only pip on the destination; repak itself is not installed there.
    ``unpak-{name}`` verifies the SHA-256 before writing anything.
    """
    extra = ""
    if index_url.rstrip("/") != DEFAULT_INDEX_URL:
        extra = f" --index-url {index_url.rstrip('/')}"
    return (
        f"# latest — re-run pip install -U to pull newer uploads\n"
        f"pip install -U{extra} {pypi_name}\n"
        f"{console_script} {dest}\n"
        f"\n"
        f"# pinned at {version} — reproducible\n"
        f"pip install{extra} {pypi_name}=={version}\n"
        f"{console_script} {dest}"
    )


def pinned_run(
    pypi_name: str,
    pkg: str,
    version: str,
    payload_sha256: str,
    dest: str = DEST_PLACEHOLDER,
    index_url: str = DEFAULT_INDEX_URL,
) -> str:
    """Return a Dockerfile RUN line that installs a specific bundle version.

    Uses only curl, unzip, sha256sum, and tar — no Python or pip required.
    The payload sha256 is baked in at publish time for supply-chain integrity.
    The wheel is matched by its exact filename in the PEP 503 simple index.
    """
    base = _index(index_url, pypi_name)
    return (
        f"# pinned at {version} — sha256 locked at publish time\n"
        f"RUN set -eu \\\n"
        f" && WHL_URL=$(curl -fsSL {base} \\\n"
        f"      | grep -o 'https://[^#\"]*{pkg}-{version}-py3-none-any\\.whl[^#\"]*' \\\n"
        f"      | head -1) \\\n"
        f" && curl -fsSL \"$WHL_URL\" -o /tmp/bundle.whl \\\n"
        f" && cd /tmp && unzip -q bundle.whl {pkg}/payload.tar.gz \\\n"
        f" && echo \"{payload_sha256}  {pkg}/payload.tar.gz\" | sha256sum -c \\\n"
        f" && mkdir -p {dest} \\\n"
        f" && tar -xzf {pkg}/payload.tar.gz -C {dest} \\\n"
        f" && rm -rf /tmp/bundle.whl /tmp/{pkg}"
    )


def latest_run(
    pypi_name: str,
    pkg: str,
    dest: str = DEST_PLACEHOLDER,
    index_url: str = DEFAULT_INDEX_URL,
) -> str:
    """Return a Dockerfile RUN line that always installs the newest bundle.

    Uses only curl, unzip, sha256sum, and tar — no Python or pip required.
    The newest version is selected by a numeric ``major.minor`` sort of the
    versions in the PEP 503 simple index, rather than relying on the order in
    which the index happens to list files.
    """
    base = _index(index_url, pypi_name)
    return (
        f"# always latest — every rebuild pulls the newest upload\n"
        f"RUN set -eu \\\n"
        f" && IDX=$(curl -fsSL {base}) \\\n"
        f" && VER=$(printf '%s' \"$IDX\" \\\n"
        f"      | grep -o '{pkg}-[0-9][0-9]*\\.[0-9][0-9]*-py3-none-any\\.whl' \\\n"
        f"      | sed 's/^{pkg}-//;s/-py3-none-any\\.whl$//' \\\n"
        f"      | sort -t. -k1,1n -k2,2n | tail -1) \\\n"
        f" && WHL_URL=$(printf '%s' \"$IDX\" \\\n"
        f"      | grep -o 'https://[^#\"]*{pkg}-'\"$VER\"'-py3-none-any\\.whl[^#\"]*' \\\n"
        f"      | head -1) \\\n"
        f" && curl -fsSL \"$WHL_URL\" -o /tmp/bundle.whl \\\n"
        f" && cd /tmp && unzip -q bundle.whl {pkg}/payload.tar.gz {pkg}/payload.sha256 \\\n"
        f" && echo \"$(cat {pkg}/payload.sha256)  {pkg}/payload.tar.gz\" | sha256sum -c \\\n"
        f" && mkdir -p {dest} \\\n"
        f" && tar -xzf {pkg}/payload.tar.gz -C {dest} \\\n"
        f" && rm -rf /tmp/bundle.whl /tmp/{pkg}"
    )
