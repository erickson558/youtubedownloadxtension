# 00 — Project Spec

## Purpose

`youtubedownloadxtension` lets a person save, for their own personal/offline
use, a YouTube video they are watching, directly from the browser toolbar —
no separate app to install. It also blocks YouTube ads. This is a deliberate
trade-off: quality is capped (see [[01-extension-spec]], "Direct download")
and it only works for some videos, in exchange for nothing to install.

This is the same category of tool as `yt-dlp` itself or the long-standing
"Video DownloadHelper" browser extension: a personal-use downloader, not a
piracy or redistribution tool.

## Scope

- Browser extension (Manifest V3) for Chromium-based browsers (Chrome, Edge,
  Brave) and Firefox 113+.
- A Download button on the extension's own toolbar popup. On a YouTube
  video page, it extracts a direct file URL client-side and hands it to the
  browser's own downloads API — see [[01-extension-spec]], "Direct
  download", for exactly what this can and cannot do, and why.
- Automatic YouTube ad blocking (request blocking + in-player skip/fast-
  forward) — see [[01-extension-spec]], "Ad blocking".
- Spec-driven development: every new capability starts as a change to the
  relevant spec in this directory (see `templates/change-proposal-template.md`)
  before implementation.

## Not currently used, but still in the repository

`backend/` — a Python desktop companion app that acts as a WebExtensions
native-messaging host and downloads via `yt-dlp` (any of ~1800 sites, full
quality, muxed audio+video) — predates the current design and is not called
by the extension any more (see [[01-extension-spec]], "History"). It still
works exactly as documented in [[02-native-host-spec]] and
[[03-security-spec]]. Keeping vs. removing it outright is a separate,
not-yet-made decision; don't assume it's dead code to delete opportunistically,
and don't assume it's wired up to anything either.

## Non-goals (for now)

- No support for sites that require login/DRM-protected streams.
- No bundling or redistribution of downloaded copyrighted content — this is a
  single-user local tool, not a hosting/sharing service.
- No attempt at yt-dlp's ~1800-site breadth or at qualities above what a
  progressive (pre-muxed) YouTube format offers — both require the desktop
  app in `backend/`, which the extension does not currently use.
- No guarantee the direct-download feature keeps working: it depends on
  reverse-engineered details of YouTube's own player that change without
  notice, and is explicitly best-effort (see [[01-extension-spec]]).

## Legal / ethical disclaimer (canonical text)

> This tool is provided for downloading content you have the right to save
> for personal, offline use (e.g. your own uploads, Creative-Commons/public
> domain videos, or content whose platform ToS/license permits it).
> Downloading from a platform can violate that platform's Terms of Service
> even when it is technically possible — that is a contract matter between
> you and the platform, independent of copyright law. You are solely
> responsible for how you use this tool. The authors do not host, distribute,
> or have access to any content you download.

This exact text must appear in `README.md` and be shown once to the user on
first run of the extension (see `01-extension-spec.md`).

## Target environments

| Component | Target |
|---|---|
| Browser extension | Chrome/Edge/Brave (latest 2 major versions), Firefox ESR/release ≥ 113 |
| `backend/` (currently unused by the extension) | Windows 10/11 x64 (packaged); source runs anywhere Python 3.11+ + Tk are available |

## Related specs

- [[01-extension-spec]] — extension behavior contract
- [[02-native-host-spec]] — native messaging protocol + backend behavior (currently unused)
- [[03-security-spec]] — threat model and mitigations
- [[04-i18n-spec]] — supported locales and fallback rules
- [[05-release-versioning-spec]] — versioning policy and release artifacts
- [[06-store-publishing-spec]] — Firefox AMO / Chrome Web Store / Edge Add-ons publishing
