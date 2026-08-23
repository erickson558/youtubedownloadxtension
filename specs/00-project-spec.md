# 00 — Project Spec

## Purpose

`youtubedownloadxtension` lets a person save, for their own personal/offline use,
a video they are watching in their browser. It adds a "Download" button under
every detected `<video>` element. Clicking it sends the page URL to a local
desktop companion app (the *native host*), which asks where to save the file
and downloads it using [`yt-dlp`](https://github.com/yt-dlp/yt-dlp).

This is the same category of tool as `yt-dlp` itself or the long-standing
"Video DownloadHelper" browser extension: a personal-use downloader, not a
piracy or redistribution tool.

## Scope

- Browser extension (Manifest V3) for Chromium-based browsers (Chrome, Edge,
  Brave) and Firefox 109+.
- A button injected under the video player on YouTube watch pages.
- A Python desktop companion app (Windows `.exe` first) that:
  - Acts as the WebExtensions **Native Messaging** host for the extension.
  - Also runs as a normal windowed app with a system tray icon showing the
    download queue and progress.
  - Performs the actual download via `yt-dlp`.
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
- "Any video site" support is best-effort: YouTube is the fully-specified,
  tested target; other sites work to the extent `yt-dlp`'s extractor list
  already supports them, via a generic `<video>`-detection fallback.

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
| Browser extension | Chrome/Edge/Brave (latest 2 major versions), Firefox ESR/release ≥ 109 |
| Desktop app | Windows 10/11 x64 (packaged); source runs anywhere Python 3.11+ + Tk are available |
| Backend download engine | `yt-dlp` (pinned version, see `requirements.txt`) |

## Related specs

- [[01-extension-spec]] — extension behavior contract
- [[02-native-host-spec]] — native messaging protocol + backend behavior
- [[03-security-spec]] — threat model and mitigations
- [[04-i18n-spec]] — supported locales and fallback rules
- [[05-release-versioning-spec]] — versioning policy and release artifacts
- [[06-store-publishing-spec]] — Firefox AMO / Chrome Web Store / Edge Add-ons publishing
