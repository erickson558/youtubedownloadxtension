# 01 — Extension Spec

Depends on [[00-project-spec]]. Implemented under `extension/`.

## Manifest

Manifest V3, single `manifest.json` for both browsers:

- `background`: declares **both** `service_worker` (used by Chromium) and
  `scripts` (used by Firefox) pointing at the same
  `src/background/background.js`. This is the documented cross-browser
  pattern — do not split into two manifests for this.
- `browser_specific_settings.gecko.id`:
  `youtubedownloadxtension@erickson558.github.io`. Mandatory for Firefox.
  This exact string is also the value used in the Firefox native-messaging
  host manifest's `allowed_extensions` (see [[02-native-host-spec]]) — if the
  two ever diverge, the native host silently refuses to launch on Firefox.
- `browser_specific_settings.gecko.strict_min_version`: `113.0` — the
  floor `declarative_net_request.rule_resources` needs on Firefox (see
  "Ad blocking" below); anything declaring that key on an older Firefox
  gets a lint warning and the rules silently never load.
- Permissions: `storage`, `activeTab`, `nativeMessaging`,
  `declarativeNetRequest`. No `host_permissions` — reading the active
  tab's URL/title uses `activeTab` (see "Download trigger" below), and
  the ad-blocking content script's `matches` in `content_scripts` is its
  own grant, not duplicated here.
- `content_scripts`: `src/content/youtube-adblock.js`, matching
  `*://*.youtube.com/*`. Injects no visible DOM element of its own — see
  "Ad blocking".

## History

Two earlier designs, in order, before landing back where the project
started (with real fixes and ad blocking added along the way):

1. **Injected in-page "Download" button.** Removed after repeated,
   reproduced collisions with other extensions' own UI in the same
   "under the player" spot — with 20+ other YouTube/video-download
   extensions commonly installed alongside this one in the wild, that was
   an open-ended arms race, not a bounded bug.
