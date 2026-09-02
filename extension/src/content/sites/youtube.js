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
    const below = document.querySelector("#below");
    if (below) {
      below.prepend(buttonHost);
      return;
    }
    // Fallback for layouts where #below isn't present (e.g. Shorts, an
    // embedded player, or a future YouTube redesign): drop the button
    // right after the <video> element itself.
    video.insertAdjacentElement("afterend", buttonHost);
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
