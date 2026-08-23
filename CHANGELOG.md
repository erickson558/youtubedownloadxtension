# Changelog

All notable changes to this project are documented in this file. Format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning
follows [Semantic Versioning](specs/05-release-versioning-spec.md).

## [Unreleased]

### Added

- Store publishing pipeline: `publish-firefox-amo`, `publish-chrome-webstore`,
  and `publish-edge-addons` jobs in the release workflow, each self-skipping
  until its store's credentials are configured as GitHub secrets — see
  `specs/06-store-publishing-spec.md` and the new `store-publish` skill for
  the one-time manual account setup each requires (Firefox AMO signing is
  free and fully API-driven; Chrome Web Store costs a one-time $5 fee;
  Edge Add-ons is free — both need one manual first upload via their
  dashboards before automation takes over).

### Fixed

- The Chrome Web Store publish job referenced a third-party GitHub Action
  (`mnao305/chrome-extension-upload-action`) that doesn't exist — GitHub
  Actions resolves every `uses:` in a job during "Set up job" before any
  step's `if:` runs, so the invalid reference failed the job outright
  instead of skipping it, which blocked `publish-release` entirely and
  silently dropped the v0.1.3 release (a tag was pushed, but no GitHub
  Release was ever published). Fixed by calling the official Chrome Web
  Store API directly with `curl` instead, and by adding an `always()`
  guard to `publish-release` so a real failure in any best-effort
  store-publish job can never block the release again.
- The built `.exe` failed to actually run yt-dlp: inside a frozen
  PyInstaller build, `sys.executable` is the app itself, so the dev-mode
  `python -m yt_dlp` invocation silently did nothing. Fixed by having the
  frozen exe re-invoke itself with an internal sentinel argument that runs
  yt-dlp's own CLI entry point, verified against the compiled `.exe`.
- Multi-language auto-detection never engaged on Windows: `LANG`/`LC_ALL`/
  `LC_MESSAGES` are not set by default on Windows (confirmed on a real
  Spanish-locale machine), so the app always silently fell back to
  English. Now reads the Windows UI language directly via
  `GetUserDefaultUILanguage()` before falling back to the POSIX env vars.
- The GitHub Actions release workflow interpolated the raw commit message
  into a shell script (`${{ github.event.head_commit.message }}` inlined
  into `run:`), so a message containing backticks was re-parsed as shell
  command substitution — this actually broke the first live release run.
  Fixed by passing it through `env:` instead.
- The release workflow's version-sync step never updated the README
  version badge, despite `specs/05-release-versioning-spec.md` listing it
  as a required sync target — the badge stayed stuck on `0.1.0` through
  the `v0.1.1` release. Now synced alongside `manifest.json` and
  `__version__.py`.
- `pip-audit` flagged 33 known vulnerabilities against the pinned
  `yt-dlp==2024.8.6` and `Pillow==10.4.0`; bumped to `2026.7.4` and
  `12.3.0` respectively (also bumped `ruff`, `pip-audit`, `pyinstaller`,
  and the pinned GitHub Actions to their Dependabot-proposed versions).
- Minor lint fixups surfaced by the `ruff` bump (nested `with` statements,
  an unnecessary `range()` start argument) — no behavior change.

### Changed

- The compiled `.exe` now lands in `backend/ytdlx_backend/`, next to
  `main.py` and the `.ico` it's built from, instead of a `dist/`
  subfolder — matching the project's packaging requirement. Building it
  now requires `--distpath backend/ytdlx_backend` (documented in the
  README, the release workflow, and the `release-automation` skill).

## [0.1.0] - 2026-08-22

### Added

- Initial project scaffold: Manifest V3 browser extension (Chrome/Edge/
  Brave + Firefox 109+) that injects a download button under YouTube
  videos, surviving SPA navigation.
- Python native-messaging host + Tkinter desktop app with a system tray
  icon and download queue/progress view, using `yt-dlp` for the actual
  download.
- Every download prompts for a destination folder via a native dialog.
- i18n: English, Spanish, Portuguese, French, in both the extension and the
  desktop app.
- "Buy me a beer" donation link in the extension popup/options and the
  desktop app's About dialog.
- Spec-driven development artifacts under `specs/`.
- Claude Code project agents (`extension-engineer`, `backend-engineer`,
  `release-devops`, `security-reviewer`) and skills (`github-publish`,
  `release-automation`, `thorough-code-comments`, `security-audit`).
- CI (lint + tests), CodeQL scanning, Dependabot, and an automated release
  workflow that builds the extension packages and a windowed Windows `.exe`
  and publishes them to GitHub Releases on every push to `main`.
- Apache License 2.0.
