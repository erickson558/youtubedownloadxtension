---
name: release-automation
description: Cut a release of this project - sync versions, tag, let CI build the extension zips and Windows exe, verify the GitHub Release. Trigger phrases- "cut a release", "bump the version", "publica la version X.Y.Z", "haz un release".
---

# Release Automation

This is the human-readable runbook counterpart to `.github/workflows/release.yml`
(owned by the `release-devops` agent). Use it to trigger a release manually,
verify one that ran automatically, or debug one that failed. The policy
behind every step here is `specs/05-release-versioning-spec.md` — read it if
anything below seems to conflict with what you observe in the repo.

## 1. Decide the bump

- **MAJOR**: breaking native-messaging protocol change, breaking manifest
  permission change, removed feature.
- **MINOR**: new capability, backward compatible (new site, new locale, new
  UI).
- **PATCH**: bug fix, dependency bump (including routine `yt-dlp` bumps),
  docs, CI-only change.

## 2. Sync the version everywhere (if not already done by CI)

Single source of truth is `/VERSION`. Update it, then propagate:

```sh
NEW_VERSION="X.Y.Z"
echo "$NEW_VERSION" > VERSION
```

Then update, by hand or with a small script:
- `extension/manifest.json` → `"version": "X.Y.Z"`
- `backend/ytdlx_backend/__version__.py` → `__version__ = "X.Y.Z"`
- `README.md` version badge

Update `CHANGELOG.md` with a new `## [X.Y.Z] - YYYY-MM-DD` section
summarizing user-facing changes (Keep a Changelog format).

## 3. Commit, tag, push

```sh
git add VERSION extension/manifest.json backend/ytdlx_backend/__version__.py README.md CHANGELOG.md
git commit -m "chore(release): v$NEW_VERSION [skip release]"
git tag "v$NEW_VERSION"
git push origin main --tags
```

The `[skip release]` marker is required in this exact commit so
`release.yml` doesn't try to re-trigger itself on its own version-bump push.

## 4. Let CI build, or build locally to debug

CI (`release.yml`) builds three artifacts on push to `main`:
`ytdlx-chrome-vX.Y.Z.zip`, `ytdlx-firefox-vX.Y.Z.zip`,
`ytdlx-backend-vX.Y.Z-windows.exe`. To reproduce locally:

```sh
# extension packages
npx web-ext build --source-dir=extension --artifacts-dir=build --overwrite-dest

# windows exe (must run on Windows / a Windows runner)
pip install -r backend/requirements.txt pyinstaller
pyinstaller backend/pyinstaller.spec
```

## 5. Publish the GitHub Release

If not already done by CI:

```sh
gh release create "v$NEW_VERSION" \
  build/ytdlx-chrome-*.zip \
  build/ytdlx-firefox-*.zip \
  backend/dist/ytdlx-backend-*-windows.exe \
  --title "v$NEW_VERSION" \
  --generate-notes
```

## 6. Verify

- `gh release view v$NEW_VERSION` — confirm exactly three assets attached.
- Unzip the extension artifacts and check `manifest.json`'s `version` field
  matches the tag.
- Run the `.exe` once and check its About/version display matches.
- Confirm the tag, the release title, `VERSION`, `manifest.json`, and
  `__version__.py` all agree — if any of them disagrees, do not consider the
  release done; fix and re-tag rather than leaving a mismatched release live.
