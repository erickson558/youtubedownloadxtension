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
- Permissions: `nativeMessaging`, `storage`, `activeTab`. No `host_permissions`,
  no content scripts, no broad `<all_urls>` permission — the extension never
  runs any code inside a web page (see "Download trigger" below for why this
  is enough).
- No `content_scripts` entry. A previous design injected a "Download" button
  into the page itself (via a content script watching for `<video>`
  elements); it was removed after repeated reports of the button visually
  colliding with other extensions' own UI in the same "under the player"
  spot, and even after several rounds of collision-avoidance fixes, that
  remained an open-ended arms race against arbitrary third-party page
  content this project cannot control. See the CHANGELOG for that history —
  it is not repeated here since the code it describes no longer exists.

## Download trigger (toolbar popup)

The **only** way to start a download is the toolbar action's popup
(`src/popup/`) — there is no per-page injected UI of any kind, so there is
nothing in any web page for another extension to visually collide with.

- On open, the popup queries the current tab
  (`chrome.tabs.query({ active: true, currentWindow: true })`) to read its
  `url` and `title`. This works without any `host_permissions` because
  `activeTab` — already a declared permission — grants the extension
  temporary access to the active tab's real `url`/`title`/`favIconUrl`
  specifically when the user invokes the extension (opening the popup from
  the toolbar icon counts as that invocation). No permission prompt, no
  per-site opt-in: this works on whatever tab is currently focused,
  regardless of site, the moment the user clicks the icon.
- Clicking the popup's "Download" button sends
  `chrome.runtime.sendMessage({ type: "download.request", url: tab.url, pageTitle: tab.title, requestId })`
  — the same message shape and background/native-host handling as before,
  just originating from the popup instead of a content script. The URL sent
  is always the tab's page URL (`tab.url`), never anything read out of the
  page's own DOM — there is no content script in a position to read
  `video.currentSrc` (or anything else) any more, which also sidesteps the
  `blob:`-URL class of bug a DOM-based approach had to work around: the
  page's own URL is what `yt-dlp` needs to re-extract the stream regardless.
- While waiting for a response, the button is disabled and shows a
  "Downloading…" state; the popup listens on `chrome.runtime.onMessage` for
  `download.progress` / `download.complete` / `download.error` matching its
  `requestId` and updates its status text accordingly, then re-enables the
  button. Since an MV3 popup's JS context is destroyed when it closes, this
  status only updates while the popup stays open — the desktop app's own
  tray/queue window (see [[02-native-host-spec]]) remains the durable way to
  watch a download that's still running after the popup is closed.

## Messaging contract

Popup → background → native host. The popup cannot call native-messaging
APIs directly.

1. Popup, on click: `chrome.runtime.sendMessage({ type: "download.request", url, pageTitle, requestId })`
   (see "Download trigger" above for where `url`/`pageTitle`/`requestId`
   come from).
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
