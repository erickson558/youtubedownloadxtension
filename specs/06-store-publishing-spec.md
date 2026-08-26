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

**Decision (2026-08-25):** Firefox publishing uses AMO's `listed` channel
(not `unlisted`) — the extension is meant to be genuinely public and
searchable on addons.mozilla.org, not just self-distributed as a signed
`.xpi`. `publish-firefox-amo` submits every release on the `listed`
channel via `web-ext sign`; Mozilla reviews each submission (the first one
creates the public listing), which can take anywhere from minutes to a
few days — longer/manual review is more likely here than for a typical
extension because this one requests the `nativeMessaging` permission.
`web-ext sign` blocks on the review outcome, so a slow review shows up as
the `publish-firefox-amo` job simply running longer, not as a failure.
Filling in the full listing page (long description, category, screenshots)
is not covered by the API — do that once via
<https://addons.mozilla.org/developers/addons> after the first submission
creates the bare listing.

**A `listed` submission with no license declared is rejected outright**
("This field, or custom_license, is required for listed versions.") —
found on the first real run of this pipeline. `web-ext sign` doesn't
expose license/category/summary as its own flags; they're supplied via
`--amo-metadata=.github/amo-metadata.json` (deliberately kept outside
`extension/` so it's never bundled into the shipped zip/xpi). That file
declares the Apache-2.0 license (matching `LICENSE`), the
"download-management" AMO category, and a short summary per locale. AMO's
locale codes aren't always the bare ISO code an extension's own
`_locales/` uses — a bare `"es"` summary key was rejected ("The language
code \"es\" is invalid"); AMO wanted the region-qualified `"es-ES"`
instead, while bare `"fr"` was accepted as-is. If another locale is ever
added to `amo-metadata.json`, don't assume the extension's own locale code
is valid there without checking the submission result.

**A `listed` submission being accepted is not the same as it being
signed.** Once license/category/locale metadata was correct, the first
submission was genuinely accepted by AMO and queued for review — but
`nativeMessaging` extensions are more likely to need manual (not just
automated) review, and that review took longer than any reasonable amount
of time to block a CI job on. `web-ext sign` polls for a decision and
exits nonzero with an "Approval: timeout exceeded" message once its own
`--timeout` elapses; `publish-firefox-amo` treats that specific message as
a successful-but-pending outcome (logs the direct AMO review-status link,
attaches no `.xpi` to that release) rather than a job failure, and only
fails on a genuine validation/rejection error. This is also fine
architecturally: once approved, a `listed` add-on's primary distribution
path is users installing it straight from its AMO page, not from a
GitHub Release asset.

| Store | Cost | Account needed | First submission | Subsequent updates |
|---|---|---|---|---|
| Firefox (AMO) | Free | Mozilla account — **the existing Firefox Sync account works, log into addons.mozilla.org with it** — + generated API key/secret | `web-ext sign --channel=listed` submits directly for public review/listing — no web UI step is required to create the listing itself, though the full store page (screenshots, longer description, category) is filled in manually afterward via the AMO dashboard | `publish-firefox-amo` job, automatic on every release once `AMO_JWT_ISSUER`/`AMO_JWT_SECRET` secrets exist |
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
