# repak

Bundle files once. Every Docker image that rebuilds gets the latest version automatically.

`repak` packages a local directory as a PyPI wheel and uploads it. Any Dockerfile
can then pull and extract the files with nothing but `curl`, `unzip`, and `tar` —
no Python, no pip, no repak required on the consuming side.

> Only bundle public-domain data. `repak` does not and cannot enforce this —
> it is your responsibility.

## The Docker config bundle use case

Platform teams maintain shared configs — nginx rules, CA certificates, logrotate
configs, entrypoint scripts — that every service needs. Without repak, those files
end up copy-pasted across Dockerfiles and drift the moment anyone edits the source.

With repak:

1. The platform team keeps the files in one directory and runs `repak` when
   anything changes.
2. Every Dockerfile has a single `RUN` line that pulls from PyPI.
3. Any rebuild — by anyone, on any machine — gets the current version
   automatically. No PRs needed across a dozen repos.

```
platform-team/             ← owns this directory
  nginx.conf
  logrotate.conf
  ca-bundle.crt
  entrypoint.sh
```

```bash
cd platform-team && repak   # publish once; teams rebuild to get updates
```

Each consuming Dockerfile chooses between two modes:

```dockerfile
# Always latest — every rebuild pulls whatever is current
RUN set -eu \
 && WHL_URL=$(curl -fsSL https://pypi.org/simple/repak-platform-team/ \
      | grep -o 'https://[^#"]*repak_platform_team[^#"]*\.whl' | tail -1) \
 && curl -fsSL "$WHL_URL" -o /tmp/bundle.whl \
 && cd /tmp && unzip -q bundle.whl repak_platform_team/payload.tar.gz repak_platform_team/payload.sha256 \
 && echo "$(cat repak_platform_team/payload.sha256)  repak_platform_team/payload.tar.gz" | sha256sum -c \
 && mkdir -p /etc/service && tar -xzf repak_platform_team/payload.tar.gz -C /etc/service \
 && rm -rf /tmp/bundle.whl /tmp/repak_platform_team

# Pinned at 0.3 — reproducible builds, sha256 locked at publish time
RUN set -eu \
 && WHL_URL=$(curl -fsSL https://pypi.org/simple/repak-platform-team/ \
      | grep -o 'https://[^#"]*repak_platform_team-0.3-py3-none-any[^#"]*') \
 && curl -fsSL "$WHL_URL" -o /tmp/bundle.whl \
 && cd /tmp && unzip -q bundle.whl repak_platform_team/payload.tar.gz \
 && echo "a3f9...  repak_platform_team/payload.tar.gz" | sha256sum -c \
 && mkdir -p /etc/service && tar -xzf repak_platform_team/payload.tar.gz -C /etc/service \
 && rm -rf /tmp/bundle.whl /tmp/repak_platform_team
```

repak prints both ready-to-paste snippets (with the real sha256 baked in) after
every successful upload.

Both snippets require `curl` and `unzip` in the base image:

```dockerfile
# Alpine
RUN apk add -q curl unzip

# Debian/Ubuntu
RUN apt-get install -y --no-install-recommends curl unzip
```

### Common bundle types

| Bundle | Contents | Extract to |
|---|---|---|
| Service configs | nginx.conf, logrotate rules, sysctl.d snippets | `/etc/service` |
| CA certificates | Corporate root CAs (`.crt` files) | `/usr/local/share/ca-certificates` |
| Entrypoint scripts | Signal handlers, health checks, init helpers | `/usr/local/bin` |
| Developer tooling | `.pylintrc`, `pyproject.toml`, `.pre-commit-config.yaml` | repo root |
| DB fixtures | SQL seed files, migration scripts | `/docker-entrypoint-initdb.d` |

### Pinned vs. latest

| | Pinned | Always latest |
|---|---|---|
| Rebuild behavior | Identical every time | Pulls current upload |
| sha256 | Baked in at publish time | Read from bundle at build time |
| Recommended for | Production images | Active development, shared infra |

## Install

```bash
pip install repak
```

## Usage

```bash
export PYPI_TOKEN="pypi-..."        # or TWINE_PASSWORD

repak --path /path/to/folder
# or, from inside the folder:
repak

# non-interactive (skip confirmation prompts):
repak --path /path/to/folder --yes
```

After a successful upload repak prints the two Dockerfile snippets with the
correct package name and sha256 already filled in. Replace `/your/destination`
with your actual target path.

## How it works

**Upload side**

1. The directory name is normalized to a PyPI name: `repak-{folder}`.
2. PyPI is queried; a new package starts at `0.1`, an existing repak package
   is bumped (`0.1 → … → 0.99`). You confirm before overwriting.
3. The directory **contents** are tarred (`.git`/`.hg`/`.svn`/`.bzr`
   excluded), gzipped, and SHA-256'd.
4. A self-contained wheel is built containing the tar blob, the checksum, and
   an `unpak-{folder}` console-script entry point.
5. The wheel size is checked against PyPI's 100 MiB per-file limit, then
   uploaded with `twine`.

**Download side — with pip**

```bash
pip install repak-myproject
unpak-myproject /target/landing/folder
```

The entry point verifies the SHA-256 **before writing anything**, then
reproduces the directory. `repak` itself does not need to be installed on the
destination.

**Download side — without pip (Docker)**

Use the generated `RUN` snippets above. They use the PyPI simple index to
resolve the wheel URL, then extract and verify using only shell primitives.

## Behavior & constraints

- **Extract** is overwrite/merge in place: existing unrelated files are left
  untouched; re-running with the same payload is idempotent.
- **Safety**: tar entries with absolute paths or `..` traversal are rejected;
  a checksum mismatch aborts before any file is written.
- **Versioning** runs `0.1`–`0.99` (99 uploads per package name). PyPI does
  not allow re-uploading an existing version.
- **Name collisions**: if `repak-{folder}` already exists on PyPI but was not
  created by repak (no repak marker), upload is refused.
- **Mirror lag**: propagation from public PyPI to an internal mirror is
  **not immediate** and the delay is environment-specific.
- **Mirror limits**: a private mirror may impose size limits below PyPI's
  100 MiB.

## Non-goals

No dependency resolution, no "correct" packaging (the wheel is a transport
container), no git integration (clone/prepare the directory yourself), and no
repak install required on the destination side.

## Development

```bash
pip install -e ".[dev]"
pytest -q          # full suite, incl. venv install + roundtrip e2e
```

## License

MIT
