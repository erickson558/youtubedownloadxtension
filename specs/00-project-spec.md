# 00 — Project Spec

## Purpose

`youtubedownloadxtension` lets a person save, for their own personal/offline
use, a video they are watching in their browser. Clicking the toolbar
popup's Download button sends the current tab's page URL to a local
desktop companion app (the *native host*, `backend/`), which launches
automatically, asks where to save the file, downloads it using
[`yt-dlp`](https://github.com/yt-dlp/yt-dlp), and closes itself
automatically once done (see [[02-native-host-spec]], "Auto-close on
settle"). It also blocks YouTube ads.

This is the same category of tool as `yt-dlp` itself or the long-standing
"Video DownloadHelper" browser extension: a personal-use downloader, not a
piracy or redistribution tool.

## Scope

- Browser extension (Manifest V3) for Chromium-based browsers (Chrome, Edge,
  Brave) and Firefox 113+.
- A Download button on the extension's own toolbar popup, sending the
  active tab's URL to the desktop companion app over native messaging —
  see [[01-extension-spec]], "Download trigger", and "History" for why a
  fully client-side (no desktop app) design was tried and abandoned.
- A Python desktop companion app (Windows `.exe` first) that:
  - Acts as the WebExtensions **Native Messaging** host for the extension,
    launched automatically by the browser and closing itself automatically
    once a download settles (see [[02-native-host-spec]]).
  - Also runs as a normal windowed app with a system tray icon showing the
    download queue and progress, when the user opens it directly instead
    (in which case it behaves like an ordinary desktop app and does not
    auto-close).
  - Performs the actual download via `yt-dlp`.
- Automatic YouTube ad blocking (request blocking + in-player skip/fast-
  forward) — see [[01-extension-spec]], "Ad blocking". Unrelated to the
  download mechanism; kept through every download-design change so far.
- Spec-driven development: every new capability starts as a change to the
  relevant spec in this directory (see `templates/change-proposal-template.md`)
  before implementation.

## Non-goals (for now)

- No support for sites that require login/DRM-protected streams (yt-dlp itself
  cannot bypass DRM; this project does not attempt to).
- No macOS/Linux packaged builds in the first milestones (the *code* is
  written to be portable, but only the Windows `.exe` is built/released
  initially — see `05-release-versioning-spec.md`).
- No bundling or redistribution of downloaded copyrighted content — this is a
  single-user local tool, not a hosting/sharing service.
- No client-side (no-desktop-app) YouTube extraction — tried and abandoned;
  see [[01-extension-spec]], "History". YouTube's SABR streaming protocol
  and PoToken (bot-attestation) requirement need infrastructure (a real
  BotGuard-challenge-solving JS runtime, or a separate helper server) a
  browser extension's sandbox cannot provide.
- "Any video site" support is best-effort: YouTube is the fully-specified,
  tested target; other sites work to the extent `yt-dlp`'s extractor list
  already supports them. The popup always sends the active tab's own URL
  (see [[01-extension-spec]], "Download trigger") with no in-page
  detection or per-site permission grant at all — it is `yt-dlp` itself,
  not this extension, that determines whether a given site's URL can
  actually be extracted.

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
first run of the extension (see `01-extension-spec.md`) and first run of the
desktop app.

## Target environments

| Component | Target |
|---|---|
| Browser extension | Chrome/Edge/Brave (latest 2 major versions), Firefox ESR/release ≥ 113 |
| Desktop app | Windows 10/11 x64 (packaged); source runs anywhere Python 3.11+ + Tk are available |
| Backend download engine | `yt-dlp` (pinned version, see `requirements.txt`) |

## Related specs

- [[01-extension-spec]] — extension behavior contract
- [[02-native-host-spec]] — native messaging protocol + backend behavior
- [[03-security-spec]] — threat model and mitigations
- [[04-i18n-spec]] — supported locales and fallback rules
- [[05-release-versioning-spec]] — versioning policy and release artifacts
- [[06-store-publishing-spec]] — Firefox AMO / Chrome Web Store / Edge Add-ons publishing
