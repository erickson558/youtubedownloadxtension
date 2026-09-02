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
      // `video.currentSrc` is a `blob:` URL on any site using Media Source
      // Extensions for adaptive streaming (YouTube always does) -- it only
      // resolves inside this page's own JS context, so handing it to the
      // native host's yt-dlp subprocess is a silent no-op download failure
      // (yt-dlp cannot follow it at all). Only trust currentSrc when it is
      // a real, externally-fetchable URL (a plain progressive <video src>,
      // on a generic non-SPA site); otherwise fall back to the page URL,
      // which is what yt-dlp actually needs to re-extract the stream.
      const src = video.currentSrc;
      const url = src && !src.startsWith("blob:") ? src : location.href;
      sendDownloadRequest(url, document.title);
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

  function isForeignElementAt(host, x, y) {
    // pointer-events: none makes elementFromPoint skip `host` (and its
    // shadow content) for hit-testing, revealing whatever else is rendered
    // at that screen position.
    host.style.pointerEvents = "none";
    const el = document.elementFromPoint(x, y);
    host.style.pointerEvents = "";
    if (!el) return false;
    // Walking up from `host` always reaches its own ancestor chain (the
    // parent container naturally sits "underneath" a child at the same
    // point) -- that is not a collision. Anything else found there is a
    // sibling/foreign element genuinely occupying the same space.
    for (let node = host; node; node = node.parentElement) {
      if (node === el) return false;
    }
    return true;
  }

  function avoidOverlap(host) {
    // Other extensions can inject their own UI in this same "under the
    // player" area (observed colliding with a YouTube-enhancer-style
    // toolbar, via floats/negative margins/absolute positioning on their
    // side, none of which our own CSS alone can prevent). Nudge the button
    // down, bounded, until nothing foreign renders at its own position.
    //
    // Sampled on a 3x3 grid (top/middle/bottom rows), not just the
    // vertical center: a foreign element only partially covering `host`
    // (e.g. clipping its top edge as a nudge closes the gap) is invisible
    // to a single center row, which reports "clear" one step too early --
    // caught via a local test fixture, not a hypothetical.
    const MAX_NUDGES = 12;
    const STEP_PX = 10;
    for (let nudges = 0; nudges < MAX_NUDGES; nudges += 1) {
      const rect = host.getBoundingClientRect();
      if (rect.width === 0 || rect.height === 0) return; // not laid out/visible yet
      const xs = [rect.left + 2, rect.left + rect.width / 2, rect.right - 2];
      const ys = [rect.top + 2, rect.top + rect.height / 2, rect.bottom - 2];
      const overlapping = ys.some((y) => xs.some((x) => isForeignElementAt(host, x, y)));
      if (!overlapping) return;
      host.style.marginTop = `${(nudges + 1) * STEP_PX}px`;
    }
  }

  function inject(video, placement, shouldInject) {
    if (video.hasAttribute(INJECTED_ATTR) || !isRealVideo(video)) return;
    if (shouldInject && !shouldInject(video)) return;
    video.setAttribute(INJECTED_ATTR, "1");
    const button = buildButton(video);
    placement(video, button);
    injectedPairs.push({ video, host: button });
    // Checked once now and once shortly after: other extensions' UI can be
    // injected asynchronously, after ours has already been placed.
    avoidOverlap(button);
    setTimeout(() => avoidOverlap(button), 500);
  }

  function scan(placement, shouldInject) {
    document.querySelectorAll("video").forEach((video) => inject(video, placement, shouldInject));
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
