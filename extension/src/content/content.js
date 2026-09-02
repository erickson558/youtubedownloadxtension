// Shared video-detection/button-injection engine, used by the per-site
// scripts under src/content/sites/*.js (see specs/01-extension-spec.md).
//
// This file owns *how* to find <video> elements and inject a download
// button; a site script (e.g. youtube.js) owns *when* to ask it to look
// again, since that differs per site (YouTube is a single-page app and
// needs SPA-navigation hooks; a plain site just needs one initial scan).
(function () {
  "use strict";

  const INJECTED_ATTR = "data-ytdlx-injected";

  // Tracks every button we've injected so cleanup() can remove ones whose
  // <video> has since been removed from the page (e.g. after a YouTube SPA
  // navigation tears down the old watch-page DOM). Without this, a
  // long-lived tab accumulates orphaned button elements over time.
  const injectedPairs = [];

  function sendDownloadRequest(url, pageTitle) {
    const requestId = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    chrome.runtime.sendMessage({ type: "download.request", url, pageTitle, requestId });
    return requestId;
  }

  function isRealVideo(video) {
    // Filters out ad/preview <video> elements, which typically report no
    // usable duration.
    return !Number.isNaN(video.duration) && video.duration > 1;
  }

  function buildButton(video) {
    // The button lives inside a Shadow DOM so the host page's CSS can never
    // affect it, and our styles can never leak onto the host page — this
    // matters a lot on YouTube, whose CSS is aggressive and changes often.
    const host = document.createElement("div");
    // `all: initial` isolates from any inherited page styles, but it also
    // resets `display` to its CSS-initial value, "inline" -- left there,
    // the host has no guaranteed own row/stacking context and can visually
    // collide with another extension's UI injected in the same spot below
    // the player (see specs/01-extension-spec.md, "Host-element layout").
    host.style.all = "initial";
    host.style.display = "block";
    host.style.position = "relative";
    host.style.zIndex = "2147483647";
    const shadow = host.attachShadow({ mode: "open" });

    const style = document.createElement("style");
    style.textContent = `
      button {
        font: 13px/1.4 Roboto, Arial, sans-serif;
        background: #d33;
        color: #fff;
        border: none;
        border-radius: 4px;
        padding: 8px 14px;
        cursor: pointer;
        margin: 8px 0;
      }
      button:hover { background: #b22; }
      button:disabled { background: #999; cursor: default; }
    `;
    shadow.appendChild(style);

    const button = document.createElement("button");
    const label = chrome.i18n.getMessage("downloadButton") || "Download";
    button.textContent = label;
    button.addEventListener("click", () => {
      button.disabled = true;
      button.textContent = chrome.i18n.getMessage("downloadStarted") || "Downloading…";
      sendDownloadRequest(video.currentSrc || location.href, document.title);
      // The button itself only gives a lightweight click affordance; real
      // progress/completion is reported asynchronously via the popup
      // (see specs/01-extension-spec.md, "Messaging contract").
      setTimeout(() => {
        button.disabled = false;
        button.textContent = label;
      }, 4000);
    });

    shadow.appendChild(button);
    return host;
  }

  function inject(video, placement) {
    if (video.hasAttribute(INJECTED_ATTR) || !isRealVideo(video)) return;
    video.setAttribute(INJECTED_ATTR, "1");
    const button = buildButton(video);
    placement(video, button);
    injectedPairs.push({ video, host: button });
  }

  function scan(placement) {
    document.querySelectorAll("video").forEach((video) => inject(video, placement));
  }

  function cleanup() {
    for (let i = injectedPairs.length - 1; i >= 0; i -= 1) {
      const { video, host } = injectedPairs[i];
      if (!video.isConnected) {
        host.remove();
        injectedPairs.splice(i, 1);
      }
    }
  }

  window.__ytdlxEngine = { scan, cleanup, INJECTED_ATTR };
})();
