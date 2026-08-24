---
name: store-publish
description: Step-by-step runbook to get this extension into a real, installable state on Firefox (AMO), Chrome Web Store, and Microsoft Edge Add-ons, and to wire the already-prepared GitHub Actions jobs that auto-publish new versions once account setup is done. Trigger phrases- "publica la extension", "sube a la chrome web store", "firma el xpi", "publica en firefox add-ons".
---

# Store Publish

Getting a *real* installable file (not "load unpacked"/"temporary add-on")
requires an account + one-time setup on each store — those steps are
identity/payment actions only the project owner can do. **Current
decision (specs/06-store-publishing-spec.md): Firefox and Edge are the
active targets — both free; Chrome Web Store is on hold because of its
one-time $5 fee, and stays implemented-but-dormant (`publish-chrome-webstore`
keeps self-skipping) until that decision changes.** See the
`release-devops` agent for the workflow jobs themselves.

## 1. Firefox — Mozilla Add-ons (AMO) — do this first, it's free and fastest

1. **No new account needed if a Firefox Sync account already exists** —
   Mozilla accounts are shared between Firefox Sync and AMO. Just log into
   <https://addons.mozilla.org/> with that same account. (Only create a
   new one at that URL if there isn't an existing Firefox/Mozilla account
   at all.)
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

## 2. Microsoft Edge Add-ons — free, needs manual first upload

1. Register (free) at
   <https://partner.microsoft.com/en-us/dashboard/microsoftedge>.
2. Create a new extension listing, upload `ytdlx-chrome-vX.Y.Z.zip` from
   the latest GitHub Release (Edge accepts the Chromium package as-is,
   same file Chrome would use), fill in the listing, submit for review.
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
5. `publish-edge-addons` then auto-submits every new version. Its step
   uses the community-maintained `wdzeng/edge-addon` action — re-check its
   README for current input names right before this first real run (it
   resolved fine in this project's own CI, but has never run with real
   credentials yet).

## 3. Chrome Web Store — on hold (costs $5 once) — skip unless this changes

Not being pursued right now because of the one-time $5 registration fee.
`publish-chrome-webstore` is fully implemented (calls the official Chrome
Web Store API directly with `curl`, no third-party action involved) and
will activate automatically the moment its four secrets exist — nothing
else needs to change in the pipeline if this is revisited later. To pick
it back up:

1. Create/use a Google account, register as a developer at
   <https://chrome.google.com/webstore/devconsole>, pay the one-time **$5
   USD** fee (covers all future extensions from that account, forever).
2. Click "New Item", upload `ytdlx-chrome-vX.Y.Z.zip` from the latest
   GitHub Release, fill in the store listing (description, screenshots,
   the "Privacy practices" tab — be explicit that the extension only talks
   to a local native-messaging host, never a remote server), submit for
   review.
3. Once approved, get automation credentials: in
   [Google Cloud Console](https://console.cloud.google.com/), enable the
   "Chrome Web Store API", create an OAuth 2.0 Client ID (Desktop app),
   and follow the [chrome-webstore-upload-cli docs](https://github.com/fregante/chrome-webstore-upload-cli#usage)
   to exchange it for a refresh token (one-time, on your own machine, not
   in CI). Find the extension ID in the Developer Dashboard URL.
4. Add the four secrets:
   ```sh
   gh secret set CHROME_EXTENSION_ID --repo erickson558/youtubedownloadxtension
   gh secret set CHROME_CLIENT_ID --repo erickson558/youtubedownloadxtension
   gh secret set CHROME_CLIENT_SECRET --repo erickson558/youtubedownloadxtension
   gh secret set CHROME_REFRESH_TOKEN --repo erickson558/youtubedownloadxtension
   ```

## Verifying a store job actually worked

```sh
gh run list --repo erickson558/youtubedownloadxtension --limit 1
gh run view <run-id> --repo erickson558/youtubedownloadxtension --log
```

Each of `publish-firefox-amo` / `publish-chrome-webstore` /
`publish-edge-addons` shows as a **successful** job even when its secrets
aren't configured — the job itself always completes, it just skips its
inner upload/sign steps (look for the `::notice::` annotation naming which
secret is missing, not a "skipped" job conclusion, to tell "not configured
yet" apart from "something is broken").
