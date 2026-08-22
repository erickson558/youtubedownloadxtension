// Fallback injection logic for non-YouTube sites, used once a user grants
// the optional *://*/* host permission from the options page (see
// specs/01-extension-spec.md — "other sites" is opt-in, never silent).
//
// Not registered as a static content script in manifest.json: it is
// injected dynamically via chrome.scripting.executeScript by the
// background worker, only into tabs matching a permission the user has
// explicitly granted. See background.js.
(function () {
  "use strict";

  const engine = window.__ytdlxEngine;
  if (!engine) return;

  function placeAfterVideo(video, buttonHost) {
    // No site-specific layout knowledge here, so the safest placement is
    // simply right after the <video> element itself.
    video.insertAdjacentElement("afterend", buttonHost);
  }

  function rescan() {
    engine.scan(placeAfterVideo);
  }

  // Generic sites don't have a reliable SPA-navigation event to hook, so a
  // debounced MutationObserver on <body> is the only re-scan trigger.
  let debounceTimer = null;
  const observer = new MutationObserver(() => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(rescan, 250);
  });
  observer.observe(document.body, { childList: true, subtree: true });

  rescan();
})();
