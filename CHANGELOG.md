# Changelog

All notable changes to this project are documented in this file. Format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning
follows [Semantic Versioning](specs/05-release-versioning-spec.md).

## [Unreleased]

### Changed

- Extension name changed from a translated "Video Download Button" /
  "Botón de Descarga de Video" style name to the literal
  `youtubedownloadxtension` across every locale and the AMO listing name,
  so the name shown in the browser toolbar, the extension manager, and the
  Firefox Add-ons store page all match.
- Extension icons (`extension/src/icons/icon-{16,32,48,128}.png`) are now
  generated directly from `backend/ytdlx_backend/assets/icon.ico` — the
  same icon the desktop app uses — instead of a separately-generated set,
  so the toolbar icon, AMO listing icon, and desktop app icon match.
- Filled in previously-empty AMO listing fields (`description`,
  `homepage`, `support_url`) in `.github/amo-metadata.json`; `tags` is
  deliberately left out since AMO validates it against a server-side list
  this project hasn't confirmed.

### Fixed

- The injected Download button's shadow-host `<div>` could visually
  collide with UI injected by other extensions in the same "under the
  player" area (reported with a YouTube-enhancer-style extension's own
  toolbar) — `all: initial`, used to isolate the host from page styles,
  also silently reset `display` to its CSS-initial value (`inline`),
  leaving the host with no guaranteed own row or stacking context. The
  host now explicitly sets `display: block`, `position: relative`, and a
  high `z-index` after `all: initial`.
- The previous fix stopped the button from sharing a line box with other
  content, but a follow-up report showed it could still render flush
  against another extension's floating toolbar in the same spot (a
  `display: block` sibling isn't visually separated from an
  absolutely-positioned/floated element that doesn't participate in
  normal flow). The button now checks, right after placement and again
  ~500ms later, whether anything foreign renders at its own screen
  position (via `elementFromPoint` with itself temporarily
  `pointer-events: none`) and nudges itself down with `margin-top`,
  bounded, until clear. Verified against a local test fixture reproducing
  a fixed floating toolbar under the player.
- Clicking Download did nothing on YouTube: the click handler sent
  `video.currentSrc`, which on YouTube (and any other site using Media
  Source Extensions for adaptive streaming) is always a `blob:` URL --
  only resolvable inside that page's own JS context, so yt-dlp could
  never do anything with it. Now sends `location.href` instead whenever
  `currentSrc` is empty or a `blob:` URL, keeping `currentSrc` only for a
  generic site with a plain progressive `<video src="https://...">`.
  Verified the URL-selection logic directly (blob/empty -> page URL,
  real direct file URL -> kept as-is).
- YouTube's floating miniplayer could keep its own `<video>` on the page
  alongside the main one, each independently passing the real-video
  check and getting its own "Download" button — two identical buttons
  for what looks like one video. The per-site scan now skips any
  `<video>` whose `closest("ytd-miniplayer")` is non-null.



## [0.1.10] - 2026-08-26

### Fixed

- The Firefox `listed` submission was actually *succeeding* (accepted by
  AMO, queued for review) but `publish-firefox-amo` still reported it as a
  job failure, because `web-ext sign` polls for a review decision and
  exits nonzero once its wait times out — expected for `nativeMessaging`
  extensions, which are more likely to need a longer manual review than
  any CI job should block on. The job now recognizes the specific
  "Approval: timeout exceeded" outcome as success-but-pending (logs the
  AMO review-status link, skips attaching a `.xpi` to that release) and
  only fails on a genuine rejection/validation error.

## [0.1.9] - 2026-08-25

### Fixed

- The `listed` submission to AMO still failed after adding license/category
  metadata: `"es"` is not a valid AMO summary locale code (`"The language
  code \"es\" is invalid"`); changed to the region-qualified `"es-ES"` in
  `.github/amo-metadata.json`. `"fr"` and `"pt-BR"` were accepted as-is.

## [0.1.8] - 2026-08-25

### Fixed

- The first `listed` submission to AMO failed outright ("This field, or
  custom_license, is required for listed versions.") — `web-ext sign` has
  no CLI flag for license/category/summary, so they're now supplied via
  `--amo-metadata=.github/amo-metadata.json` (Apache-2.0 license,
  "download-management" category, a short per-locale summary).

## [0.1.7] - 2026-08-25

### Changed

- Firefox publishing switched from `unlisted` to `listed`: the extension
  is now submitted for Mozilla's public review and a searchable listing on
  addons.mozilla.org, not just signed for direct/self distribution. First
  review may take minutes to a few days.

## [0.1.6] - 2026-08-25

### Added

- `workflow_dispatch` trigger on the release workflow, so it can be re-run
  manually (e.g. right after configuring a store's secrets for the first
  time) without needing a throwaway commit.

### Changed

- Firefox (AMO) signing is now live: `AMO_JWT_ISSUER`/`AMO_JWT_SECRET` are
  configured, so `publish-firefox-amo` signs a real `.xpi` and attaches it
  to every release from now on.

## [0.1.5] - 2026-08-24

### Changed

- Store publishing priority decided: Firefox (AMO) and Microsoft Edge
  Add-ons are the active targets (both free); Chrome Web Store is on hold
  because of its one-time $5 fee and stays implemented-but-dormant. The
  existing Firefox Sync account works directly for AMO — no separate
  Mozilla account needed. See `specs/06-store-publishing-spec.md` and the
  `store-publish` skill (reordered accordingly).

## [0.1.4] - 2026-08-23

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
