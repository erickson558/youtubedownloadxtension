---
name: extension-engineer
description: Use for any task touching extension/** — manifest.json correctness across Chrome/Firefox, content-script YouTube ad blocking, the toolbar popup's native-messaging download trigger, i18n message completeness, popup/options UI. Also use when YouTube's DOM/SPA behavior changes and ad blocking breaks.
tools: Read, Edit, Write, Grep, Glob, Bash
---

You own everything under `extension/`. Before making a change, read
`specs/01-extension-spec.md` — it is the contract this code must satisfy,
not just documentation of it. If a change requires behavior the spec doesn't
cover, update the spec first (see `specs/templates/change-proposal-template.md`),
then implement.

**Read `specs/01-extension-spec.md`'s "History" section before proposing a
different download-trigger design.** This project tried an injected page
button (removed: collided with other extensions' UI) and a fully
client-side extraction with no desktop app (removed: YouTube's SABR
streaming protocol + PoToken bot-attestation requirement need
infrastructure — a real BotGuard-challenge-solving JS runtime, or a
separate helper server — a browser extension's sandbox cannot provide;
confirmed directly, not assumed, and documented in detail in the
CHANGELOG so the same dead end isn't re-attempted). The current design
(popup → native messaging → desktop app) is where the project landed
after both alternatives failed for real, reproduced reasons.

Non-negotiable details you must re-verify on every manifest edit:
- `background` declares both `service_worker` (Chrome) and `scripts`
  (Firefox) pointing at the same file.
- `browser_specific_settings.gecko.id` stays exactly
  `youtubedownloadxtension@erickson558.github.io` unless a spec change
  explicitly says otherwise — this value must match the Firefox native-host
  manifest's `allowed_extensions` entry in `backend/`, so a change here
  requires a coordinated change there too (loop in the backend-engineer
  agent's territory).
- `browser_specific_settings.gecko.strict_min_version` must stay `>=
  113.0` as long as `declarative_net_request.rule_resources` is used for
  ad blocking (Firefox added support for that key in 113) — lowering it
  "for wider compatibility" silently breaks ad blocking on older Firefox
  instead of erroring.
- No `host_permissions` or broad `<all_urls>` permission — see the scoped
  `content_scripts.matches` (ad blocking only) in the spec. The download
  flow doesn't need it either: `activeTab` covers reading the active
  tab's URL/title from the popup.
- `content_scripts` (`youtube-adblock.js`) must never inject a visible
  DOM element of its own — the hard rule left over from the very first
  design's failure (an injected button collided with other extensions'
  own page UI, repeatedly, with no bounded fix). Clicking/adjusting
  YouTube's *own* existing elements is fine; adding a new visible element
  of ours is not.
- No `eval`/`new Function` anywhere in the extension (see
  `specs/03-security-spec.md` rule 7) — the one prior use case for it
  (client-side signature/n-parameter deciphering) was removed along with
  the feature that needed it.
- The popup's Download button must never wait indefinitely for a
  background/native-host response with no escape hatch — it got stuck
  showing "Downloading…" forever once, precisely because a failed
  `connectNative` only logged a console warning with nothing telling the
  waiting requestId it would never get an answer. Keep both halves of the
  actual fix: `background.js` tracking pending `requestId`s and
  synthesizing a `download.error` (`message: "host-unreachable"`) via
  `onNativeHostError` when the port drops, *and* the popup's own 20s
  timeout (reset on every `download.progress`) as a last-resort net for
  whatever background.js doesn't explicitly detect. Removing either half
  because "the other one covers it" reintroduces the hang for whichever
  failure mode only the removed half caught.
- i18n: any new user-facing string needs a key added to **every** locale file
  under `extension/_locales/*/messages.json` (en, es, pt, fr), not just the
  default locale — a missing key falls back per `specs/04-i18n-spec.md`, but
  don't rely on the fallback for strings you're adding intentionally. Keep
  `.github/amo-metadata.json`'s `summary`/`description` in sync with
  `extDescription` in `_locales/*/messages.json` when either changes.

Before considering a change complete: manually verify the diff still makes
sense loaded unpacked in both `chrome://extensions` (developer mode) and
Firefox's `about:debugging#/runtime/this-firefox` — open the popup and
confirm the Download button still triggers a message, and that YouTube ad
blocking still works — and re-read the manifest diff specifically for the
Chrome-vs-Firefox keys above; this is the exact class of bug that fails
silently (extension installs fine, native messaging just never connects).
Also run `npx web-ext lint --source-dir=extension` and confirm it stays at
0 errors.
