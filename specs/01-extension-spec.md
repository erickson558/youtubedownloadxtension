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
- `browser_specific_settings.gecko.strict_min_version`: `113.0` — the
  floor `declarative_net_request.rule_resources` needs on Firefox (see
  "Ad blocking" below); anything declaring that key on an older Firefox
  gets a lint warning and the rules silently never load.
- Permissions: `storage`, `activeTab`, `downloads`, `declarativeNetRequest`.
  No `nativeMessaging`, no `host_permissions` — there is no desktop
  companion app any more (see "History" below).
- `content_scripts`: `src/content/youtube-extract.js` and
  `src/content/youtube-adblock.js`, matching `*://*.youtube.com/*` only.
  Neither injects any visible DOM element of its own — one only reads page
  data when asked, the other only clicks/adjusts YouTube's *own* existing
  player elements — so neither can visually collide with another
  extension's UI the way the removed injected-button design once did (see
  "History").

## History

Two designs preceded the current one, in order:

1. **Injected in-page "Download" button.** Removed after repeated,
   reproduced collisions with other extensions' own UI in the same
   "under the player" spot — with 20+ other YouTube/video-download
   extensions commonly installed alongside this one in the wild, that was
   an open-ended arms race, not a bounded bug.
2. **Toolbar popup + local desktop companion app (`backend/`), talking
   over WebExtensions native messaging.** Removed at the user's explicit
   request to not require installing anything separate, after being
   warned of the trade-off (see "Direct download" below) and choosing to
   accept it anyway. `backend/` still exists in the repository and still
   works exactly as documented in [[02-native-host-spec]] and
   [[03-security-spec]] — it is simply no longer *used* by this
   extension. Removing it outright is a separate, not-yet-made decision.

Both are documented in the CHANGELOG, not repeated here since the code
they describe no longer runs.

## Direct download (experimental, YouTube only)

The toolbar popup (`src/popup/`) asks the YouTube content script
(`src/content/youtube-extract.js`) to extract a direct, playable file URL
for the current tab's video, then hands that URL straight to
`chrome.downloads.download({ url, filename, saveAs: true })` — the
browser's own download manager, prompting for a save location every time,
same as before. No native messaging, no separate process.

**This only works for some videos, not all — a deliberate, informed
trade-off, not a bug to "fix":**

- Only **progressive** formats (`streamingData.formats`, video+audio
  already combined into one file) are usable at all: a browser extension
  cannot invoke `ffmpeg`, so it cannot mux a separate video-only +
  audio-only pair the way `yt-dlp` does for higher qualities. This caps
  quality at whatever YouTube's progressive format tops out at (typically
  360p).
- Some progressive formats carry the direct file URL already
  (`format.url`), skipping the signature-decipher step below — but even
  these are not automatically usable, since they can still carry a
  throttling `n` param that must be fixed too (see further down). Most
  videos' progressive format instead carries a `signatureCipher` that
  must be deciphered first —
  YouTube encodes the real URL's signature by running it through a short
  sequence of array operations (reverse / remove-from-front / swap)
  defined in that page load's player JS, in an order that changes per
  player build.
- `youtube-extract.js` looks for that operation sequence (the same
  technique every non-`yt-dlp`-based YouTube downloader uses — confirmed
  by extracting and reading one such installed, real extension's own
  decipher code during this feature's research) and replays it. **As of
  2026-09-03, this fails to even locate the sequence against a live,
  current player build for an ordinary popular video** — most likely
  because YouTube's server-side adaptive streaming rollout (SABR) has
  moved the WEB client off the code shape these patterns look for.
  Verified directly, not assumed: neither this project's own pattern set
  nor the installed extension's were able to locate it against the same
  real player JS. It is kept anyway because YouTube ships player builds
  gradually (some sessions may still get a build this matches), it costs
  nothing extra when it fails, and reverting the deciphered signature
  back would need no extension update if YouTube's structure shifts back.
  **Do not describe this as a reliable capability anywhere user-facing —
  it is explicitly experimental, and empirically fails far more often
  than it succeeds today.**
- Separately, a resolved URL's `n` query parameter throttles playback
  speed unless also transformed by another player-embedded function.
  `youtube-extract.js` attempts this too (evaluating the extracted
  function's body via `new Function(...)`, flagged `DANGEROUS_EVAL` by
  `web-ext lint` — expected, not a bug; safe only because youtube.com's
  own CSP allows `'unsafe-eval'`, verified directly against the live
  response header). **This also fails to locate the transform against the
  current player as of 2026-09-03** — checked directly, including the
  exact multi-pattern search a real installed extension's own decipher
  code uses for this specific step, not just this project's own first
  attempt at it.
- **The `n` fix is not optional the way it first looked — a real
  download attempt proved this, don't re-loosen it.** The initial
  version of this feature applied the `n` transform only on the
  signature-cipher path, on the (reasonable-sounding but wrong)
  assumption that an untransformed `n` merely throttles delivery. A real
  user report showed the popup successfully extracting a URL for a
  format with *no signature cipher at all* and starting a download that
  then failed; fetching that exact URL directly confirmed YouTube's CDN
  returns **HTTP 403** for an untransformed `n`, not a slow response.
  `youtube-extract.js` now checks every candidate URL (cipher path or
  plain `url`) for an `n` param and treats the candidate as unusable —
  moving to the next format, or returning `{available:false, reason:
  "no-usable-format"}` — if a required `n` transform can't be applied,
  rather than ever handing back a URL known to fail.
- Net effect, stated plainly so nobody re-discovers this the hard way:
  **as of 2026-09-03, no video has been confirmed to complete an actual
  download end-to-end with this feature.** Both transform-extraction
  paths are implemented and kept because they cost nothing when they
  fail cleanly and a future/different player build may match one of
  them, not because either is currently known to work. What changed
  with the `n`-param fix above is not "downloads now succeed" — it's
  "the popup now reports unavailable honestly upfront, instead of
  showing a misleading in-progress download that then fails in the
  browser's own downloads UI."
- When nothing usable is found, the content script returns
  `{ available: false, reason: ... }`; the popup shows one generic
  "couldn't download this video directly" message (`popupVideoNotAvailable`)
  regardless of the specific reason — deliberately not a technical error
  dump, since the reason is rarely actionable by the user.
- Outside `youtube.com`/`*.youtube.com` tabs, the popup shows
  `popupYoutubeOnly` and does not attempt anything — this feature is
  YouTube-only, full stop; it does not attempt yt-dlp's ~1800-site
  breadth (that bar always required the desktop app).

## Ad blocking

Two complementary pieces, since network-level blocking alone cannot
remove an in-player *video* ad (it streams from the same googlevideo.com
CDN as real content, so blocking that domain would break real playback
too):

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

## UI surfaces

- **Popup** (`src/popup/`): the Download button and status for the active
  tab (see "Direct download" above), plus the donation button.
- **Options page** (`src/options/`): language override (see [[04-i18n-spec]]),
  donation button.
- **Donation button**: a link to
  `https://www.paypal.com/donate/?hosted_button_id=ZABFRXC2P3JQN`, labelled
  via an i18n key (`donateButton`), present in both popup and options page.
- **First-run notice**: on `chrome.runtime.onInstalled` with `reason === "install"`,
  open the options page once, showing the disclaimer text from
  [[00-project-spec]].

## Related specs

[[02-native-host-spec]] (describes `backend/`, currently unused by this
extension — see "History" above) · [[03-security-spec]] · [[04-i18n-spec]]
