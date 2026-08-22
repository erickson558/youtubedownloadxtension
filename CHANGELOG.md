# Changelog

All notable changes to this project are documented in this file. Format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning
follows [Semantic Versioning](specs/05-release-versioning-spec.md).

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
