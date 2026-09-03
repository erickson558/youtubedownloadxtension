# 02 — Native Host / Backend Spec

Depends on [[00-project-spec]], [[01-extension-spec]]. Implemented under `backend/`.

## Process model

Single app, `backend/ytdlx_backend/main.py`, with two invocation shapes:

- **GUI mode** (no special args, e.g. user double-clicked the `.exe`): opens
  the Tkinter main window + a `pystray` tray icon. Closing the window hides it
  to the tray; only "Quit" from the tray menu exits the process.
- **Native-messaging mode**: the browser launches the exe itself, per the
  installed native-messaging manifest (see below), and talks to it purely
  over stdin/stdout using the framed JSON protocol. Chrome/Firefox invoke the
  host as `ytdlx_backend.exe <extension-origin-or-id> [windows-parent-handle]`
  with no explicit "native mode" flag — detect this mode by checking
  `not sys.stdin.isatty()`.
- If a GUI instance is already running (single-instance lock via binding a
  fixed local loopback TCP port, `127.0.0.1:51737`, never exposed beyond
  that), a second native-messaging-launched process acts as a forwarder to
  the running instance instead of starting a second competing tray icon.
  It does **not** exit right away: for every message it reads from the
  browser, it opens a dedicated connection to the running instance,
  forwards the message, and relays every response that comes back over
  that connection to its own stdout in turn — since this forwarder process,
  not the running instance, is the one actually connected to the browser's
  Port. A first version of this forwarded the request but never relayed
  the response, so a download started through a forwarded connection
  silently never got anywhere back to the extension — the request really
  had been handled, the reply just went to the wrong process's stdout. See
  `RequestHandler`'s `respond` callback (`native_host/handler.py`), which
  every response is routed through instead of writing straight to stdout,
  for how the running instance knows to send a given request's replies
  back over the right forwarded connection rather than its own stdout.
  The forwarder only exits once the browser disconnects (its stdin closes).

## Auto-close on settle

A **browser-launched** primary instance (`start_hidden=True` — the browser
invoked the exe itself, as opposed to the user double-clicking it) closes
itself automatically once it has nothing left to do: `RequestHandler`'s
`on_settled` callback fires every time a `download.request` reaches a
terminal outcome (complete, error, cancelled, or rejected outright) *and*
no other request is still queued or downloading (`RequestHandler.has_active_downloads()`).
`main.py` schedules the actual close `AUTO_CLOSE_DELAY_MS` (3s) after that
point — long enough for the tray/queue view to show the final status and
for the downloaded file's last writes to flush, short enough not to feel
like the app forgot to close — and re-checks `has_active_downloads()`
right before closing, in case a new request arrived during that delay
(e.g. the user queued a second download right after the first).

An instance the user started themselves (double-clicked the `.exe`,
`start_hidden=False`) never auto-closes this way — it behaves like an
ordinary desktop app until "Quit" from the tray menu, regardless of
whether a download happens to finish while it's open. This exists because
the popup's toolbar-icon click is what launches the app in the common
case (see [[01-extension-spec]]); users don't want to babysit a tray icon
for a one-off download, but someone who deliberately opened the app to
watch its queue should not have it vanish under them.

## Wire protocol (stdio native messaging)

Identical framing on Chrome and Firefox: a 4-byte **little-endian** unsigned
length prefix, followed by that many bytes of UTF-8-encoded JSON. Max
incoming/outgoing message size: 1 MiB (the conservative cross-browser limit;
Firefox has not raised it the way recent Chrome has).

```python
import struct, sys, json

def read_message():
    raw_length = sys.stdin.buffer.read(4)
    if not raw_length:
        return None  # stdin closed -> browser disconnected, exit
    length = struct.unpack("<I", raw_length)[0]
    return json.loads(sys.stdin.buffer.read(length).decode("utf-8"))

def send_message(msg: dict) -> None:
    data = json.dumps(msg).encode("utf-8")
    sys.stdout.buffer.write(struct.pack("<I", len(data)))
    sys.stdout.buffer.write(data)
    sys.stdout.buffer.flush()
```

## Message types

| type | direction | payload |
|---|---|---|
| `download.request` | extension → host | `{ url, pageTitle, requestId }` |
| `download.progress` | host → extension | `{ requestId, percent, speed, eta }` |
| `download.complete` | host → extension | `{ requestId, filePath }` |
| `download.error` | host → extension | `{ requestId, message }` |
| `queue.list` | extension → host | `{}` (request current queue snapshot) |
| `queue.snapshot` | host → extension | `{ items: [...] }` |

## Download flow

1. Host receives `download.request`.
2. Host validates the sender (see [[03-security-spec]]).
3. Host shows a native folder-picker dialog (`tkinter.filedialog.askdirectory`)
   on the GUI thread — **every** download prompts; there is no default/auto
   save location, and no "remember last folder and skip the dialog" mode.
4. If the user cancels, send `download.error` with a `cancelled` reason; do
   not invoke `yt-dlp`.
5. Host runs `yt-dlp` as a subprocess (see below), streams `download.progress`
   messages parsed from `yt-dlp`'s `--newline --progress-template` output.
6. On completion, send `download.complete` with the final file path; on
   failure, `download.error` with a short, non-sensitive message (never leak
   full stack traces or local file-system layout to the extension).

## yt-dlp invocation contract

- Always `subprocess.run([...], shell=False)` with an explicit argument list.
  Never build a shell command string from the URL — the URL originates from
  an untrusted web page reached via the extension.
- Always insert `"--"` immediately before the URL argument, so a URL crafted
  to start with `-` cannot be parsed as a yt-dlp flag.
- Pin the `yt-dlp` version in `backend/requirements.txt`; bump deliberately
  (yt-dlp ships frequent releases to keep up with site changes) rather than
  auto-updating at runtime.
- Use `--newline --progress-template` with a machine-parseable template
  instead of regexing yt-dlp's human-formatted progress bar.
- Apply a timeout/kill policy: a single download that produces no progress
  update for longer than a configured threshold is killed and reported as
  `download.error`.

## Native-messaging host manifests (installed by `manifest_installer.py`)

Two separate files — **not interchangeable**, see [[03-security-spec]] for why
this is a security-relevant detail, not just a compatibility one:

- Chrome/Edge/Brave: `allowed_origins: ["chrome-extension://<EXTENSION_ID>/"]`
- Firefox: `allowed_extensions: ["youtubedownloadxtension@erickson558.github.io"]`

Both share `name: "com.erickson558.ytdlx"` (must match the `hostName` used by
`connectNative()` in the extension) and `type: "stdio"`.

Install locations written by `manifest_installer.py` (idempotent, re-run on
every app start so a moved/updated `.exe` path is always reflected; uses
`HKEY_CURRENT_USER` so no admin elevation is required):

| Browser | Windows registration |
|---|---|
| Chrome | `HKCU\Software\Google\Chrome\NativeMessagingHosts\com.erickson558.ytdlx` → path to manifest JSON |
| Edge | `HKCU\Software\Microsoft\Edge\NativeMessagingHosts\com.erickson558.ytdlx` (registered separately — Edge does not read Chrome's key) |
| Firefox | `HKCU\Software\Mozilla\NativeMessagingHosts\com.erickson558.ytdlx` |

(macOS/Linux use fixed file paths under each browser's native-messaging-hosts
directory instead of the registry; supported by the same installer module
even though only the Windows `.exe` is packaged/released initially.)

## Related specs

[[03-security-spec]] · [[04-i18n-spec]] · [[05-release-versioning-spec]]
