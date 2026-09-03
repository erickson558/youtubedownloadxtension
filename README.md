# youtubedownloadxtension

![version](https://img.shields.io/badge/version-1.0.1-blue) ![license](https://img.shields.io/badge/license-Apache--2.0-green)

A browser extension (Chrome, Edge, Brave, Firefox) that adds a **Download**
button to its own toolbar icon and tries to save the YouTube video in your
current tab directly to your computer, plus blocks YouTube ads. No separate
app to install.

> **Experimental, YouTube only, works for some videos, not all.** This
> extension used to pair with a local desktop app (`yt-dlp`-based, still in
> `backend/` but not currently used) that reliably handled ~1800 sites in
> full quality. The current design trades that reliability for not
> requiring a separate install: it can only save YouTube's lower-quality
> "progressive" format, and only when it can work out that format's
> access details from YouTube's own player code — which changes without
> notice and, as of this writing, fails far more often than it succeeds.
> See `specs/01-extension-spec.md`, "Direct download", for exactly what
> that means and why it was still built this way, on request, with that
> trade-off understood upfront.

> **Before you use this**: this tool is for downloading content you have
> the right to save for personal, offline use (your own uploads,
> Creative-Commons/public-domain videos, or content whose platform terms
> permit it). Downloading from a platform can violate that platform's Terms
> of Service even when it is technically possible — that is a contract
> matter between you and the platform, separate from copyright law. You are
> solely responsible for how you use this tool. The authors do not host,
> distribute, or have access to any content you download.

## Features

- A **Download** button on the extension's toolbar popup that tries to save
  the current tab's YouTube video directly — no separate app, no button
  injected into the page itself.
- Automatic YouTube ad blocking: known ad/tracking requests are blocked,
  and in-player video ads are skipped or fast-forwarded automatically.
- Every successful download prompts you to choose a destination folder via
  the browser's own download dialog — nothing is ever auto-saved to a
  default location.
- Cross-browser: one extension codebase for Chromium-based browsers and
  Firefox 113+.
- Interface available in English, Spanish, Portuguese, and French.

## How it works

```
Click the toolbar icon → popup asks the YouTube content script to extract
   a direct file URL → chrome.downloads saves it → your disk
```

See `specs/` for the full behavior contract, including exactly what the
direct-download feature can and cannot do
(`specs/01-extension-spec.md`) and the security model
(`specs/03-security-spec.md`).

## Requirements

- **Browser**: Chrome/Edge/Brave (recent) or Firefox 113+.
- Nothing else to install for the current feature set.

## Installation

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

Open a YouTube video, click the extension's toolbar icon, click
**Download**. If it can't work out a direct URL for that video (common
right now — see the warning above), it says so rather than pretending to
succeed; try a different video. Ads are blocked automatically on every
YouTube page, no action needed.

## Building from source

No build step required for development (plain JS/HTML/CSS). To produce a
release-style zip:

```sh
npx web-ext build --source-dir=extension --artifacts-dir=build
```

## Versioning

Semantic versioning (`vMAJOR.MINOR.PATCH`), kept in sync across `VERSION`,
`extension/manifest.json`, `backend/ytdlx_backend/__version__.py`, and this
README's badge. Full policy: `specs/05-release-versioning-spec.md`.

## Project structure

```
extension/    Browser extension (Manifest V3, Chrome + Firefox) -- the active code
backend/      Python native-messaging host + tray/queue desktop app -- not
              currently used by the extension (see specs/00-project-spec.md)
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

See `specs/03-security-spec.md` for the threat model and mitigations.
Note the direct-download feature evaluates code extracted from YouTube's
own player JS (`new Function`, flagged by `web-ext lint` as
`DANGEROUS_EVAL`) — this is deliberate and explained in
`specs/01-extension-spec.md`. Dependencies are scanned via `pip-audit` and
CodeQL on every push — see `.github/workflows/`.

## Support this project

If this tool is useful to you, you can
[buy me a beer](https://www.paypal.com/donate/?hosted_button_id=ZABFRXC2P3JQN).

## License

Apache License 2.0 — see [LICENSE](LICENSE).
