# 03 — Security Spec

Depends on [[00-project-spec]], [[01-extension-spec]], [[02-native-host-spec]].
Reviewed by the `security-reviewer` agent and the `security-audit` skill
before every release.

## Trust boundary

```
untrusted web page (any site with a <video>)
        |  (DOM only, no direct access to the extension's privileges)
        v
content script (extension, isolated world)
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

## Threats and mitigations

| # | Threat | Mitigation | Where enforced |
|---|---|---|---|
| 1 | A malicious/compromised page could try to have the extension relay an arbitrary string as a "URL" to the native host, hoping it's later used unsafely (command injection, path traversal). | `yt-dlp` is always invoked via `subprocess.run([...], shell=False)` with an explicit argument list and a literal `"--"` before the URL. No string concatenation into a shell command anywhere in the codebase. | `downloader/ytdlp_runner.py` |
| 2 | Another extension, or a rogue local process, could try to speak the native-messaging protocol to our host and issue requests. | Chrome/Firefox only ever launch the host for a browser origin/extension id present in the *installed* native-messaging manifest's `allowed_origins`/`allowed_extensions` — this is enforced by the browser itself, not our code, before our process even starts. As defense in depth, the host additionally cross-checks the origin/extension-id argument the browser passes on `argv` against a hardcoded allow-list compiled into the app, and rejects/exits if it doesn't match. | `native_host/manifest_installer.py` (manifest content), `security/origin_validator.py` (argv cross-check) |
| 3 | `allowed_origins` (Chrome) and `allowed_extensions` (Firefox) are two different keys with different value shapes (a `chrome-extension://` URL vs. a bare Gecko add-on id). Using the wrong key/shape on the wrong browser is a classic silent-failure bug — worse, a *wildcard* in either key would defeat the allow-list entirely. | Never use a wildcard in either key. The installer writes browser-specific manifest files with the correct key name and value shape for each browser, generated from a single source of truth (the extension id and the gecko id), so they cannot drift independently. | `native_host/manifest_installer.py` |
| 4 | A crafted filename/title from page metadata, or a chosen save path, could contain path-traversal sequences (`..`) or point outside the user-approved directory (e.g. via a symlink or a UNC path). | Every save path is validated: reject any path containing `..` segments, resolve to an absolute real path and confirm it is still inside the user-chosen root directory, and reject UNC/network paths unless the user explicitly opted in. | `security/path_sanitizer.py` |
| 5 | A vulnerable dependency (`yt-dlp`, a Python package, or a JS dev dependency) ships a known CVE. | Dependencies are pinned; `pip-audit` runs in CI and blocks merges on high-severity findings; Dependabot opens update PRs weekly; CodeQL scans both the JS and Python code on every push to `main` and weekly on a schedule. | `.github/workflows/ci.yml`, `codeql.yml`, `dependabot.yml` |
| 6 | An error message from the host leaks local filesystem layout, environment details, or a full stack trace back to the extension (and thus, indirectly, closer to the page). | `download.error` messages sent over the native-messaging channel are short, user-facing strings from a fixed set of known error categories; full tracebacks are logged only to a local log file, never sent over the wire. | `native_host/handler.py` |
| 7 | A download that hangs forever (network stall, malicious/broken stream) ties up a queue slot indefinitely. | `yt-dlp` subprocess is killed if no progress update is observed for a configured timeout; the queue item is marked failed. | `downloader/ytdlp_runner.py` |

## Non-negotiable rules (checked by the `security-audit` skill before every release)

1. No `shell=True` anywhere in the Python codebase.
2. No wildcard in `allowed_origins` or `allowed_extensions`.
3. Every path written to disk passes through `path_sanitizer.py`.
4. Every message read from stdin is length-checked against the 1 MiB cap
   before `json.loads` is called on it (defends against a malformed/hostile
   length prefix causing an unbounded read).
5. `pip-audit` and CodeQL must be green before a release is published.

## Related specs

[[00-project-spec]] · [[01-extension-spec]] · [[02-native-host-spec]]
