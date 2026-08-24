# 06 — Store Publishing Spec

Depends on [[00-project-spec]], [[01-extension-spec]], [[05-release-versioning-spec]].
Implemented by the `publish-firefox-amo`, `publish-chrome-webstore`, and
`publish-edge-addons` jobs in `.github/workflows/release.yml`; the manual
account-setup steps are documented in the `store-publish` skill.

## Why this is split into "automatable" vs "manual, one-time"

Getting an extension into a real, publicly installable state (a Chrome/Edge
Web Store listing, or a Mozilla-signed `.xpi`) requires, for each store,
account creation, agreeing to a developer agreement, and — for Chrome — a
one-time $5 registration fee. These are identity/payment actions tied to
the maintainer personally; nothing in this repo or its automation can
perform them. Everything *after* that one-time setup — packaging,
signing, uploading a new version on every release — is automated here.

## Per-store status and requirements

**Decision (2026-08-24):** the project owner already has a Mozilla account
(used for Firefox Sync — Mozilla accounts are shared between Sync and AMO,
no separate signup needed) and does not want to pay the Chrome Web Store's
one-time $5 registration fee. Active near-term targets are **Firefox
(AMO)** and **Microsoft Edge Add-ons** (both free); **Chrome Web Store
publishing stays implemented but on hold** — `publish-chrome-webstore`
keeps self-skipping indefinitely until/unless that decision changes, at no
cost to the rest of the pipeline. Chrome/Brave/Vivaldi users can still
install the extension via "Load unpacked" in developer mode in the
meantime (see README), or — since Edge accepts the same Chromium
package — via the Edge Add-ons listing once it exists, even in another
Chromium browser that supports cross-store installs.

| Store | Cost | Account needed | First submission | Subsequent updates |
|---|---|---|---|---|
| Firefox (AMO) | Free | Mozilla account — **the existing Firefox Sync account works, log into addons.mozilla.org with it** — + generated API key/secret | Can be done via `web-ext sign` (API) directly, including the first "unlisted" or "listed" submission — no web UI step is strictly required, though filling in full listing metadata (screenshots, category, longer description) is easier the first time via the AMO web dashboard | `publish-firefox-amo` job, automatic on every release once `AMO_JWT_ISSUER`/`AMO_JWT_SECRET` secrets exist |
| Microsoft Edge Add-ons | Free | Microsoft account + Partner Center registration | Manual: upload the zip once via Partner Center, fill in the store listing | `publish-edge-addons` job, automatic on every release once `EDGE_PRODUCT_ID`/`EDGE_CLIENT_ID`/`EDGE_CLIENT_SECRET`/`EDGE_ACCESS_TOKEN_URL` secrets exist |
| Chrome Web Store | $5 one-time — **on hold, not pursued for now** | Google account + Chrome Web Store Developer Dashboard registration | Manual: upload the zip once via the dashboard, fill in the store listing (description, screenshots, privacy practices, category), submit for review | `publish-chrome-webstore` job — implemented and ready, stays dormant (self-skips) until this is revisited |

## Design decisions

- **Every publish job is best-effort and self-skipping.** Each job's first
  step checks whether its required secrets are set and skips the rest of
  the job if not — pushing to `main` before any store account exists must
  keep working exactly as it does today (extension zips + Windows `.exe`
  attached to a GitHub Release), never fail because a store isn't
  configured yet.
- **Chrome and Edge accept the same package.** Both are Chromium-based and
  read the same Manifest V3 format this project already produces via
  `web-ext build`; no separate "Edge build" step is needed, only a
  separate upload/publish step with Edge's own credentials.
- **Firefox needs its own signed artifact.** `web-ext sign` produces a
  Mozilla-signed `.xpi` distinct from the plain zip — the signed `.xpi` is
  attached to the GitHub Release in addition to the existing
  `ytdlx-firefox-vX.Y.Z.zip`, so the zip stays available for anyone who
  wants to inspect/load it unpacked, while the `.xpi` is what a normal
  Firefox installation actually accepts.
- **Chrome publishing calls the official Chrome Web Store API directly
  with `curl`, not a third-party GitHub Action.** An earlier version of
  this job used `mnao305/chrome-extension-upload-action`, which turned out
  not to exist (repository not found) — and because GitHub Actions
  resolves every `uses:` reference in a job during "Set up job" *before*
  any step-level `if:` is evaluated, the invalid reference made the whole
  job fail outright instead of being skipped, which in turn blocked
  `publish-release` (see the `always()` guard on that job, added for
  exactly this reason) and silently ate a release. Calling Google's
  documented OAuth-token-refresh + upload + publish endpoints directly
  removes that failure mode entirely.
- **Edge Add-ons still uses a third-party action** (`wdzeng/edge-addon`) —
  it resolved successfully during this project's own CI runs, but was
  never exercised with real secrets yet. Before the first real run,
  re-check its current README for input-name changes, the same way the
  Chrome action reference above was found to be stale.

## Related specs

[[00-project-spec]] · [[01-extension-spec]] · [[05-release-versioning-spec]]
