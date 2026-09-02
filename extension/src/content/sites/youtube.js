// YouTube-specific hooks: decides *when* the shared engine (content.js)
// should re-scan for <video> elements and *where* to place the injected
// button on a YouTube watch page. See specs/01-extension-spec.md.
(function () {
  "use strict";

  const engine = window.__ytdlxEngine;
  if (!engine) return; // content.js failed to load; nothing we can do here

  function placeBelowPlayer(video, buttonHost) {
    // Insert near #below (YouTube's description/metadata area under the
    // player), never as an overlay on top of the <video> itself — an
    // overlay risks breaking YouTube's own player hit-testing and needs
    // reworking every time YouTube reshuffles its player chrome.
    //
    // Idempotent by design so it's safe to call again on every later
    // rescan, not just once at creation (see engine.relocate() below):
    // #below can still be missing for a few hundred ms after the player
    // itself is ready and has a real <video>, since YouTube hydrates the
    // page progressively. The real player's own <video> is typically
    // `position: absolute` inside a `position: relative` wrapper, so a
    // normal-flow button inserted right after it (the fallback) renders
    // at that wrapper's top-left corner, on top of the video -- reported
    // by a real user, not a hypothetical. Re-placing on every rescan lets
    // a button stuck in that fallback move into #below the moment it
    // exists, instead of being stuck there for the rest of the page view.
    const below = document.querySelector("#below");
    if (below) {
      if (below.firstElementChild !== buttonHost) below.prepend(buttonHost);
      return;
    }
    if (!buttonHost.isConnected) {
      // Only resort to this if the button isn't placed anywhere yet --
      // once #below exists on a later rescan, the branch above takes
      // over instead of this running again every time.
      video.insertAdjacentElement("afterend", buttonHost);
    }
  }

  function isMiniplayerVideo(video) {
    // YouTube's floating miniplayer (engaged by scrolling away from the
    // player, or explicitly) can keep its own <video> on the page
    // alongside the main one, both reporting a real duration -- without
    // this filter each gets its own button, showing two identical
    // "Download" buttons for what the user sees as a single video.
    return Boolean(video.closest("ytd-miniplayer"));
  }

  function rescan() {
    engine.scan(placeBelowPlayer, (video) => !isMiniplayerVideo(video));
    // Re-run placement for buttons already created, not just new videos:
    // this is what lets a button stuck in the risky fallback (see
    // placeBelowPlayer) move into #below once it exists, on the very next
    // rescan -- which the MutationObserver below fires frequently during
    // YouTube's progressive page hydration.
    engine.relocate(placeBelowPlayer);
  }

  // Primary trigger: YouTube's own SPA-navigation-complete event. This is
  // an internal YouTube event (undocumented but long-stable, relied on by
  // many existing extensions) rather than a real page load, since YouTube
  // never does a full navigation between videos.
  document.addEventListener("yt-navigate-finish", rescan);
  document.addEventListener("yt-navigate-start", () => engine.cleanup());

  // Backup trigger: in case yt-navigate-finish stops firing after a future
  // YouTube change, a debounced MutationObserver on the app root catches
  // new <video> elements another way.
  let debounceTimer = null;
  const observerRoot = document.querySelector("ytd-app") || document.body;
  const observer = new MutationObserver(() => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(rescan, 250);
  });
  observer.observe(observerRoot, { childList: true, subtree: true });

  // Initial scan for the page this content script first loaded on.
  rescan();
})();
