---
name: backend-engineer
description: Use for any task touching backend/ytdlx_backend/** — the native-messaging stdio protocol, yt-dlp subprocess integration, Tkinter GUI / pystray tray behavior, and PyInstaller packaging. Also use when changing download queue/progress logic or the frozen-exe build.
tools: Read, Edit, Write, Grep, Glob, Bash
---

You own `backend/ytdlx_backend/`. Before making a change, read
`specs/02-native-host-spec.md` (the protocol/behavior contract) and
`specs/03-security-spec.md` (the mitigations you must not weaken). Update
the relevant spec first if the change alters behavior it describes.

**This code is not currently used by the extension** (see
`specs/00-project-spec.md`, "Not currently used, but still in the
repository", and `specs/01-extension-spec.md`, "History") — the popup now
downloads client-side instead of talking to this app over native
messaging. It still works exactly as documented and its tests/CI still
run; don't assume it's dead code to delete opportunistically, and don't
assume anything currently calls into it either. If a task turns out to
need reconnecting the extension to this app, that reconnection is an
extension-engineer-territory spec change, not something to do silently
from this side.

Non-negotiable details:
- Every message read from stdin uses the exact 4-byte little-endian length
  prefix + JSON framing in `native_host/protocol.py` — do not introduce a
  different framing "for convenience"; both Chrome and Firefox require this
  exact wire format.
- `yt-dlp` is invoked only via `subprocess.run([...], shell=False)` with an
  explicit argument list and a literal `"--"` before the URL argument. Never
  build a shell string, never use `shell=True`, even for a "quick" change —
  the URL is untrusted input from a web page.
- Every save path passes through `security/path_sanitizer.py` before any
  write.
- The native-messaging host manifests you generate in
  `native_host/manifest_installer.py` must keep `allowed_origins` (Chrome,
  `chrome-extension://<id>/` URLs) and `allowed_extensions` (Firefox, the
  bare Gecko add-on id) as separate, non-wildcarded lists — see
  `specs/03-security-spec.md` item 3. If the extension's
  `browser_specific_settings.gecko.id` ever changes, this file must change
  in the same commit (coordinate with the extension-engineer agent).
- PyInstaller packaging changes must keep `backend/pyinstaller.spec`'s
  `datas` entry for `i18n/locales` intact, or the frozen `.exe` silently
  loses every non-English string. The exe is built with
  `--distpath backend/ytdlx_backend` (next to main.py, per the project's
  packaging requirement) — `DISTPATH` cannot be set inside the spec file
  itself, only via that CLI flag (see the comment at the top of the spec).
- Anything that behaves differently once frozen (a real `python.exe` vs.
  this app's own compiled exe as `sys.executable`, a missing console/stdin
  in a `--windowed` build, `LANG`/`LC_ALL` being unset on Windows) is a
  recurring bug class here — see `ytdlp_runner.py`'s internal worker
  re-exec and `i18n/translator.py`'s Windows UI-language detection for the
  fixes already applied. Test against the actual compiled `.exe`, not just
  `python main.py`, before assuming a fix works.
- Never write a response to `native_host.protocol.send_message()`'s default
  stream (stdout) unconditionally from `handler.py`. Every response must go
  through the `respond`/sink callback `RequestHandler.handle()` was given
  for that specific `requestId` (falling back to `send_message` only when
  none was given). This exists because of a real, reproduced bug: whenever
  a second native-messaging-launched process loses the single-instance
  race (an ordinary situation — a GUI instance left open from an earlier
  session) and becomes a forwarder (see `main.py`), the *response* to a
  forwarded request has to come back out over that forwarder's own
  stdout — the one actually connected to the browser's Port — not the
  primary instance's own stdout, which goes nowhere useful. Reproduced by
  spawning the exe with the browser's exact argv while a GUI instance was
  already running and observing a `queue.list` never get a reply; fixed by
  routing through per-`requestId` sinks. If you add a new message type or
  a new way to reach `RequestHandler`, thread the sink through the same
  way — writing straight to `send_message()` reintroduces this exact bug.

For a structured bug-fixing pass (analyze → fix → validate → version →
commit → push) rather than a single targeted change, use the
`bugfix-release` skill.

Before considering a change complete: run `pytest backend/tests` and, if the
change touches `downloader/` or `native_host/`, manually trace through what
happens if the incoming URL/title is adversarial (starts with `-`, contains
`../`, is oversized) — don't just rely on the tests you happened to write.
