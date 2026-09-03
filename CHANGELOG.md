# Changelog

All notable changes to this project are documented in this file. Format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning
follows [Semantic Versioning](specs/05-release-versioning-spec.md).

## [Unreleased]

### Added

- YouTube ad blocking: `src/rules/youtube-adblock-rules.json`
  (`declarativeNetRequest`) blocks known ad/tracking request domains
  (`doubleclick.net`, `googlesyndication.com`, `googleadservices.com`) and
  YouTube's own `/pagead/`, `/api/stats/ads`, `/get_midroll_*` paths;
  `src/content/youtube-adblock.js` complements that by watching for
  YouTube's own `ad-showing` player class and clicking the skip button or
  fast-forwarding past non-skippable in-player video ads — network
  blocking alone can't remove those, since the ad video streams from the
  same googlevideo.com CDN as real content.

### Removed

- The toolbar-popup-to-desktop-app download path (native messaging,
  `background.js`'s relay logic, `src/lib/native-messaging.js`) is gone,
  at the user's explicit request, after being warned this trades away
  reliability (see "Changed" below) and choosing to accept that anyway.
  `backend/` itself is untouched and still works exactly as documented in
  specs 02/03 — it is simply not called by the extension any more.
  Removing it outright is a separate, not-yet-made decision.
- `nativeMessaging`/`host_permissions` dropped from `manifest.json` —
  nothing uses them any more.
- Unused i18n keys (`downloadComplete`, `downloadCancelled`,
  `popupHostUnreachable`, `chooseFolderPrompt`) removed from all four
  locales — none had any remaining code reference after the change above.

### Changed

- **The Download button now tries to save the video directly, client-side
  — no desktop app, but real, accepted trade-offs. Read this before
  assuming it works like the old one did.** `src/content/youtube-extract.js`
  (a data-only content script, no visible UI — nothing for another
  extension to collide with) fetches the current YouTube page fresh,
  reads `ytInitialPlayerResponse`, and looks for a *progressive* format
  (audio+video already combined — the only kind downloadable without
  `ffmpeg`, which a browser extension cannot invoke). The popup hands
  whatever URL comes back straight to `chrome.downloads.download()`.
  Concretely, as of 2026-09-03:
  - Quality is capped at whatever YouTube's progressive format offers
    (typically 360p) — there is no muxing step to combine separate
    higher-quality video-only + audio-only streams.
  - Only YouTube is supported (no more ~1800-site `yt-dlp` breadth).
  - Most progressive formats carry a `signatureCipher` that must be
    deciphered before the URL is usable, using the same
    reverse/remove-from-front/swap-replay technique every
    non-`yt-dlp`-based YouTube downloader relies on (confirmed by
    extracting and reading a real installed extension's own decipher
    code as part of this feature's research). **This currently fails to
    even locate the operation sequence against a live player build for
    an ordinary popular video** — most likely because YouTube's
    server-side adaptive streaming (SABR) rollout moved the WEB client
    off the code shape these patterns look for. A separate `n`-parameter
    (anti-throttling) transform, checked independently, **also** fails
    to locate its function against the same build. Both were verified
    directly against a real, live player build fetched during this
    session — not assumed, and not just this project's first attempt:
    the exact patterns from a real installed extension's decipher code
    were tested too and fail identically.
  - **Net result: the feature only actually succeeds today for the rare
    video whose progressive format needs neither transformation at all**
    (confirmed working on one old/low-traffic video; confirmed failing
    on an ordinary popular one, end-to-end, with this project's actual
    shipped code, via a live headless browser against the real
    youtube.com). Both transform-extraction paths are kept anyway: they
    cost nothing when they fail cleanly, and YouTube ships player builds
    gradually, so some sessions may still get a build one of them
    matches.
  - When extraction fails, the popup shows one honest, generic "couldn't
    download this video directly" message — never a fabricated success.
  See specs/01-extension-spec.md, "Direct download", for the full
  contract, and specs/03-security-spec.md for why evaluating a fragment
  of YouTube's own player JS (`new Function`, flagged `DANGEROUS_EVAL` by
  `web-ext lint`) is an accepted, scoped risk rather than an oversight.
- `strict_min_version` (Firefox) raised from `109.0` to `113.0` —
  `declarative_net_request.rule_resources` (used for ad blocking) isn't
  supported before Firefox 113; declaring it below that version only
  produces a silent no-op on older Firefox, which `web-ext lint` flags.
- `extDescription` (all locales) and `.github/amo-metadata.json`'s
  `summary`/`description` (all locales) rewritten to describe the direct-
  download-attempt + ad-blocking behavior, explicitly calling the
  download feature experimental rather than implying it reliably works.

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
- The button could render on top of the video instead of below it: the
  real player's `<video>` is typically `position: absolute` inside a
  `position: relative` wrapper, and the button's fallback placement
  (used when `#below` isn't found yet) inserts it right after `<video>`
  — a normal-flow sibling in that situation renders at the wrapper's own
  top-left corner, on top of the video, because `#below` can still be a
  few hundred ms from existing even after the player has a real
  `<video>` (YouTube hydrates the page progressively). Placement is now
  re-run for already-created buttons on every rescan
  (`engine.relocate()`), not just for newly found videos, so a button
  stuck in the fallback moves into `#below` the moment it exists.
  Reproduced and verified fixed with a test fixture mimicking the real
  player's DOM shape.
- The button's collision check (previous entries above) never actually
  re-ran against a real "under the player" extension's UI: the backup
  `MutationObserver` was scoped to `document.querySelector('ytd-app')`'s
  subtree, but a real installed extension (Enhancer for YouTube,
  confirmed by extracting and reading its `.xpi` source) appends its
  floating control bar directly to `document.body` — a sibling of
  `ytd-app`, not a descendant — so that insertion was invisible to the
  observer and no rescan (and thus no collision re-check) ever fired
  afterwards, even though the nudge math itself was already correct. Now
  observes `document.body` instead, a strict superset.

### Removed

- The in-page injected "Download" button, and the content script
  (`extension/src/content/`, `extension/src/content/sites/`) that placed
  it, are gone entirely — along with the `content_scripts` entry,
  `host_permissions`, and `optional_host_permissions` in `manifest.json`,
  none of which anything else in the extension used any more. This
  follows the five entries directly above: each one fixed a real,
  reproduced collision between the injected button and another
  extension's own UI in the same "under the player" spot (a
  YouTube-enhancer-style toolbar, in every case) — but with over 20 other
  YouTube/video-download extensions commonly installed alongside this
  one in the wild, fixing collisions against page content this project
  has no control over is an open-ended arms race, not a bounded bug. The
  download trigger moved to the extension's own toolbar popup instead
  (see `specs/01-extension-spec.md`, "Download trigger") — browser
  toolbar chrome is not page content, so there is nothing left for
  another extension's page UI to collide with, full stop.
- Since there is no content script any more, `video.currentSrc` (the
  `blob:`-URL bug fixed above) and YouTube's miniplayer video (the
  duplicate-button bug fixed above) are no longer things this extension
  reads or detects at all — the popup always sends the active tab's own
  `url`/`title` via `chrome.tabs.query()`, which was the actual fix for
  the `blob:`-URL problem in the first place, just arrived at from a
  different direction.

