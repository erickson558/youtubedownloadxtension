---
name: store-publish
description: Step-by-step runbook to get this extension into a real, installable state on Firefox (AMO), Chrome Web Store, and Microsoft Edge Add-ons, and to wire the already-prepared GitHub Actions jobs that auto-publish new versions once account setup is done. Trigger phrases- "publica la extension", "sube a la chrome web store", "firma el xpi", "publica en firefox add-ons".
---

# Store Publish

Getting a *real* installable file (not "load unpacked"/"temporary add-on")
requires an account + one-time setup on each store — those steps are
identity/payment actions only the project owner can do, and are listed
below in the order that unblocks automation fastest (Firefox first: free,
fully API-driven, no waiting on a paid review). See
`specs/06-store-publishing-spec.md` for why this is split into manual vs
automated pieces, and the `release-devops` agent for the workflow jobs
themselves.

## 1. Firefox — Mozilla Add-ons (AMO) — do this first, it's free and fastest

1. Create a free account at <https://addons.mozilla.org/> (a Firefox
   Account — can be created with any email, no separate password needed if
   you already have one).
2. Generate API credentials at
   <https://addons.mozilla.org/en-US/developers/addon/api/key/> — this
   gives a **JWT issuer** (looks like `user:1234567:589`) and a **JWT
   secret** (a long hex string). Copy both immediately; the secret is only
   shown once.
3. Add them as GitHub Actions secrets on this repo:
   ```sh
   gh secret set AMO_JWT_ISSUER --repo erickson558/youtubedownloadxtension
   gh secret set AMO_JWT_SECRET --repo erickson558/youtubedownloadxtension
   ```
   (each command prompts for the value — paste it there, not in chat).
4. That's it — the next push to `main` runs `publish-firefox-amo`
   automatically, which signs a real `.xpi` via `web-ext sign` and attaches
   it to the GitHub Release. The very first submission creates the AMO
   listing itself (initially as a bare/minimal listing); go to
   <https://addons.mozilla.org/developers/addons> afterwards to fill in the
   full store page (screenshots, longer description, category) — this
   part has no API, it's a one-time manual polish step.

## 2. Chrome Web Store — costs $5 once, needs manual first upload

1. Create/use a Google account, then register as a developer at
   <https://chrome.google.com/webstore/devconsole> — pay the one-time **$5
   USD** registration fee (only required once per Google account, covers
   all future extensions).
2. Click "New Item", upload `ytdlx-chrome-vX.Y.Z.zip` from the latest
   GitHub Release, fill in the store listing (description, screenshots,
   category, the "Privacy practices" tab — be explicit that the extension
   only talks to a local native-messaging host, never a remote server),
   and submit for review.
3. Once approved, get automation credentials so future versions upload
   without repeating this dashboard flow:
   - In [Google Cloud Console](https://console.cloud.google.com/), create
     a project (or reuse one), enable the "Chrome Web Store API".
   - Create an OAuth 2.0 Client ID (type: Desktop app).
   - Use the [chrome-webstore-upload-cli docs](https://github.com/fregante/chrome-webstore-upload-cli#usage)
     flow to exchange it for a refresh token (one-time interactive step on
     your machine, not in CI).
   - Find your extension's ID in the Developer Dashboard URL after the
     first listing exists.
4. Add the four secrets:
   ```sh
   gh secret set CHROME_EXTENSION_ID --repo erickson558/youtubedownloadxtension
   gh secret set CHROME_CLIENT_ID --repo erickson558/youtubedownloadxtension
   gh secret set CHROME_CLIENT_SECRET --repo erickson558/youtubedownloadxtension
   gh secret set CHROME_REFRESH_TOKEN --repo erickson558/youtubedownloadxtension
   ```
5. From then on, `publish-chrome-webstore` uploads and publishes every new
   version automatically (Chrome re-reviews each update, usually faster
   than the first review).

## 3. Microsoft Edge Add-ons — free, needs manual first upload

1. Register (free) at
   <https://partner.microsoft.com/en-us/dashboard/microsoftedge>.
2. Create a new extension listing, upload the same
   `ytdlx-chrome-vX.Y.Z.zip` (Edge accepts the Chromium package as-is),
   fill in the listing, submit for review.
3. In Partner Center, under account settings, create an Azure AD
   application to get `Client ID`, `Client Secret`, and the tenant's
   `Access Token URL` for the Submission API; find the `Product ID` on the
   extension's overview page.
4. Add the four secrets:
   ```sh
   gh secret set EDGE_PRODUCT_ID --repo erickson558/youtubedownloadxtension
   gh secret set EDGE_CLIENT_ID --repo erickson558/youtubedownloadxtension
   gh secret set EDGE_CLIENT_SECRET --repo erickson558/youtubedownloadxtension
   gh secret set EDGE_ACCESS_TOKEN_URL --repo erickson558/youtubedownloadxtension
   ```
5. `publish-edge-addons` then auto-submits every new version.

## Before relying on any of this for a real release

The Chrome and Edge publish steps use community-maintained GitHub Actions
(`mnao305/chrome-extension-upload-action`, `wdzeng/edge-addon`) — re-check
each action's README for its current input names right before the first
real run; these can change between major versions and aren't covered by
this project's own tests.

## Verifying a store job actually worked

```sh
gh run list --repo erickson558/youtubedownloadxtension --workflow Release.yml --limit 1
gh run view <run-id> --repo erickson558/youtubedownloadxtension --log
```

Look for the `publish-firefox-amo` / `publish-chrome-webstore` /
`publish-edge-addons` job specifically — a "skipped" conclusion there means
its secrets aren't set yet, not that something is broken.
