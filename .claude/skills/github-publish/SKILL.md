---
name: github-publish
description: Publish this project to GitHub under the erickson558 account — create the public repo with Apache-2.0 license, push main, open PRs. Trigger phrases- "publica esto en GitHub", "crea el repo", "sube el proyecto", "abre un PR".
---

# GitHub Publish

This project is published under the `erickson558` GitHub account, already
authenticated via `gh` (protocol https; scopes `gist`, `read:org`, `repo`,
`workflow`). Always confirm `gh auth status` shows `erickson558` as the
active account before creating or pushing anything — never assume.

## Repo creation (one-time)

```sh
gh auth status                                    # confirm active account = erickson558
git init -b main                                  # if not already a repo
git add -A
git status                                        # review what's staged before committing — check for stray secrets/build output
git commit -m "feat: initial project scaffold — extension, native host, specs, CI"
gh repo create erickson558/youtubedownloadxtension \
  --public \
  --source=. \
  --remote=origin \
  --description "Browser extension + Python native host to download videos you have the right to save, via yt-dlp." \
  --license apache-2.0 \
  --push
```

Notes:
- `--license apache-2.0` only seeds a `LICENSE` file if one isn't already
  present in the working tree; this repo already commits its own
  hand-authored `LICENSE` (Apache-2.0 text) — do not let `gh repo create`
  overwrite it. If in doubt, create the repo without `--license` and rely on
  the committed `LICENSE` file.
- `--push` pushes the current branch (`main`) and sets the upstream in one
  step. This is a public, visible action — confirm with the user before
  running it if this skill is invoked outside of an explicit "publish now"
  request.
- Repo topics worth setting after creation for discoverability:
  `gh repo edit erickson558/youtubedownloadxtension --add-topic browser-extension --add-topic yt-dlp --add-topic firefox-extension --add-topic chrome-extension --add-topic video-downloader`

## Subsequent pushes

```sh
git status                 # review before staging broadly
git add <specific files>   # avoid `git add -A` blindly on later commits — check for build artifacts, .env, etc.
git commit -m "<type>: <summary>"   # Conventional Commits, see CONTRIBUTING.md
git push origin main
```

## Pull requests (for anyone else contributing, or for reviewing your own
feature branch before merging to main)

```sh
git checkout -b feat/<short-name>
# ... commits ...
git push -u origin feat/<short-name>
gh pr create --title "<type>: <summary>" --body "$(cat <<'EOF'
## Summary
- ...

## Test plan
- [ ] ...
EOF
)"
```

## Safety notes

- Never run `gh repo delete`, `git push --force`, or change repo visibility
  from public to private (or vice versa) without the user explicitly asking
  for exactly that action in that message.
- Before any push, run `git status` and read the diff of anything unusual —
  double-check no `.env`, credentials, or PyInstaller `build/`/`dist/`
  output got staged (see `.gitignore`).
- This account's token has `repo` and `workflow` scope, which is sufficient
  for everything above; it does not have `delete_repo` scope by default —
  if a destructive operation is ever requested, expect it to require a
  fresh `gh auth refresh` and treat that as a deliberate, separately
  confirmed step.
