# youtubedownloadxtension

![version](https://img.shields.io/badge/version-0.1.15-blue) ![license](https://img.shields.io/badge/license-Apache--2.0-green)

A browser extension (Chrome, Edge, Brave, Firefox) that adds a **Download**
button under every YouTube video, paired with a small Python desktop
companion app that performs the actual download via
[`yt-dlp`](https://github.com/yt-dlp/yt-dlp).

> **Before you use this**: this tool is for downloading content you have
> the right to save for personal, offline use (your own uploads,
> Creative-Commons/public-domain videos, or content whose platform terms
> permit it). Downloading from a platform can violate that platform's Terms
> of Service even when it is technically possible — that is a contract
> matter between you and the platform, separate from copyright law. You are
> solely responsible for how you use this tool. The authors do not host,
> distribute, or have access to any content you download.

## Features

- A download button injected under the player on YouTube watch pages,
  surviving YouTube's single-page-app navigation.
- A native desktop companion app with a system tray icon and a download
  queue/progress view.
- Every download prompts you to choose a destination folder — nothing is
  ever auto-saved to a default location.
- Cross-browser: one extension codebase for Chromium-based browsers and
  Firefox 109+.
- Interface available in English, Spanish, Portuguese, and French.
- Built on `yt-dlp`, which supports YouTube and ~1800 other sites — other
  sites work best-effort, opt-in, once you grant the extension permission
  for them.

## How it works

```
YouTube page → content script (button) → background worker
   → native messaging → desktop app (native host) → yt-dlp → your disk
```

See `specs/` for the full behavior contract, including the exact
native-messaging protocol and the security model
(`specs/03-security-spec.md`).

## Requirements

- **Browser**: Chrome/Edge/Brave (recent) or Firefox 109+.
- **Desktop app**: the packaged Windows `.exe` (no Python needed), or
  Python 3.11+ if running from source.

## Installation

### 1. Desktop companion app

Download the latest `ytdlx-backend-vX.Y.Z-windows.exe` from the
[Releases](../../releases) page and run it once — this registers the native
messaging host for Chrome, Edge, and Firefox automatically and opens the
tray app.

Running from source instead:

```sh
cd backend
pip install -r requirements.txt
python ytdlx_backend/main.py
```

### 2. Browser extension

Store publishing (Chrome Web Store, Firefox Add-ons, Microsoft Edge
Add-ons) is in progress — see `specs/06-store-publishing-spec.md` for
status. Until each listing is live, load it unpacked/temporarily:

- **Chrome/Edge/Brave**: go to `chrome://extensions`, enable Developer
  Mode, click "Load unpacked", select the `extension/` folder.
- **Firefox**: go to `about:debugging#/runtime/this-firefox`, click
  "Load Temporary Add-on", select `extension/manifest.json`. Note: a
  temporary add-on is removed when Firefox restarts — normal for
  unsigned, unpublished extensions.

## Usage

Open a YouTube video, click the **Download** button that appears below the
player, choose a destination folder in the dialog that opens, and watch
progress in the desktop app's tray/queue view.

## Building from source

### Extension

No build step required for development (plain JS/HTML/CSS). To produce a
release-style zip:

```sh
npx web-ext build --source-dir=extension --artifacts-dir=build
```

### Desktop app → Windows .exe

```sh
cd backend
pip install -r requirements.txt pyinstaller
pyinstaller pyinstaller.spec --distpath ytdlx_backend --workpath build
```

Produces a single windowed (no console), icon-embedded `ytdlx_backend.exe`
in `backend/ytdlx_backend/` — the same folder as `main.py`, using the
`.ico` already in that folder. See `specs/05-release-versioning-spec.md`
for how this is automated on every push to `main`.

## Versioning

Semantic versioning (`vMAJOR.MINOR.PATCH`), kept in sync across `VERSION`,
`extension/manifest.json`, `backend/ytdlx_backend/__version__.py`, and this
README's badge. Full policy: `specs/05-release-versioning-spec.md`.

## Project structure

```
extension/    Browser extension (Manifest V3, Chrome + Firefox)
backend/      Python native-messaging host + tray/queue desktop app
specs/        Spec-driven development: the behavior contract code follows
.claude/      Project-specific Claude Code agents and skills
.github/      CI, CodeQL, dependency updates, release automation
```

## Contributing

See `CONTRIBUTING.md`. Development follows spec-driven development: a
behavior change starts as an edit to the relevant file in `specs/` (see
`specs/templates/change-proposal-template.md`) before the corresponding
code change.

## Security

See `specs/03-security-spec.md` for the threat model and mitigations
(native-messaging origin validation, subprocess argument handling,
save-path sanitization). Dependencies are scanned via `pip-audit` and
CodeQL on every push — see `.github/workflows/`.

## Support this project

If this tool is useful to you, you can
[buy me a beer](https://www.paypal.com/donate/?hosted_button_id=ZABFRXC2P3JQN).

## License

Apache License 2.0 — see [LICENSE](LICENSE).
