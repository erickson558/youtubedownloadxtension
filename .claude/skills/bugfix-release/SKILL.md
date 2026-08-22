---
name: bugfix-release
description: Analyze, fix, validate, version-bump, commit, and push a bug-fix pass on this project without breaking existing functionality. Trigger phrases- "corrige errores", "encuentra y arregla bugs", "estabiliza el proyecto", "prepara un patch release".
---

# Bugfix + Release

A structured debugging-and-release runbook for this specific project. The
rule that matters most: **analyze before changing anything**, and never
remove or alter existing behavior a fix doesn't need to touch — this
project already works end-to-end (extension → native host → yt-dlp →
disk), and a "fix" that breaks that chain is worse than the bug it solved.

## Phase 1 — Analysis (mandatory, do this before editing code)

Look for, in order of how likely they are to matter in this codebase:

1. **Correctness bugs in the security-sensitive paths** — re-read
   `specs/03-security-spec.md`'s five non-negotiable rules and grep for
   violations: `shell=True`, wildcard `allowed_origins`/`allowed_extensions`,
   an unvalidated filesystem write, a length check happening after (not
   before) a read.
2. **Packaging/runtime mismatches between dev mode and the frozen `.exe`**
   — anything that assumes `sys.executable` behaves like a real
   interpreter (it doesn't once frozen — see `ytdlp_runner.py`'s
   `INTERNAL_YTDLP_WORKER_ARG` pattern for the shape of this class of bug),
   anything that assumes a console/stdin exists (a `--windowed` build has
   none), anything that assumes an env var Windows doesn't set by default
   (`LANG`/`LC_ALL`/`LC_MESSAGES` — see `i18n/translator.py`).
3. **Concurrency issues** — Tkinter must only be touched from the main
   thread (worker threads calling into `gui/` must bridge through
   `root.after()`); anything writing to the native-messaging stdout stream
   from more than one thread must go through `protocol.py`'s lock.
4. **CI/CD script-injection or shell-quoting bugs** in `.github/workflows/*.yml`
   — never interpolate `${{ github.event.* }}` or other externally-influenced
   text directly into a `run:` block; pass it through `env:` first.
5. **Dependency vulnerabilities** — run `pip-audit -r backend/requirements.txt`
   locally; check `gh pr list` for open Dependabot PRs that describe a fix
   already proposed and tested.
6. **Everything else**: exception handling that's too broad or too narrow,
   obvious logic errors, dead code.

For each finding, write down: what it is, the root cause (not just the
symptom), the impact, and the risk of fixing it. Do not fix anything you
can't explain the root cause of.

## Phase 2 — Fix

- Fix only what Phase 1 identified. No opportunistic refactors, no
  "while I'm here" rewrites, no removed features.
- Prefer the smallest change that addresses the root cause.
- If a fix changes documented behavior (a spec file describes it), update
  the spec in the same change — see `specs/templates/change-proposal-template.md`.
- Add or update a comment explaining *why*, when the fix is non-obvious —
  see the `thorough-code-comments` skill's standard.

## Phase 3 — Validate

```sh
cd backend
pip install -r requirements-dev.txt
ruff check ytdlx_backend tests
pytest tests -q
pip-audit -r requirements.txt
```

Also, for anything touching the extension: load it unpacked in both
`chrome://extensions` and Firefox's `about:debugging#/runtime/this-firefox`
and confirm the download button still appears and still triggers a
message. Add a regression test for the bug you just fixed wherever
feasible — an untested fix is not a validated fix.

## Phase 4 — Version

Per `specs/05-release-versioning-spec.md`: a bug fix is normally a
**patch**. It's **minor** if the fix also adds new user-visible behavior
(rare for a pure bugfix pass), and **major** only if it changes the
native-messaging protocol or extension permissions incompatibly.

If pushed to `main`, `.github/workflows/release.yml` bumps and syncs the
version automatically (`VERSION`, `extension/manifest.json`,
`backend/ytdlx_backend/__version__.py`, the README badge) — you normally
don't hand-edit these. To force a minor/major bump instead of the default
patch, include `[minor]` or `[major]` in the commit message (see
`release-automation` skill).

## Phase 5 — Commit

Conventional Commits, describing the root cause fixed, not just the
symptom:

```
fix: <what was actually wrong, briefly>

<why it happened, what the fix does, how it was validated>
```

Add a `CHANGELOG.md` entry under `## [Unreleased]` (Keep a Changelog
format) before committing, so the next release has a ready-made summary.

## Phase 6 — Push

```sh
git add <only the files the fix actually touched>
git status                 # re-check before committing — no stray build output, no secrets
git commit -m "..."
git push origin main
```

Pushing to `main` triggers CI and the release pipeline automatically; no
manual tag/release step is needed unless you're overriding the automatic
patch bump (see `release-automation` skill for that case). After pushing,
check `gh run list --limit 5` and read any failure with
`gh run view <id> --log-failed` rather than assuming it passed.
