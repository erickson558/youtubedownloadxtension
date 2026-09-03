# 03 — Security Spec

Depends on [[00-project-spec]], [[01-extension-spec]], [[02-native-host-spec]].
Reviewed by the `security-reviewer` agent and the `security-audit` skill
before every release.

There are two trust boundaries documented here: the one the extension
**currently uses** ("Current: direct download, no backend", below), and
the native-messaging one `backend/` implements, which the extension does
not currently call into (see [[00-project-spec]], "Not currently used, but
still in the repository"). Both stay documented since `backend/` still
works and could be wired back up.

## Current: direct download, no backend

```
youtube.com's own page HTML + player JS (fetched fresh by the content
script, same-origin -- not attacker-controlled: it is YouTube's own
first-party response, over HTTPS)
        |  regex-extracted operation sequences / function bodies
        v
youtube-extract.js (content script, isolated world -- has its own
        |  global object, separate from the page's; can reach chrome.*
        |  messaging APIs but nothing more privileged than that)
        |  new Function(...) -- evaluates a small, regex-extracted
        |  fragment of YouTube's own player code (flagged DANGEROUS_EVAL
        |  by web-ext lint; safe only because youtube.com's own CSP
        |  allows 'unsafe-eval', verified directly -- see
        |  specs/01-extension-spec.md, "Direct download")
        v
popup.js -- chrome.tabs.sendMessage / chrome.runtime.onMessage
        |  (same-extension only)
        v
chrome.downloads.download({ url, filename, saveAs: true })
        |  the browser's own download manager fetches the URL and always
        |  prompts for a save location -- this project's code never
        |  chooses or writes a path itself for this feature
        v
filesystem
```

### Threats and mitigations (current design)

| # | Threat | Mitigation | Where enforced |
|---|---|---|---|
| 1 | The regex-based extraction could mis-match and evaluate more (or less) of the fetched player JS than intended, since the closing-brace pattern used is not brace-depth-aware. | Bounded blast radius even if it happens: the fetched JS is YouTube's own same-origin response (not attacker-controlled), the evaluated code runs in the content script's own isolated-world global (not the page's, and not with any extension privilege beyond messaging), and every extraction step already fails closed (returns `null`/`{available:false}`) on no match, a parse error, or a thrown exception — never partial/best-guess output. | `src/content/youtube-extract.js` |
| 2 | A malicious page could try to make `chrome.tabs.sendMessage`/`chrome.runtime.onMessage` traffic look like it came from the popup, to trigger a download to an attacker-chosen URL. | Only the popup ever sends `{type:"ytdlx.extract"}`, and only the content script's own extraction result is ever passed to `chrome.downloads.download()` — the popup never accepts a URL from page content directly, and `saveAs:true` means the user always sees and confirms a real save dialog before anything is written. | `src/popup/popup.js` |
| 3 | The direct-download feature could be used against a video the user has no right to download, same as any downloader. | Unchanged from the project's original scope: this is a personal-use tool, and the legal/ethical disclaimer in [[00-project-spec]] is shown on first run. | [[00-project-spec]] |
| 4 | `youtube-adblock.js` programmatically sets `video.currentTime`/clicks buttons — could this be abused to manipulate playback in a way that harms the user (e.g. skipping content that wasn't actually an ad)? | It only acts while YouTube's own player carries the `ad-showing` class, which is YouTube's own signal, not something this extension infers independently; the same class is what YouTube's own UI uses to show/hide ad-only controls (skip button, "Ad" label). | `src/content/youtube-adblock.js` |

## Legacy: native-messaging trust boundary (backend/, currently unused)

```
active browser tab (any site)
        |  chrome.tabs.query() -- browser-provided tab.url/tab.title,
        |  never DOM content read out of the page itself; no content
        |  script runs in any page at all
        v
popup (extension, invoked by the user clicking the toolbar icon)
        |  chrome.runtime.sendMessage — same-extension only
        v
background service worker (extension)
        |  chrome.runtime.connectNative — OS-mediated, manifest-gated
        v
OS native messaging (Chrome/Firefox validate allowed_origins/allowed_extensions
        |  and the manifest `path` before ever launching the host process)
        v
native host process (Python, our code)
        |  subprocess.run([...], shell=False) — argument list, never a shell string
        v
yt-dlp subprocess
        |  writes only inside the user-chosen folder
        v
filesystem
```

The only input that ever crosses from "untrusted web content" into "our
process" is the page URL/title, passed through two extension-internal
message hops before it ever reaches the native host over stdio.

### Threats and mitigations (legacy design)

| # | Threat | Mitigation | Where enforced |
|---|---|---|---|
| 1 | A malicious/compromised page could try to have the extension relay an arbitrary string as a "URL" to the native host, hoping it's later used unsafely (command injection, path traversal). | `yt-dlp` is always invoked via `subprocess.run([...], shell=False)` with an explicit argument list and a literal `"--"` before the URL. No string concatenation into a shell command anywhere in the codebase. | `downloader/ytdlp_runner.py` |
| 2 | Another extension, or a rogue local process, could try to speak the native-messaging protocol to our host and issue requests. | Chrome/Firefox only ever launch the host for a browser origin/extension id present in the *installed* native-messaging manifest's `allowed_origins`/`allowed_extensions` — this is enforced by the browser itself, not our code, before our process even starts. As defense in depth, the host additionally cross-checks the origin/extension-id argument the browser passes on `argv` against a hardcoded allow-list compiled into the app, and rejects/exits if it doesn't match. | `native_host/manifest_installer.py` (manifest content), `security/origin_validator.py` (argv cross-check) |
| 3 | `allowed_origins` (Chrome) and `allowed_extensions` (Firefox) are two different keys with different value shapes (a `chrome-extension://` URL vs. a bare Gecko add-on id). Using the wrong key/shape on the wrong browser is a classic silent-failure bug — worse, a *wildcard* in either key would defeat the allow-list entirely. | Never use a wildcard in either key. The installer writes browser-specific manifest files with the correct key name and value shape for each browser, generated from a single source of truth (the extension id and the gecko id), so they cannot drift independently. | `native_host/manifest_installer.py` |
| 4 | A crafted filename/title from page metadata, or a chosen save path, could contain path-traversal sequences (`..`) or point outside the user-approved directory (e.g. via a symlink or a UNC path). | Every save path is validated: reject any path containing `..` segments, resolve to an absolute real path and confirm it is still inside the user-chosen root directory, and reject UNC/network paths unless the user explicitly opted in. | `security/path_sanitizer.py` |
| 5 | A vulnerable dependency (`yt-dlp`, a Python package, or a JS dev dependency) ships a known CVE. | Dependencies are pinned; `pip-audit` runs in CI and blocks merges on high-severity findings; Dependabot opens update PRs weekly; CodeQL scans both the JS and Python code on every push to `main` and weekly on a schedule. | `.github/workflows/ci.yml`, `codeql.yml`, `dependabot.yml` |
| 6 | An error message from the host leaks local filesystem layout, environment details, or a full stack trace back to the extension (and thus, indirectly, closer to the page). | `download.error` messages sent over the native-messaging channel are short, user-facing strings from a fixed set of known error categories; full tracebacks are logged only to a local log file, never sent over the wire. | `native_host/handler.py` |
| 7 | A download that hangs forever (network stall, malicious/broken stream) ties up a queue slot indefinitely. | `yt-dlp` subprocess is killed if no progress update is observed for a configured timeout; the queue item is marked failed. | `downloader/ytdlp_runner.py` |
| 8 | A GitHub Actions workflow interpolates externally-influenced text (e.g. `${{ github.event.head_commit.message }}`) directly into a `run:` shell block; a value containing backticks or `$(...)` gets re-parsed as shell syntax instead of treated as data (classic Actions script injection). This is not hypothetical — it broke the project's first live release run. | Any such value is passed through `env:` and referenced as `$VAR` in the script, never interpolated as `${{ ... }}` inside the script body itself. | `.github/workflows/release.yml` |

## Non-negotiable rules (checked by the `security-audit` skill before every release)

1. No `shell=True` anywhere in the Python codebase.
2. No wildcard in `allowed_origins` or `allowed_extensions`.
3. Every path written to disk passes through `path_sanitizer.py`.
4. Every message read from stdin is length-checked against the 1 MiB cap
   before `json.loads` is called on it (defends against a malformed/hostile
   length prefix causing an unbounded read).
5. `pip-audit` and CodeQL must be green before a release is published.
6. No GitHub Actions `run:` step interpolates `${{ github.event.* }}` (or
   any other externally-influenced expression) directly into the script
   body — it must go through `env:` first.
7. `eval`/`new Function` on dynamic content is confined to
   `src/content/youtube-extract.js`, and only ever on text fetched
   same-origin from `youtube.com` itself (the player JS) — never on
   anything read out of the page's rendered DOM or supplied by another
   extension/site. Do not add another `eval`/`new Function` call site
   without updating this rule and the current-design threats table above.

## Related specs

[[00-project-spec]] · [[01-extension-spec]] · [[02-native-host-spec]]
