# 05 — Release & Versioning Spec

Depends on [[00-project-spec]]. Automated by `.github/workflows/release.yml`;
manual runbook counterpart is the `release-automation` skill.

## Versioning scheme

Semantic versioning, `vMAJOR.MINOR.PATCH`, applied to the project as a whole
(the extension and the desktop app are versioned together, not
independently, since they must be protocol-compatible with each other):

- **MAJOR** — a breaking change to the native-messaging protocol (message
  types/fields in [[02-native-host-spec]] change incompatibly), a breaking
  change to the extension's manifest permissions that requires re-consent, or
  removal of a previously supported site/feature.
- **MINOR** — a new capability that stays backward compatible: a new
  supported site, a new locale, the tray/queue UI, a new optional permission.
- **PATCH** — bug fixes, dependency bumps (including routine `yt-dlp`
  version bumps to track site changes), documentation, CI/build-only changes.

## Single source of truth

`/VERSION` (a bare `X.Y.Z` string) is the source of truth. The following
files must always contain the same value and are kept in sync by the
`determine-version` CI job (or manually, per the `release-automation` skill,
for an out-of-band release):

- `/VERSION`
- `extension/manifest.json` → `.version`
- `backend/ytdlx_backend/__version__.py` → `__version__`
- `README.md` version badge

## Release artifacts (attached to each GitHub Release)

| Artifact | Built by | Contents |
|---|---|---|
| `ytdlx-chrome-vX.Y.Z.zip` | `web-ext build` against `extension/` | Chromium-loadable unpacked extension archive |
| `ytdlx-firefox-vX.Y.Z.zip` | `web-ext build` against `extension/` | Firefox-loadable archive (also the artifact submitted to AMO for signing when self-distribution requires a signed `.xpi` — signing itself is a manual/future step, not automated here) |
| `ytdlx-backend-vX.Y.Z-windows.exe` | `pyinstaller backend/pyinstaller.spec` on `windows-latest` | Windowed, console-free native host + tray app |

## Release trigger

A push to `main` triggers `.github/workflows/release.yml`, unless the
triggering commit message contains `[skip release]` (used by the
version-bump commit itself, to avoid an infinite loop back into the same
workflow).

## Commit convention

[Conventional Commits](https://www.conventionalcommits.org/) (`feat:`,
`fix:`, `chore:`, `docs:`, `refactor:`, `test:`, `ci:`) — documented in
`CONTRIBUTING.md`. The initial release automation uses an explicit bump
signal (label or commit-message marker) rather than auto-parsing commit
history, to avoid unpredictable version jumps while the convention is still
being adopted; switching to full Conventional-Commits-driven bumping is a
tracked fast-follow, not a day-one requirement.

## Related specs

[[00-project-spec]] · [[02-native-host-spec]]
