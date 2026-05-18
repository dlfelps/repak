# repak

Bundle a public directory once. Everything that re-pulls — a Docker build, a
new project, a teammate's machine — gets the latest version automatically.

`repak` packages a local directory as a versioned, checksum-verified PyPI
wheel and uploads it. Consumers pull it back two ways:

- **With pip** — `pip install -U repak-{name} && unpak-{name} ./dest`. No
  Docker, no clone. Good for scaffolds and shared tool config.
- **Without pip** — a `curl`/`unzip`/`tar` shell snippet. Good for Dockerfiles
  whose base image has no Python.

Either way, the consuming side needs **no repak install** and PyPI does the
hosting, versioning, and CDN delivery for free.

> **Public data only.** Uploading to public PyPI publishes your files to the
> world. Only bundle data you would publish anyway — open-source project
> assets, public test fixtures, public datasets, demo/tutorial configs,
> scaffolds and tool config you'd open-source. `repak` does not and cannot
> enforce this; it is your responsibility. For private data, use a private
> index (see [Private indexes](#private-indexes)) — or a container registry.

> Not related to [`trumank/repak`](https://github.com/trumank/repak), the Rust
> CLI for Unreal Engine `.pak` files. Different tool, same name.

## Is repak the right tool?

repak rides on public PyPI as a free, CDN-backed file host. That only makes
sense for a narrow case. Reach for it only when **all** of the following hold:

- The bundle is **genuinely public** (you would publish it anyway).
- You have **no infrastructure** for the job — no container registry, no
  internal package server, no appetite to run one.
- You want consumers to need **zero specialized tooling** — just `pip`, or
  just `curl`/`unzip`/`tar`.

If you already run a container registry, `COPY --from=registry/...` is the
better answer for build-context files. If you want parameterized project
scaffolding, `cookiecutter`/`copier` do variable substitution that repak does
not. If your shared config lives in a repo people already clone, a git
submodule or a `git clone` is simpler. repak wins only when there is no such
infra and the data is public.

Using PyPI as a generic file host is guest use of infrastructure funded by the
Python Software Foundation and its sponsors. Keep bundles small, don't churn
them needlessly, and move heavy or internal use to a private index.

## What repak transports

repak does one thing: snapshot a directory's **contents** into a versioned,
SHA-256'd artifact and put it where anyone can pull the current version with
zero setup. It is *not* a templating engine and not a sync daemon — it ships a
static snapshot that consumers extract (overwrite/merge) into a destination.

Three use cases fit that shape well.

### 1. Shared bundles for Docker builds

A project maintains public files that many Docker images need — example
configs, seed fixtures, demo datasets. Without repak, those files get
copy-pasted across Dockerfiles and drift the moment anyone edits the source.

With repak, the owning team keeps the files in one directory and runs `repak`
when anything changes; every Dockerfile has one `RUN` line that pulls the
current version. Any rebuild — by anyone, on any machine — gets the latest. No
PRs across a dozen repos. See [Docker consumers](#docker-consumers) for the
ready-to-paste snippets.

### 2. Project scaffolds / starter templates

You start new projects from the same skeleton — CI workflow, linter and
formatter config, `Makefile`, license, a minimal source layout. Keep that
skeleton in a directory and publish it:

```bash
cd my-python-scaffold && repak
```

Starting a new project anywhere, with nothing but pip:

```bash
pip install -U repak-my-python-scaffold
unpak-my-python-scaffold ./new-service
```

Every new project picks up the **current** scaffold. Fix a flaw in your CI
config once, re-run `repak`, and the next project you start has the fix — no
template repo to clone, no scaffolding tool to install on each machine.

> **Snapshot, not template.** repak copies files verbatim. It does *not*
> substitute `{{project_name}}` or run post-generation hooks. If you need
> parameterized generation, use `cookiecutter`/`copier`. repak is for "shared
> starting point you then edit," with versioning and checksums for free.

### 3. Shared, evolving tool config

A set of editor/linter/assistant config that you want identical across many
repos and machines and that **changes over time**: `.editorconfig`,
`.pre-commit-config.yaml`, `ruff.toml`, shared AI-assistant config and prompt
files (e.g. an `.claude/` directory of skills and instructions), shell
dotfiles you'd publish anyway.

```bash
cd my-dev-config && repak
```

On any machine or in any repo:

```bash
pip install -U repak-my-dev-config
unpak-my-dev-config .            # merge into the current repo
# or:  unpak-my-dev-config ~     # into your home dir
```

Edit the config once, re-publish, and `pip install -U` on the next machine
pulls the new version. Extraction is overwrite/merge: your unrelated files are
left untouched. This is the closest repak gets to a "sync" story — it's still
pull-on-demand, not a daemon, but the `pip install -U` step is lighter than
maintaining a dotfiles repo clone or a submodule across N projects.

The alternative — a config repo people `git clone` — is perfectly fine and
often simpler. repak's only edge here is the versioned, checksum-verified,
clone-free `pip install -U` ergonomic for genuinely public config.

### Common bundle contents

All examples assume the contents are **public** (see the warning above).

| Use case | Contents | Typical destination |
|---|---|---|
| Docker assets | demo `nginx.conf`, logrotate rules, seed SQL | `/etc/service`, initdb.d |
| Docker CA bundles | published trust stores (`.crt`) | `/usr/local/share/ca-certificates` |
| Scaffold | CI yaml, `pyproject.toml`, `Makefile`, src skeleton | new project dir |
| Tool config | `.editorconfig`, `.pre-commit-config.yaml`, `ruff.toml` | repo root |
| Assistant config | shared skills / instruction files | `.claude/`, `~` |

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

The PyPI package name is derived from the directory name as `repak-{folder}`,
and the extractor entry point is `unpak-{folder}`. After a successful upload
repak prints **all** consumer commands — the pip `install`/`unpak` pair and
both Dockerfile snippets — with the correct package name and sha256 already
filled in.

### pip consumers (no Docker)

This path needs no generated snippet — it is fully determined by the name:

```bash
pip install -U repak-{folder}     # newest published version
# or pin: pip install repak-{folder}==0.3
unpak-{folder} /path/to/destination
```

`unpak-{folder}` verifies the SHA-256 **before writing anything**, then
reproduces the directory contents at the destination (overwrite/merge in
place). `repak` itself is not needed on the destination.

### Docker consumers

For base images without Python, each consuming Dockerfile picks one mode.
`repak` prints both, filled in, after every upload.

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
which the index lists files. Both snippets require `curl` and `unzip` in the
base image:

```dockerfile
# Alpine
RUN apk add -q curl unzip

# Debian/Ubuntu
RUN apt-get install -y --no-install-recommends curl unzip
```

### Pinned vs. latest

| | Pinned | Always latest |
|---|---|---|
| Behavior | Identical every pull | Pulls current upload |
| sha256 | Baked in at publish time | Read from bundle at extract time |
| Recommended for | Production images, reproducible builds | Active development, scaffolds, shared config |

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
pip install -U repak-myproject
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

No dependency resolution, no templating or variable substitution (the wheel is
a transport container for a static snapshot), no sync daemon, no "correct"
packaging, no git integration (clone/prepare the directory yourself), and no
repak install required on the destination side.

## Development

```bash
pip install -e ".[dev]"
pytest -q          # full suite, incl. venv install + roundtrip e2e
```

## License

MIT
