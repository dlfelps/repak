"""Generate dependency-free Docker RUN snippets for consuming a bundle."""

from __future__ import annotations

DEST_PLACEHOLDER = "/your/destination"


def pinned_run(
    pypi_name: str,
    pkg: str,
    version: str,
    payload_sha256: str,
    dest: str = DEST_PLACEHOLDER,
) -> str:
    """Return a Dockerfile RUN line that installs a specific bundle version.

    Uses only curl, unzip, sha256sum, and tar — no Python or pip required.
    The payload sha256 is baked in at publish time for supply-chain integrity.
    """
    return (
        f"# pinned at {version} — sha256 locked at publish time\n"
        f"RUN set -eu \\\n"
        f" && WHL_URL=$(curl -fsSL https://pypi.org/simple/{pypi_name}/ \\\n"
        f"      | grep -o 'https://[^#\"]*{pkg}-{version}-py3-none-any[^#\"]*') \\\n"
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
) -> str:
    """Return a Dockerfile RUN line that always installs the newest bundle.

    Uses only curl, unzip, sha256sum, and tar — no Python or pip required.
    Every Docker rebuild will pull whatever version is current on PyPI.
    """
    return (
        f"# always latest — every rebuild pulls the newest upload\n"
        f"RUN set -eu \\\n"
        f" && WHL_URL=$(curl -fsSL https://pypi.org/simple/{pypi_name}/ \\\n"
        f"      | grep -o 'https://[^#\"]*{pkg}[^#\"]*\\.whl' | tail -1) \\\n"
        f" && curl -fsSL \"$WHL_URL\" -o /tmp/bundle.whl \\\n"
        f" && cd /tmp && unzip -q bundle.whl {pkg}/payload.tar.gz {pkg}/payload.sha256 \\\n"
        f" && echo \"$(cat {pkg}/payload.sha256)  {pkg}/payload.tar.gz\" | sha256sum -c \\\n"
        f" && mkdir -p {dest} \\\n"
        f" && tar -xzf {pkg}/payload.tar.gz -C {dest} \\\n"
        f" && rm -rf /tmp/bundle.whl /tmp/{pkg}"
    )
