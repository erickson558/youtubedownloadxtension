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
- Permissions: `nativeMessaging`, `storage`, `activeTab`. No broad
  `<all_urls>` permission.
- `host_permissions`: scoped to `*://*.youtube.com/*` and `*://*.youtu.be/*`
  for the fully-supported flow. Other sites are opt-in via
  `optional_host_permissions` requested from the options page, never granted
  silently — this keeps the install-time permission prompt honest.

## Video detection & button injection

YouTube is a single-page app: normal `<video>`-appeared-on-page-load logic is
not enough because navigating between videos does not reload the page.

- Primary trigger: listen for the `yt-navigate-finish` event on `document`
  (YouTube's own internal SPA-navigation-complete event). Re-scan for
  `<video>` elements on every firing.
- Backup trigger: a debounced `MutationObserver` on `document.querySelector('ytd-app')`
  (fallback to `document.body` if not found), `{ childList: true, subtree: true }`,
  in case `yt-navigate-finish` stops firing after a YouTube redesign.
- Idempotency: mark each handled `<video>` with `data-ytdlx-injected="1"` so a
  video is never double-injected across repeated scans.
- Placement: insert the button as a sibling near `#below` on the YouTube
  watch page (below the player/description area), **not** as an overlay on
  top of the `<video>` element itself — overlaying risks breaking YouTube's
  own player hit-testing and needs replacing every time YouTube's player
  chrome changes. On generic (non-YouTube) pages, fall back to inserting a
  sibling `<div>` immediately after the `<video>` node.
- Isolation: the button and its styles live inside a Shadow DOM
  (`element.attachShadow({mode: "open"})`) so YouTube's global CSS cannot
  affect the button and the button's CSS cannot leak onto the page.
- Host-element layout: the shadow host gets `all: initial` for isolation,
  which also resets `display` to its CSS-initial value (`inline`) — this
  must always be followed by explicitly setting `display: block`,
  `position: relative`, and a high `z-index` on the host. Without this, the
  host is an inline box with no guaranteed stacking context, which can
  visually collide with another extension's own UI injected in the same
  "under the player" area (observed with a YouTube-enhancer-style
  extension's toolbar occupying the same spot) instead of rendering on its
  own row above/below it.
- Collision avoidance: `display: block` alone does not guarantee visual
  separation from another extension's floating/absolutely-positioned UI in
  the same spot, since that other element may not participate in normal
  flow at all. After placement, sample a 3x3 grid of points across the
  host's own bounding rect via `elementFromPoint` (with the host
  temporarily `pointer-events: none` so it doesn't hit-test itself) and, if
  any point resolves to an element outside the host's own ancestor chain,
  nudge the host down with `margin-top` in bounded steps (12 steps of
  10px) until clear. A single center-row sample is not enough — a
  partial overlap confined to one edge of the rect can go undetected as a
  nudge closes the gap (confirmed with a local test fixture); sampling
  top/middle/bottom rows catches it. Re-run once more ~500ms after initial
  placement, since a competing extension's UI may be injected
  asynchronously. This cannot defend against a foreign element that
  recomputes its own position relative to wherever the host currently is
  (e.g. a negative margin sized to its previous sibling) — that specific
  construction has no fixed target to clear and is a known, accepted
  limitation of a downward-nudge strategy.
- Cleanup: on `yt-navigate-start`, remove any injected button whose
  associated `<video>` node is no longer attached to the document, to avoid
  DOM/listener leaks on long-lived YouTube tabs.

## Messaging contract

Content script → background → native host. Content scripts cannot call
native-messaging APIs directly.

1. Content script, on click: `chrome.runtime.sendMessage({ type: "download.request", url, pageTitle, requestId })`.
2. Background worker holds a persistent `chrome.runtime.connectNative("com.erickson558.ytdlx")`
   `Port` (not `sendNativeMessage` — a one-shot call cannot stream progress
   back). The `hostName` string must exactly match the `name` field in both
   native-host manifest files (see [[02-native-host-spec]]).
3. Because an MV3 service worker can be suspended after ~30s idle, the
   background worker must not assume the port survives: lazily call
   `connectNative` again if `port` is undefined or its `onDisconnect` fired.
4. Background relays native-host messages (`download.progress`,
   `download.complete`, `download.error`) back to the popup/content script via
   `chrome.runtime.sendMessage`, keyed by `requestId`.

## UI surfaces

- **Popup** (`src/popup/`): shows the current download queue/status for the
  active tab and the donation button (see below).
- **Options page** (`src/options/`): language override (see [[04-i18n-spec]]),
  optional-site permission requests, donation button.
- **Donation button**: a link to
  `https://www.paypal.com/donate/?hosted_button_id=ZABFRXC2P3JQN`, labelled
  via an i18n key (`donateButton`), present in both popup and options page.
- **First-run notice**: on `chrome.runtime.onInstalled` with `reason === "install"`,
  open the options page once, showing the disclaimer text from
  [[00-project-spec]].

## Related specs

[[02-native-host-spec]] · [[03-security-spec]] · [[04-i18n-spec]]
