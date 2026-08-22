# Change Proposal: <short title>

> Copy this file, fill it in, and land the spec-file edits it describes
> *before* opening the implementation PR. This is what "spec-driven" means
> in this repo: the spec is the plan of record, code follows it.

## Problem

What's missing, broken, or newly needed? Who hits this and how?

## Proposed spec change

Which spec file(s) under `specs/` change, and what do the new/edited
sections say? Paste the actual diff/new prose here, not just a summary.

## Affected specs

- [ ] `specs/00-project-spec.md`
- [ ] `specs/01-extension-spec.md`
- [ ] `specs/02-native-host-spec.md`
- [ ] `specs/03-security-spec.md`
- [ ] `specs/04-i18n-spec.md`
- [ ] `specs/05-release-versioning-spec.md`

## Implementation checklist

- [ ] Spec file(s) above updated and merged/committed first
- [ ] Code changes match the updated spec (no undocumented behavior)
- [ ] Tests added/updated for the new behavior
- [ ] `security-audit` skill re-run if the change touches `native_host/`,
      `downloader/`, or any allow-list
- [ ] Version bump category decided per `specs/05-release-versioning-spec.md`
