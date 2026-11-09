# Release Runbook

Step-by-step procedure for publishing a Whisper-Code release on GitHub with the
`gh` CLI. This is the pattern used for v1.0.1 (2026-11-09); follow it in order —
each step produces the evidence the next step claims.

`docs/PACKAGING.md` covers PyInstaller spec/DMG basics in the abstract. This
document is the concrete, verified flow for *this* repository, including the two
failure modes we hit (a 422 from `--target`, and a verification grep that proves
nothing).

---

## What a release produces

| Output | Location |
| --- | --- |
| Annotated tag `vX.Y.Z` | `origin` (`refs/tags/vX.Y.Z`) |
| GitHub release, marked Latest | `https://github.com/lekodeveloperweb/whisper-code/releases/tag/vX.Y.Z` |
| Asset: single-file executable | `dist/Whisper-Code` (gitignored) |
| Asset: app bundle zip | `dist/Whisper-Code.app.zip` (gitignored) |
| Dated `CHANGELOG.md` entry | `## [X.Y.Z] - YYYY-MM-DD` |

---

## 0. Prerequisites

```bash
git remote -v                 # must be github.com:lekodeveloperweb/whisper-code.git
gh auth status                # account lekodeveloperweb, scopes: repo, read:org
uv sync                       # keep .venv in lockstep with uv.lock
```

The repo also has a Gitea skill and `tea` installed. **Check the remote before
choosing a CLI** — this project is on GitHub, so every hosting command here is
`gh`, not `tea`.

`dist/` and `build/` are gitignored, so artifacts are never committed; they only
travel as release assets.

---

## 1. Pre-flight checks

Everything below must be green before touching a version number. Run them from
a clean tree (`git status --short` prints nothing).

```bash
QT_QPA_PLATFORM=offscreen uv run pytest tests/ -q
uv run mypy src/
uv run ruff check src/<changed> tests/<changed>
uv run ruff format --check src/<changed> tests/<changed>
```

Smoke-run the app from source so a UI regression is caught before it is built
into an artifact:

```bash
uv run whisper & APP_PID=$!; sleep 6; kill -0 $APP_PID && echo "RUNNING"; kill $APP_PID
```

!!! note "Known repo lint debt"

    `uv run ruff check .` currently reports pre-existing issues in files you did
    not touch. Do not claim repo-wide green. Prove you added none:

    ```bash
    uv run ruff check --output-format=concise . | sort > /tmp/after.txt
    git stash -q && uv run ruff check --output-format=concise . | sort > /tmp/before.txt
    git stash pop -q
    comm -13 /tmp/before.txt /tmp/after.txt    # empty == no new issues
    ```

---

## 2. Freeze the changelog

Rename the `Unreleased` heading to the version and the real UTC date, so the
notes you publish match the notes in the repo:

```bash
/bin/date -u +%Y-%m-%d        # trust this, not the crash-log timestamp
```

```diff
- ## [Unreleased]
+ ## [1.0.1] - 2026-11-09
```

```bash
git add CHANGELOG.md
git commit -m "docs(changelog): date the 1.0.1 entry"
```

If the tag already exists but points before this commit, retarget it now (step 7
explains why this is only allowed while the tag is unpublished):

```bash
git tag -f -a v1.0.1 -m "Release v1.0.1"
```

---

## 3. Bump the version

Two places hold the version and they must agree. Either use the script (it
commits and tags for you):

```bash
bash scripts/build-mac.sh --patch --build     # or --minor / --major
```

…and it does: update `pyproject.toml` + `src/whisper_code/__init__.py`, `git add`
both, commit `bump version X`, `git tag -a vX`, then build.

Or edit by hand and verify:

```bash
grep -n '^version' pyproject.toml
uv run python -c "from src.whisper_code import __version__; print(__version__)"
```

Both must print the new version, and `vX.Y.Z` must be the tag you intend to
release.

---

## 4. Build the artifact

```bash
bash scripts/build-mac.sh --build
```

The script runs `rm -rf build dist` then
`uv run pyinstaller --clean scripts/whisper-code.spec`, which emits both the
one-file executable and the `.app` bundle. Expected tail of the log:

```
✅ Build complete! dist/Whisper-Code.app ( 43M)
```

