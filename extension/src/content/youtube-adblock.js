// Runs on every YouTube page. Complements the declarativeNetRequest rules
// in src/rules/youtube-adblock-rules.json: those block ad/tracking
// *requests* (doubleclick.net, googlesyndication.com, YouTube's own
// /pagead/ and /api/stats/ads paths), but the actual in-player video ad
// itself is served from the same googlevideo.com CDN as real content --
// blocking that domain would break real playback too, so it can't be
// stopped at the network level. This instead detects YouTube's own
// "ad-showing" player state and gets past the ad client-side: clicking
// the skip button the moment it's available, or fast-forwarding through
// a non-skippable one.
//
// Only interacts with elements YouTube's own player already renders --
// never adds any visible element of its own, so there is nothing here for
// another extension's UI to collide with (see specs/01-extension-spec.md).
(function () {
  "use strict";

  function trySkipAd() {
    const player = document.querySelector("#movie_player, .html5-video-player");
    if (!player || !player.classList.contains("ad-showing")) return;

    const skipButton = document.querySelector(
      ".ytp-ad-skip-button, .ytp-ad-skip-button-modern, .ytp-skip-ad-button"
    );
    if (skipButton) {
      skipButton.click();
      return;
    }

    // Non-skippable, or skip not offered yet: nothing to click, so fast-
    // forward the ad segment itself instead of waiting it out -- a
    // content script has no way to remove the segment, only get past it.
    const video = player.querySelector("video");
    if (video && Number.isFinite(video.duration) && video.duration > 0) {
      video.currentTime = video.duration;
    }
  }

  const observer = new MutationObserver(trySkipAd);
  observer.observe(document.body, { attributes: true, attributeFilter: ["class"], subtree: true });

  // Backup poll: the class-change mutation can be missed if it happens on
  // an element that gets swapped out and back in during YouTube's own
  // SPA re-renders.
  setInterval(trySkipAd, 500);
})();
