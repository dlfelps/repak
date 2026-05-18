# repak

Bundle public files once. Every Docker image that rebuilds gets the latest version automatically.

`repak` packages a local directory as a PyPI wheel and uploads it. Any Dockerfile
can then pull and extract the files with nothing but `curl`, `unzip`, and `tar` —
no Python, no pip, no repak required on the consuming side.

> **Public data only.** Uploading to public PyPI publishes your files to the
> world. Only bundle data you would publish anyway — open-source project
> assets, public test fixtures, public datasets, demo/tutorial configs.
> `repak` does not and cannot enforce this; it is your responsibility. For
> private data, use a private index (see [Private indexes](#private-indexes))
> — or, more likely, a container registry (see below).

> Not related to [`trumank/repak`](https://github.com/trumank/repak), the Rust
> CLI for Unreal Engine `.pak` files. Different tool, same name.

## Is repak the right tool?

repak rides on public PyPI as a free, CDN-backed file host. That only makes
sense for a narrow case. **If you already run a container registry** (most
teams do), the better answer for shared build-context files is a one-line,
authenticated, layer-cached copy:

```dockerfile
COPY --from=registry.example.com/platform-base:1.4 /etc/service /etc/service
```

That works with private data, uses the auth and RBAC you already have, and has
no HTML-scraping or third-party-host failure mode. Git submodules, ORAS OCI
artifacts, or a plain tarball on S3/Artifactory are also fine. Reach for repak
only when **all** of the following hold:

- The bundle is **genuinely public** (you would publish it anyway).
- You have **no container registry** and no appetite to run one.
- You want consumers to need **zero specialized tooling** — just `curl`,
  `unzip`, `tar`.

Using PyPI as a generic file host is guest use of infrastructure funded by the
Python Software Foundation and its sponsors. Keep bundles small, don't churn
them needlessly, and move heavy or internal use to a private index.

## The shared-bundle use case

A project maintains public files that many Docker images need — example
configs, seed fixtures, demo datasets. Without repak, those files end up
copy-pasted across Dockerfiles and drift the moment anyone edits the source.

With repak:

1. The owning team keeps the files in one directory and runs `repak` when
   anything changes.
2. Every Dockerfile has a single `RUN` line that pulls from the index.
3. Any rebuild — by anyone, on any machine — gets the current version
   automatically. No PRs needed across a dozen repos.

```
example-assets/            <- owns this directory
  demo-nginx.conf
  logrotate.conf
  seed.sql
  entrypoint.sh
```

```bash
cd example-assets && repak   # publish once; teams rebuild to get updates
```

Each consuming Dockerfile chooses between two modes:

```dockerfile
# always latest — every rebuild pulls the newest upload
RUN set -eu \
 && IDX=$(curl -fsSL https://pypi.org/simple/repak-example-assets/) \
 && VER=$(printf '%s' "$IDX" \
      | grep -o 'repak_example_assets-[0-9][0-9]*\.[0-9][0-9]*-py3-none-any\.whl' \
      | sed 's/^repak_example_assets-//;s/-py3-none-any\.whl$//' \
      | sort -t. -k1,1n -k2,2n | tail -1) \
 && WHL_URL=$(printf '%s' "$IDX" \
      | grep -o 'https://[^#"]*repak_example_assets-'"$VER"'-py3-none-any\.whl[^#"]*' \
      | head -1) \
 && curl -fsSL "$WHL_URL" -o /tmp/bundle.whl \
 && cd /tmp && unzip -q bundle.whl repak_example_assets/payload.tar.gz repak_example_assets/payload.sha256 \
 && echo "$(cat repak_example_assets/payload.sha256)  repak_example_assets/payload.tar.gz" | sha256sum -c \
 && mkdir -p /etc/service \
 && tar -xzf repak_example_assets/payload.tar.gz -C /etc/service \
 && rm -rf /tmp/bundle.whl /tmp/repak_example_assets

# pinned at 0.3 — reproducible builds, sha256 locked at publish time
RUN set -eu \
 && WHL_URL=$(curl -fsSL https://pypi.org/simple/repak-example-assets/ \
      | grep -o 'https://[^#"]*repak_example_assets-0.3-py3-none-any\.whl[^#"]*' \
      | head -1) \
 && curl -fsSL "$WHL_URL" -o /tmp/bundle.whl \
 && cd /tmp && unzip -q bundle.whl repak_example_assets/payload.tar.gz \
 && echo "a3f9...  repak_example_assets/payload.tar.gz" | sha256sum -c \
 && mkdir -p /etc/service \
 && tar -xzf repak_example_assets/payload.tar.gz -C /etc/service \
 && rm -rf /tmp/bundle.whl /tmp/repak_example_assets
```

The "always latest" snippet selects the newest version by a numeric
`major.minor` sort of the simple index, so it does not depend on the order in
which the index lists files. repak prints both ready-to-paste snippets (with
the real sha256 baked in) after every successful upload.

Both snippets require `curl` and `unzip` in the base image:

```dockerfile
# Alpine
RUN apk add -q curl unzip

# Debian/Ubuntu
RUN apt-get install -y --no-install-recommends curl unzip
```

### Common bundle types

All examples below assume the contents are **public** (see the warning above).

| Bundle | Contents | Extract to |
|---|---|---|
| Example configs | demo nginx.conf, logrotate rules, sysctl.d snippets | `/etc/service` |
| Public CA bundles | published trust stores (`.crt` files) | `/usr/local/share/ca-certificates` |
| Entrypoint scripts | signal handlers, health checks, init helpers | `/usr/local/bin` |
| Developer tooling | `.pylintrc`, `pyproject.toml`, `.pre-commit-config.yaml` | repo root |
| DB fixtures | public SQL seed files, migration scripts | `/docker-entrypoint-initdb.d` |

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

### Private indexes

For data that should not be on public PyPI, point repak at a private index.
`--repository-url` sets the twine upload target; `--index-url` sets the
simple-index base baked into the generated Docker snippets so consumers fetch
from the same place:

```bash
repak --path /path/to/folder \
  --repository-url https://pypi.internal.example.com/legacy/ \
  --index-url https://pypi.internal.example.com/simple
```

Running a private index is its own hosting burden — if you have a container
registry, a `COPY --from=` against an image it hosts is usually the simpler
answer for private data.

## How it works

**Upload side**

1. The directory name is normalized to a PyPI name: `repak-{folder}`.
2. PyPI is queried; a new package starts at `0.1`, an existing repak package
   is bumped. The minor wraps into the major at 100 (`0.99` is followed by
   `1.0`), so there is no upload ceiling. You confirm before overwriting.
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
- **Versioning** is `MAJOR.MINOR` with minor `0`–`99` and an unbounded major
  (`0.1, … 0.99, 1.0, … 1.99, 2.0, …`) — no upload ceiling. PyPI does not
  allow re-uploading an existing version.
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