Confirm the artifact is newer than the commit you are about to ship — a stale
`dist/` is how an unchanged binary gets released under a new version number:

```bash
stat -f "%Sm %N" dist/Whisper-Code dist/Whisper-Code.app/Contents/MacOS/Whisper-Code
git log -1 --format=%cd
```

---

## 5. Prove the artifact contains the change

Do not skip this. A released binary that does not contain the fix is worse than
no release, and the obvious check is a trap:

```bash
grep -ac setContextMenu dist/Whisper-Code      # 0 — also 0 for symbols that ARE there
```

Bytecode is marshalled inside the archive, so a plain `grep` returns 0 for
**every** symbol and proves nothing either way. Read the embedded PYZ instead:

```bash
uv run python - <<'PY'
import types
from PyInstaller.archive.readers import CArchiveReader

archive = CArchiveReader("dist/Whisper-Code")
pyz = archive.open_embedded_archive("PYZ.pyz")          # toc key is 'PYZ.pyz'
code = pyz.extract("src.gui.tray_menu")                  # returns a code object

def symbols(obj, acc):
    acc.update(obj.co_names)
    for const in obj.co_consts:
        if isinstance(const, types.CodeType):
            symbols(const, acc)
    return acc

syms = symbols(code, set())
for name in ("MENU_REASONS", "_show_menu", "_on_activated", "setContextMenu"):
    print(f"{name:16s}:", name in syms)
PY
```

Pass criterion: the symbols the fix **added** print `True`, the call the fix
**removed** prints `False`. Substitute the module and symbol names for your
change. Two API traps: `archive.toc` is a **dict** (`list(toc)` for names;
`[t[0] for t in toc]` yields single characters), and the PYZ key is `PYZ.pyz`,
not `PYZ-00.pyz`.

---

## 6. Stage the assets

Asset names follow the convention set by v1.0.0/v1.0.1 — keep them stable, users
and scripts link to them:

| Asset | Built from | Command |
| --- | --- | --- |
| `Whisper-Code` | `dist/Whisper-Code` | (as built) |
| `Whisper-Code.app.zip` | `dist/Whisper-Code.app` | `ditto -c -k --sequesterRsrc --keepParent Whisper-Code.app Whisper-Code.app.zip` |

```bash
cd dist
rm -f Whisper-Code.app.zip
ditto -c -k --sequesterRsrc --keepParent Whisper-Code.app Whisper-Code.app.zip
shasum -a 256 Whisper-Code Whisper-Code.app.zip
```

Use `ditto`, not `zip -r`: `ditto` preserves bundle metadata and resource forks,
so the unzipped `.app` launches and keeps its icon. Record the SHA-256s; step 8
publishes them.

---

## 7. Push the commit and the tag

```bash
git push origin main
git push origin refs/tags/v1.0.1
git ls-remote --tags origin | tail -3      # v1.0.1^{} must be your HEAD sha
```

Plain `git push` does **not** push tags — the tag push is a separate refspec
(alternatively `git push origin main --follow-tags`).

Retargeting a tag (`git tag -f`) is only acceptable while it has never been
pushed. Once published, a tag is public history: force-moving it leaves clones
and CI caches pointing at an old commit.

---

## 8. Compose the release notes

Write them to a file — heredoc/`--notes-file` avoids shell-quoting damage to
backticks and `$`:

```bash
$EDITOR /tmp/rel-1.0.1.md
```

House style is the one used by `docs/RELEASE-v1.0.0.md` and the v1.0.1 release:
header block, Overview, what changed with **Cause** and **Fix**, Verification
with real command output, Changed Files table, a compare link, an Assets table
carrying the SHA-256s from step 6, then Requirements / Install / Hotkeys / Known
Limitations. Skeleton:

