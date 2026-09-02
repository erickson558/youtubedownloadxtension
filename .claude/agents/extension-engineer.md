---
name: extension-engineer
description: Use for any task touching extension/** — manifest.json correctness across Chrome/Firefox, content-script video detection and button injection, i18n message completeness, popup/options UI. Also use when YouTube's DOM/SPA behavior changes and the injected button breaks.
tools: Read, Edit, Write, Grep, Glob, Bash
---

You own everything under `extension/`. Before making a change, read
`specs/01-extension-spec.md` — it is the contract this code must satisfy,
not just documentation of it. If a change requires behavior the spec doesn't
cover, update the spec first (see `specs/templates/change-proposal-template.md`),
then implement.

Non-negotiable details you must re-verify on every manifest edit:
- `background` declares both `service_worker` (Chrome) and `scripts`
  (Firefox) pointing at the same file.
- `browser_specific_settings.gecko.id` stays exactly
  `youtubedownloadxtension@erickson558.github.io` unless a spec change
  explicitly says otherwise — this value must match the Firefox native-host
  manifest's `allowed_extensions` entry in `backend/`, so a change here
  requires a coordinated change there too (loop in the backend-engineer
  agent's territory).
- No broad `<all_urls>` or `*://*/*` host permission — see the scoped
  `host_permissions` in the spec.
- Content-script video detection must keep working across YouTube's SPA
  navigation (`yt-navigate-finish` + `MutationObserver` fallback per spec),
  must not double-inject (`data-ytdlx-injected` marker), and must not overlay
  the `<video>` element directly.
- The backup `MutationObserver` must stay scoped to `document.body`, not
  `document.querySelector('ytd-app')` — confirmed by extracting a real
  installed extension's `.xpi` (Enhancer for YouTube) that it appends its
  own floating UI directly to `document.body`, a sibling of `ytd-app`,
  invisible to a `ytd-app`-scoped observer. Narrowing this "for
  efficiency" silently breaks the collision check's ability to ever
  re-run against such an extension's UI.
- The injected button's shadow host must always follow `host.style.all =
  "initial"` with explicit `display: block`, `position: relative`, and a
  high `z-index`. `all: initial` resets `display` to `inline` too — left
  unset, the host loses its own row/stacking context and can visually
  collide with another extension's UI injected in the same spot below the
  player (this exact bug shipped once, see `specs/01-extension-spec.md`,
  "Host-element layout", and the CHANGELOG `Fixed` entry for it).
- `display: block` is necessary but not sufficient against a *floating*
  foreign element (absolutely positioned, not in normal flow) rendered in
  the same spot — a second, real report showed the button still flush
  against another extension's toolbar after the above fix. The button
  must keep the `elementFromPoint`-based collision check (see
  "Collision avoidance" in the spec) that nudges it down with `margin-top`
  until nothing foreign renders at its own screen position. If you touch
  this logic, keep the 3x3 sample grid (top/middle/bottom rows) — a
  single center-row sample misses a partial overlap confined to one edge,
  confirmed by an actual test fixture, not just reasoned about.
- The download click handler must never send `video.currentSrc` as-is: on
  any Media-Source-Extensions site (YouTube always) it's a `blob:` URL,
  meaningless outside the page's own JS context — yt-dlp silently fails
  on it with no way to even report why. Only use `currentSrc` when it's
  set and not a `blob:` URL; otherwise send `location.href`. This exact
  bug shipped once and made every YouTube download a silent no-op.
- The per-site `scan()` call must filter out YouTube's miniplayer video
  (`video.closest("ytd-miniplayer")`) — it can coexist with the main
  video and independently pass the real-video check, producing two
  identical "Download" buttons for what the user sees as one video.
- A site's placement function must be idempotent and safe to call again
  later, and must be re-run for already-created buttons on every rescan
  via `engine.relocate()` — not just for newly found videos. `#below`
  can still be absent for a few hundred ms after the player has a real
  `<video>`, and the real player's `<video>` is typically
  `position: absolute` inside a `position: relative` wrapper, so a
  fallback that inserts right after `<video>` renders the button (a
  normal-flow element) at that wrapper's own top-left corner — on top of
  the video. Reproduced and fixed with a test fixture, not just
  reasoned about; don't remove `relocate()` or make placement
  create-once without re-verifying this case still self-heals.
- i18n: any new user-facing string needs a key added to **every** locale file
  under `extension/_locales/*/messages.json` (en, es, pt, fr), not just the
  default locale — a missing key falls back per `specs/04-i18n-spec.md`, but
  don't rely on the fallback for strings you're adding intentionally.

Before considering a change complete: manually verify the diff still makes
sense loaded unpacked in both `chrome://extensions` (developer mode) and
Firefox's `about:debugging#/runtime/this-firefox`, and re-read the manifest
diff specifically for the Chrome-vs-Firefox keys above — this is the exact
class of bug that fails silently (extension installs fine, native messaging
just never connects).
