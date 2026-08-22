---
name: thorough-code-comments
description: Add or review comments across this repo's JS extension code and Python backend so a newcomer can understand what each part does and, especially, why the security-sensitive parts are written the way they are. Trigger phrases- "comenta el codigo", "explica que hace cada parte", "agrega comentarios", "documenta esta funcion".
---

# Thorough Code Comments

This repo has two very different audiences: web-extension developers reading
`extension/`, and desktop/Python developers reading `backend/`. Comment for
each audience in the idiom they expect (JSDoc-style blocks for JS,
docstrings for Python), but apply the same underlying standard:

## What to comment

- **Every exported/public function or class**: one short block explaining
  what it does, its parameters, and what it returns — enough that someone
  who has never opened this file understands its contract without reading
  the body.
- **Every non-obvious "why"**: a hidden constraint, a workaround for a
  specific browser/OS quirk, an invariant that would surprise a reader. This
  repo has several of these by design — always comment on:
  - Why `background.js` uses `connectNative` (persistent Port) instead of
    `sendNativeMessage` (needs to stream progress).
  - Why the MV3 service worker re-establishes the native port lazily instead
    of holding a single long-lived reference (worker suspension).
  - Why `allowed_origins` and `allowed_extensions` are separate, non-wildcard
    lists in the two native-messaging manifest files.
  - Why `yt-dlp` is always invoked with `shell=False` and an explicit arg
    list with `--` before the URL.
  - Why every save path goes through `path_sanitizer.py` before a write.
  - Why the Python i18n loader is a flat JSON reader instead of `gettext`.
- **Every place a spec is being implemented**: a one-line reference to which
  `specs/*.md` file and section this code satisfies, so a future reader can
  find the fuller rationale instead of reverse-engineering it from the code.

## What NOT to comment

- Don't restate what well-named code already says (`# increment i` above
  `i += 1`).
- Don't write multi-paragraph docstrings for simple internal helpers — one
  line is enough if the name and signature already carry most of the
  meaning.
- Don't add comments that reference "the current task" or a specific PR/issue
  number — comments should read correctly regardless of when someone opens
  the file.

## How to apply this skill

1. Identify the target file(s) (or scan `extension/src/**` and
   `backend/ytdlx_backend/**` if asked to do a full pass).
2. For each public function/class lacking a doc comment, add one following
   the standard above.
3. For each of the six "why" hotspots listed above, verify a comment exists
   at the exact line where the non-obvious behavior lives (not just
   somewhere in the file) — grep for the relevant keyword
   (`connectNative`, `shell=False`, `allowed_origins`, `path_sanitizer`,
   etc.) to find them.
4. Cross-reference the relevant `specs/*.md` file inline where it clarifies
   intent.
5. Do not change behavior while adding comments — this skill is
   documentation-only. If you notice an actual bug while commenting, report
   it separately rather than silently fixing it inline.