```markdown
# Whisper-Code vX.Y.Z Release Notes

**Release Date:** YYYY-MM-DD
**Version:** X.Y.Z
**Build:** <one-line characterization>

---

## Overview

<what this release is, in two sentences>

## Fixed

### <symptom as the user sees it>

```
<the actual error text>
```

**Cause.** <why it happened, naming the file/line or upstream component>

**Fix.** <what changed, and why the change removes the code path>

## Verification

- `<command>` — <actual output, e.g. "241 passed">
- <native/manual check performed>

## Changed Files

| File | Change |
| --- | --- |
| `src/...` | <one line> |

Full diff: https://github.com/lekodeveloperweb/whisper-code/compare/vA.B.C...vX.Y.Z

## Assets

| Asset | Description | SHA-256 |
| --- | --- | --- |
| `Whisper-Code` | Single-file executable (arm64) | `<sha>` |
| `Whisper-Code.app.zip` | macOS app bundle (zip) | `<sha>` |

## Requirements / Install / Hotkeys / Known Limitations

<carry forward from the previous release, edited only if reality changed>
```

State the signing status honestly. Builds here are **not** code-signed or
notarized — the `codesign` / `xcrun notary` commands in `docs/PACKAGING.md` are
placeholders with a dummy Developer ID — so the notes must tell users to
right-click → **Open** on first launch.

---

## 9. Create the release

```bash
gh release create v1.0.1 \
  dist/Whisper-Code dist/Whisper-Code.app.zip \
  --repo lekodeveloperweb/whisper-code \
  --title "v1.0.1" \
  --notes-file /tmp/rel-1.0.1.md \
  --latest
```

~90 MB of assets; expect the command to take a while (give it several minutes,
not seconds).

!!! failure "Gotcha: `--target <sha>` returns HTTP 422"

    ```
    HTTP 422: Validation Failed
    Release.target_commitish is invalid
    ```

    GitHub only accepts a branch or tag name for `target_commitish`, and the
    flag is meaningless once the tag exists on the remote. **Omit `--target`** —
    the release attaches to the pushed tag.

---

## 10. Verify the published release

Never finish on "the command exited 0". Confirm what GitHub actually serves:

```bash
gh release view v1.0.1 --repo lekodeveloperweb/whisper-code \
  --json tagName,name,assets,publishedAt,url \
  -q '{tag: .tagName, name: .name, url: .url, assets: [.assets[] | {name, size, state}]}'

gh release list --limit 5                 # vX.Y.Z must be marked Latest
```

Round-trip the hosted bytes and check them against the hashes printed in the
release body — this is the step that makes the SHA-256 table a claim about the
published artifact rather than about a local file:

```bash
rm -rf /tmp/wc-dl && mkdir -p /tmp/wc-dl
gh release download v1.0.1 --repo lekodeveloperweb/whisper-code --dir /tmp/wc-dl
shasum -a 256 /tmp/wc-dl/* dist/Whisper-Code dist/Whisper-Code.app.zip | sort
```

Each hosted file must share its digest with its local counterpart. Then tidy up:

```bash
rm -rf /tmp/wc-dl /tmp/rel-1.0.1.md
git status --short                        # clean tree
```

---

## Correcting a published release

```bash
gh release edit v1.0.1 --repo <repo> --draft=true          # hide while fixing
gh release delete-asset v1.0.1 <asset> --repo <repo> --yes  # drop one asset
gh release upload v1.0.1 <file> --repo <repo> --clobber     # replace an asset
gh release edit v1.0.1 --repo <repo> --draft=false --latest
gh release view v1.0.1 --repo <repo>                       # re-verify
```

If the tag itself must move, prefer a new patch version over rewriting the
published tag; retargeting requires deleting the remote tag
(`git push origin :refs/tags/vX.Y.Z`) and is user-visible.

---

## Release checklist

- [ ] `pytest`, `mypy`, `ruff` (changed files) green; no new repo-wide lint debt
- [ ] App smoke-run from source stays alive
- [ ] `CHANGELOG.md` heading dated (`## [X.Y.Z] - YYYY-MM-DD`)
- [ ] `pyproject.toml` and `src/whisper_code/__init__.py` agree on `X.Y.Z`
- [ ] `dist/` rebuilt and newer than the release commit
- [ ] PYZ inspection confirms added symbols present, removed call absent (step 5)
- [ ] Assets named `Whisper-Code` + `Whisper-Code.app.zip`, built with `ditto`
- [ ] Commit **and** tag pushed; `ls-remote` shows the intended sha
- [ ] Notes written to a file, with real command output and both SHA-256s
- [ ] `gh release create` without `--target`; `--latest` set
- [ ] Downloaded assets hash-match local files; release listed as Latest