2. **Fully client-side extraction (`youtube-extract.js`), no desktop app
   at all.** Tried at the user's explicit request, after being warned
   YouTube's server-side adaptive streaming (SABR) rollout and
   Proof-of-Origin-Token (PoToken) requirement would very likely make it
   unreliable, and choosing to accept that anyway. Confirmed directly,
   not assumed: the classic signature/`n`-parameter extraction techniques
   every lightweight (non-`yt-dlp`-based) YouTube downloader relies on
   fail against the current player, and — the deciding finding — the
   video is actually served over the SABR protocol
   (`streamingData.serverAbrStreamingUrl` present from the very first
   byte of the page, confirmed by capturing it before YouTube's own
   script clears it), a binary/session-based streaming negotiation
   entirely unlike "fetch a URL". Implementing SABR support and PoToken
   generation (which itself requires either running a full BotGuard JS
   challenge in a real browser or a separate helper server —
   `yt-dlp`/`bgutil-ytdlp-pot-provider`'s approach — neither available
   inside a content script's sandbox) is beyond what a browser extension
   can do alone; `yt-dlp` needed a dedicated PR and ongoing maintenance
   for SABR support specifically. **No video was ever confirmed to
   complete an actual download with this design.** Removed outright —
   the code is gone, not kept dormant, since it doesn't work and isn't
   coming back without those two missing pieces.

Both are documented in the CHANGELOG in more detail, including the
specific dead ends (SABR, PoToken, the `n`-parameter 403) confirmed while
trying design 2, kept there so nobody re-attempts the exact same
approach without knowing it was already tried and why it failed.

## Download trigger (toolbar popup + desktop app)

The toolbar popup (`src/popup/`) sends the active tab's URL to the local
desktop companion app (the native host, `backend/`) over WebExtensions
native messaging; the host asks where to save and downloads with
`yt-dlp` (any of the ~1800 sites it supports, full quality — video-only
and audio-only streams muxed with `ffmpeg`, which the host can invoke
and a browser extension cannot).

- On open, the popup queries the current tab
  (`chrome.tabs.query({ active: true, currentWindow: true })`) to read its
  `url` and `title`. This works without `host_permissions` because
  `activeTab` grants the extension temporary access to the active tab's
  real `url`/`title` specifically when the user invokes the extension
  (opening the popup from the toolbar icon counts as that invocation).
- Clicking the popup's "Download" button sends
  `chrome.runtime.sendMessage({ type: "download.request", url: tab.url, pageTitle: tab.title, requestId })`.
  The URL sent is always the tab's page URL — there is no content script
  reading anything out of the page's own DOM.
- The desktop app launches automatically the first time this happens
  (that's what `chrome.runtime.connectNative()` does — the browser starts
  the registered host process if it isn't already running) and closes
  itself automatically once the download settles, so the user never has
  to manually open or close it for a one-off download — see
  [[02-native-host-spec]], "Auto-close on settle", for exactly when.
- While waiting for a response, the button is disabled and shows a
  "Downloading…" state; the popup listens on `chrome.runtime.onMessage`
  for `download.progress` / `download.complete` / `download.error`
  matching its `requestId` and updates its status text accordingly, then
  re-enables the button.

## Ad blocking

Kept from the client-side-extraction design (design 2 above) even though
its download feature was removed — ad blocking is unrelated to how
downloads happen and has its own real value. Two complementary pieces,
since network-level blocking alone cannot remove an in-player *video* ad
(it streams from the same googlevideo.com CDN as real content, so
blocking that domain would break real playback too):

- `src/rules/youtube-adblock-rules.json`, registered via
  `declarative_net_request.rule_resources`: blocks known ad/tracking
  request domains (`doubleclick.net`, `googlesyndication.com`,
  `googleadservices.com`) and YouTube's own `/pagead/`,
  `/api/stats/ads`, and `/get_midroll_*` request paths.
- `src/content/youtube-adblock.js`: watches for YouTube's own
  `ad-showing` class on the player element and, once found, clicks
  whichever of YouTube's own skip-ad buttons is present
  (`.ytp-ad-skip-button`, `.ytp-ad-skip-button-modern`,
  `.ytp-skip-ad-button`); if none is present (a non-skippable ad, or the
  skip option hasn't appeared yet), it instead jumps `video.currentTime`
  to `video.duration` to get past the ad segment quickly. Only ever
  interacts with elements YouTube's own player already rendered — never
  adds a visible element of its own, so this cannot collide with another
  extension's UI either.

## Messaging contract

Popup → background → native host. The popup cannot call native-messaging
APIs directly.

1. Popup, on click: `chrome.runtime.sendMessage({ type: "download.request", url, pageTitle, requestId })`.
2. Background worker holds a persistent `chrome.runtime.connectNative("com.erickson558.ytdlx")`
   `Port` (not `sendNativeMessage` — a one-shot call cannot stream progress
   back). The `hostName` string must exactly match the `name` field in both
   native-host manifest files (see [[02-native-host-spec]]).
3. Because an MV3 service worker can be suspended after ~30s idle, the
   background worker must not assume the port survives: lazily call
   `connectNative` again if `port` is undefined or its `onDisconnect` fired.
4. Background relays native-host messages (`download.progress`,
   `download.complete`, `download.error`) back to the popup via
   `chrome.runtime.sendMessage`, keyed by `requestId`.
5. If `connectNative` itself fails or the port disconnects with an error
   (native host not installed/registered, manifest misconfigured), the
   popup would otherwise wait forever for a message that can now never
   arrive — a real, reported bug. Background tracks pending `requestId`s
   and, on that disconnect, synthesizes a
   `{ type: "download.error", requestId, message: "host-unreachable" }`
   for each one still pending and relays it exactly like a real
   native-host message. `"host-unreachable"` is purely an
   extension-internal value; unlike `"cancelled"` (sent by the host
   itself, see [[02-native-host-spec]]), it never crosses the
   native-messaging wire, since that connection is precisely what failed.
6. As a last-resort safety net for anything background.js doesn't
   explicitly detect (e.g. the service worker itself dying), the popup
   also runs its own 20s timeout per request, reset on every
   `download.progress` so a long-running download is never cut off by
   it, that synthesizes the same "couldn't reach the app" outcome
   locally if nothing arrives in time.

## UI surfaces

- **Popup** (`src/popup/`): the Download button and status for the active
  tab (see "Download trigger" above), plus the donation button.
- **Options page** (`src/options/`): language override (see [[04-i18n-spec]]),
  donation button.
- **Donation button**: a link to
  `https://www.paypal.com/donate/?hosted_button_id=ZABFRXC2P3JQN`, labelled
  via an i18n key (`donateButton`), present in both popup and options page.
- **First-run notice**: on `chrome.runtime.onInstalled` with `reason === "install"`,
  open the options page once, showing the disclaimer text from
  [[00-project-spec]].

## Related specs

[[02-native-host-spec]] · [[03-security-spec]] · [[04-i18n-spec]]
