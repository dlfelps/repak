# repak

Package a local directory as a PyPI wheel, publish it, and reproduce it
elsewhere with a single `pip install`.

`repak` packs a directory into a **synthetic wheel**, uploads it to PyPI, and
generates a self-contained `unpak-*` command that reproduces the directory on
any machine that can run `pip install`.

> Only transfer public-domain data. `repak` does not and cannot enforce this —
> it is your responsibility.

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

**Download side (isolated environment)**

```bash
pip install repak-myproject
unpak-myproject /target/landing/folder
```

The entry point verifies the SHA-256 **before writing anything**, then
reproduces the directory. It is fully self-contained — `repak` itself does
not need to be installed on the destination.

## Install

```bash
pip install repak
```

## Usage

The PyPI token is read from the environment (never a flag, so it stays out of
shell history and process listings):

```bash
export PYPI_TOKEN="pypi-..."        # or TWINE_PASSWORD

repak --path /path/to/folder
# or, from inside the folder:
repak

# non-interactive (skip confirmation prompts):
repak --path /path/to/folder --yes
```

Then on the isolated side, once the mirror has synced:

```bash
pip install repak-<folder>
unpak-<folder> /target/landing/folder
```

## Behavior & constraints

- **Extract** is overwrite/merge in place: existing unrelated files are left
  untouched; re-running with the same payload is idempotent.
- **Safety**: tar entries with absolute paths or `..` traversal are rejected;
  a checksum mismatch aborts before any file is written.
- **Versioning** runs `0.1`–`0.99` (99 uploads per package name). PyPI does
  not allow re-uploading an existing version.
- **Name collisions**: if `repak-{folder}` already exists on PyPI but was not
  created by repak (no repak marker), upload is refused.
- **Mirror lag**: propagation from public PyPI to the internal mirror is
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
