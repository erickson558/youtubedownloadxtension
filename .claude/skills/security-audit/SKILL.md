---
name: security-audit
description: Run a structured security pass over the native-messaging origin validation, yt-dlp subprocess invocation, and downloaded-file path handling in backend/, plus CI script-injection surfaces. Trigger phrases- "revision de seguridad", "audita el native host", "chequea inyeccion de comandos", "security review".
---

# Security Audit

This skill operationalizes `specs/03-security-spec.md` as a repeatable check
list. It produces **findings**, it does not silently patch them — use the
`security-reviewer` agent (read-only tools) to run the actual review so
fixes stay a separate, reviewable step.

## Scope: the named risk surfaces

Surfaces 1–3 are in `backend/`, which is what the extension's popup talks
to on every download (see `specs/00-project-spec.md`, `specs/01-extension-spec.md`
"Download trigger") — audit them as live, reachable code, not dormant
infrastructure.

1. **Native-messaging origin validation**
   (`backend/ytdlx_backend/native_host/manifest_installer.py`,
   `security/origin_validator.py`):
   - Confirm `allowed_origins` (Chrome) uses `chrome-extension://<id>/` URLs
     with the trailing slash and no wildcard.
   - Confirm `allowed_extensions` (Firefox) uses the bare Gecko add-on id
     string and no wildcard.
   - Confirm the two keys are never swapped between browsers.
   - Confirm the host cross-checks the origin/extension-id argv value the
     browser passes at launch against a compiled-in allow-list, as defense
     in depth beyond the OS-level manifest.

2. **Subprocess invocation of yt-dlp**
   (`backend/ytdlx_backend/downloader/ytdlp_runner.py`):
   - Grep for `shell=True` or any string concatenation that builds a command
     line — must find none.
   - Confirm the argument list always includes a literal `"--"` immediately
     before the URL.
   - Confirm there's a timeout/kill policy for a hung subprocess.

3. **Downloaded-file path handling**
   (`backend/ytdlx_backend/security/path_sanitizer.py`,
   `gui/dialogs.py`, `downloader/queue_manager.py`):
   - Confirm every write path is resolved to an absolute real path and
     checked to still be inside the user-chosen root before any file
     operation.
   - Confirm `..` path segments are rejected outright, not just resolved
     away.
   - Confirm UNC/network paths are rejected unless explicitly opted in.

4. **CI/CD script injection** (`.github/workflows/*.yml`):
   - Grep every `run:` block for a raw `${{ github.event.` or
     `${{ github.head_ref` interpolation — any externally-influenced value
     must be passed through `env:` and referenced as a shell variable
     instead. This is a real, previously-hit bug in this project (see
     `specs/03-security-spec.md` threat #8) — the first live release run
     broke because a commit message containing backticks got re-parsed as
     shell syntax.

5. **`eval`/`new Function`, anywhere in the extension**
   (`extension/src/`):
   - Grep the whole `extension/src/` tree — confirm there are zero call
     sites at all. A prior design (client-side YouTube extraction, removed
     — see `specs/01-extension-spec.md`, "History") needed one and was
     removed along with the feature; see `specs/03-security-spec.md` rule 7.

## Process

1. Read `specs/03-security-spec.md` in full — it is the checklist, this
   skill just runs it against the current code state instead of a point in
   time.
2. For each surface above, read the named files and grep for the specific
   patterns called out.
3. Additionally trace the adversarial-input scenarios from
   `.claude/agents/security-reviewer.md` (URL starting with `-`, containing
   `../`, oversized, containing control characters) through the actual code
   path and note where each is (or isn't) handled.
4. Check `.github/workflows/ci.yml` still runs `pip-audit` and
   `.github/workflows/codeql.yml` still covers both `javascript-typescript`
   and `python`.
5. Report findings as a list — file, line, issue, severity, why it
   matters — most severe first. If nothing is found, say so explicitly.
6. Only apply fixes after the findings are reviewed (by the user or in a
   follow-up step), unless explicitly asked to fix inline.