### Changed

- The Download button now lives in the extension's toolbar popup
  (`src/popup/`) instead of being injected into the page: click the
  toolbar icon, then Download. `activeTab` (already a declared
  permission) is what lets the popup read the active tab's real
  `url`/`title` the moment it's opened from the icon — no
  `host_permissions` needed, and no per-site opt-in either, so "other
  sites `yt-dlp` supports" now works the same way as YouTube, with no
  separate permission grant.
- `extDescription` (all locales) and `.github/amo-metadata.json`'s
  `summary`/`description` (all locales) updated to describe the toolbar
  popup instead of the removed in-page button.

### Fixed

- The popup's Download button could get stuck showing "Downloading…"
  forever, with no folder-picker dialog ever appearing and no way out
  short of closing and reopening the popup — reported right after the
  toolbar-popup move above. Root cause: a failed/dropped native-messaging
  connection (host not installed/registered, manifest misconfigured) only
  ever logged a console warning; nothing told the popup its specific
  `requestId` would now never get a response, so it waited forever.
  `background.js` now tracks in-flight `requestId`s and, when the native
  host connection itself fails, synthesizes a
  `download.error` with `message: "host-unreachable"` for each one still
  pending, which the popup shows as a clear "couldn't reach the desktop
  app" message instead of hanging. The popup also keeps its own 20s
  timeout per request (reset on every progress update) as a last-resort
  safety net for anything not explicitly detected this way.
- Found the actual root cause behind the report above, by reproducing it
  directly: spawned `ytdlx_backend.exe` with the same argv Firefox uses
  while a GUI instance was already running (a completely ordinary
  situation — the tray app left open from an earlier session) and sent it
  a harmless `queue.list`. It never responded. The single-instance
  forwarder (a native-messaging-launched process that loses the race to
  bind the loopback port because a GUI instance already owns it) only
  ever forwarded the *request* to the running instance and closed its
  side of the connection immediately — the running instance's response
  had nowhere to go but that process's own stdout, which nothing was
  reading. Every download started while any other instance was already
  running — an extremely common case, not an edge case — silently never
  got anywhere back to the extension. `RequestHandler.handle()` now takes
  a `respond` sink and routes every response for a given `requestId`
  through whichever sink handled that request (the primary's own stdout
  for its direct browser connection, or a specific forwarded connection's
  socket); the forwarder keeps its connection to the running instance
  open and relays every response it reads back over its own stdout, which
  is the end actually attached to the browser's Port. Verified by
  re-running the exact reproduction above against the fix: the same
  `queue.list` now gets its `queue.snapshot` back correctly. Added
  `backend/tests/test_handler.py` covering the sink-routing logic
  directly.

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
