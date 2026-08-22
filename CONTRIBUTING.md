# Contributing

## Spec-driven development

This repo does spec-first development: `specs/*.md` is the contract the
code implements, not after-the-fact documentation. Before implementing a
behavior change, copy `specs/templates/change-proposal-template.md`, fill
it in, and land the spec edit it describes — then implement to match.

## Commit convention

[Conventional Commits](https://www.conventionalcommits.org/):

```
<type>: <short summary>

[optional body]
```

Types: `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `ci`.

The release workflow (`.github/workflows/release.yml`) looks for an
explicit `[major]` or `[minor]` marker in the commit message to decide the
version bump (default: patch) — see `specs/05-release-versioning-spec.md`.

## Project layout

- `extension/` — browser extension, see `specs/01-extension-spec.md`.
- `backend/` — Python native-messaging host + desktop app, see
  `specs/02-native-host-spec.md`.
- `.claude/agents/` and `.claude/skills/` — project-specific Claude Code
  automation; useful context for anyone (human or agent) maintaining this
  repo.

## Running tests

```sh
cd backend
pip install -r requirements-dev.txt
pytest tests -q
ruff check ytdlx_backend tests
```

## Security-sensitive changes

Any change touching `backend/ytdlx_backend/native_host/`,
`backend/ytdlx_backend/downloader/`, or an `allowed_origins`/
`allowed_extensions` list should be reviewed against
`specs/03-security-spec.md` before merging — see the `security-audit`
Claude Code skill for a structured checklist.
