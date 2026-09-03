// Runs on YouTube pages only, in the isolated world. Injects NO visible
// DOM of its own -- it exists purely to answer the popup's "can this
// video be downloaded directly, with no desktop app?" question when
// asked via chrome.tabs.sendMessage. See specs/01-extension-spec.md,
// "Direct download (experimental, YouTube only)".
//
// KNOWN, ACCEPTED LIMITATION, confirmed by testing against a live
// YouTube player build (2026-09-03), not assumed: BOTH the signature
// decipher (replaying a short, fixed sequence of
// reverse/remove-from-front/swap operations found in the player's own
// JS) and the separate "n" parameter (anti-throttling) transform --
// techniques every lightweight (non-yt-dlp-based) YouTube downloader has
// relied on for years, this project's own installed-extension research
// included -- fail to even locate their respective functions against the
// current player. Most likely YouTube's server-side adaptive streaming
// (SABR) rollout has moved the WEB client off the code shape these
// patterns look for.
//
// The "n" transform is NOT optional the way it first looked: a real
// download attempt on a format with *no signature cipher at all* was
// still rejected outright (HTTP 403, not merely throttled) with an
// untransformed "n" left in the URL. So a resolved URL is only ever
// returned once its "n" param (if it has one) is confirmed fixed --
// with today's player, that means this returns {available:false} for
// every video tested so far, cipher or not. Both extraction paths are
// kept anyway because they cost nothing when they fail cleanly and
// YouTube ships player builds gradually, so some session may still get
// one either pattern set matches. Do not present this as a reliable
// capability in UI copy -- as of today it is unconfirmed to complete an
// actual download for any video.
(function () {
  "use strict";

  function extractBalancedJson(html, marker) {
    const idx = html.indexOf(marker);
    if (idx === -1) return null;
    const braceStart = html.indexOf("{", idx);
    if (braceStart === -1) return null;
    let depth = 0;
    for (let i = braceStart; i < html.length; i += 1) {
      if (html[i] === "{") depth += 1;
      else if (html[i] === "}") {
        depth -= 1;
        if (depth === 0) {
          try {
            return JSON.parse(html.slice(braceStart, i + 1));
          } catch {
            return null;
          }
        }
      }
    }
    return null;
  }

  function findPlayerJsUrl(html) {
    const m = html.match(/"PLAYER_JS_URL":"([^"]+)"/);
    if (!m) return null;
    return new URL(m[1], location.origin).toString();
  }

  // Locates the decipher function and reads back the sequence of
  // operations it performs, rather than the function's exact code (which
  // is what changes between player builds; the operation *kinds* --
  // historically -- have not).
  function findCipherOperations(playerJs) {
    const callSitePatterns = [
      /\bc=([a-zA-Z0-9$]{1,3})\(decodeURIComponent\(c\)\)/,
      /\.set\(\s*"signature"\s*,\s*([a-zA-Z0-9$]{1,3})\(/,
      /\.sig\|\|([a-zA-Z0-9$]{1,3})\(/,
      /\b([a-zA-Z0-9$]{1,3})=function\(a\)\{a=a\.split\(""\);[^}]*?return a\.join\(""\)\}/,
    ];
    let fnName = null;
    for (const pattern of callSitePatterns) {
      const m = playerJs.match(pattern);
      if (m) {
        fnName = m[1];
        break;
      }
    }
    if (!fnName) return null;

    const escapedFn = fnName.replace(/\$/g, "\\$");
    const fnDefPattern = new RegExp(
      `(?:function ${escapedFn}|[;,]\\s*${escapedFn}\\s*=\\s*function)\\([a-zA-Z0-9$]+\\)\\{(.+?)\\}`,
      "s"
    );
    const fnMatch = playerJs.match(fnDefPattern);
    if (!fnMatch) return null;
    const body = fnMatch[1];

    const helperMatch = body.match(/([a-zA-Z0-9$]+)\.[a-zA-Z0-9$]+\(/);
    if (!helperMatch) return null;
    const escapedHelper = helperMatch[1].replace(/\$/g, "\\$");
    const helperDefMatch = playerJs.match(new RegExp(`var ${escapedHelper}=\\{(.+?)\\};`, "s"));
    if (!helperDefMatch) return null;
    const helperBody = helperDefMatch[1];

    function classify(methodName) {
      const escapedMethod = methodName.replace(/\$/g, "\\$");
      const m = helperBody.match(new RegExp(`${escapedMethod}:function\\([^)]*\\)\\{(.+?)\\}(?:,|$)`, "s"));
      if (!m) return null;
      const methodBody = m[1];
      if (/reverse/.test(methodBody)) return "reverse";
      if (/splice/.test(methodBody)) return "splice";
      return "swap";
    }

    const callPattern = /[a-zA-Z0-9$]+\.([a-zA-Z0-9$]+)\([a-zA-Z0-9$]+(?:,(\d+))?\)/g;
    const ops = [];
    let call;
    while ((call = callPattern.exec(body)) !== null) {
      const kind = classify(call[1]);
      if (!kind) continue;
      ops.push({ kind, arg: call[2] ? parseInt(call[2], 10) : null });
    }
    return ops.length > 0 ? ops : null;
  }

  function applyCipherOperations(signature, ops) {
    const chars = signature.split("");
    for (const op of ops) {
      if (op.kind === "reverse") chars.reverse();
      else if (op.kind === "splice") chars.splice(0, op.arg);
      else if (op.kind === "swap") {
        const idx = op.arg % chars.length;
        const tmp = chars[0];
        chars[0] = chars[idx];
        chars[idx] = tmp;
      }
    }
    return chars.join("");
  }

  // The "n" parameter throttles playback speed unless transformed by
  // another player-embedded function; unlike the signature, this one is
  // evaluated directly. youtube.com's own CSP allows 'unsafe-eval'
  // (confirmed 2026-09-03), so this runs the same way it would in the
  // page's own script. Several call-site shapes are tried because none
  // of them matched a live player build as of 2026-09-03 -- kept anyway
  // in case a different build (mobile web, an A/B test group, a future
  // rollback) still uses one of them. See specs/01-extension-spec.md.
  const N_TRANSFORM_CALL_SITE_PATTERNS = [
    /\.get\("n"\)\)&&\(\w+=([a-zA-Z0-9$]+)(?:\[(\d+)\])?\(\w+\)/,
    /=\s*"nn"\[\+[a-zA-Z0-9$_]+\.[a-zA-Z0-9$_]+\],\s*[a-zA-Z0-9$_]+=[a-zA-Z0-9$_]+\.get\([a-zA-Z0-9$_]+\)\)\s*&&\s*\([a-zA-Z0-9$_]+=([a-zA-Z0-9$]+)(?:\[(\d+)\])?\(/,
    /\(\s*[a-zA-Z0-9$_]+\s*=\s*String\.fromCharCode\(110\)[^)]*\)\s*&&\s*\([a-zA-Z0-9$_]+=([a-zA-Z0-9$]+)(?:\[(\d+)\])?\(/,
  ];

  function findNTransform(playerJs) {
    let fnName = null;
    let arrIndex = null;
    for (const pattern of N_TRANSFORM_CALL_SITE_PATTERNS) {
      const m = playerJs.match(pattern);
      if (m) {
        fnName = m[1];
        arrIndex = m[2];
        break;
      }
    }
    if (!fnName) return null;

    if (arrIndex !== undefined && arrIndex !== null) {
      const escaped = fnName.replace(/\$/g, "\\$");
      const arrMatch = playerJs.match(new RegExp(`${escaped}\\s*=\\s*\\[([a-zA-Z0-9$]+)\\]`));
      if (!arrMatch) return null;
      fnName = arrMatch[1];
    }

    const escapedFn = fnName.replace(/\$/g, "\\$");
    const fnDefMatch = playerJs.match(new RegExp(`${escapedFn}\\s*=\\s*function\\([a-zA-Z0-9$]+\\)\\{.+?\\}`, "s"));
    if (!fnDefMatch) return null;
    try {
      // eslint-disable-next-line no-new-func
      const fn = new Function(`var ${fnDefMatch[0]}; return ${fnName};`)();
      return typeof fn === "function" ? fn : null;
    } catch {
      return null;
    }
  }

  // Returns the url unchanged if it carries no "n" param at all, the
  // transformed url if one was needed and successfully applied, or null
  // if one was needed but couldn't be applied -- callers must treat null
  // as "this candidate isn't usable", not fall back to the untransformed
  // url. Confirmed necessary, not just an optimization: a format with no
  // signature cipher at all was still rejected outright (HTTP 403, not
  // merely throttled) by YouTube's CDN when its "n" param was left
  // untransformed -- tested directly against a real download attempt,
  // contradicting this file's own earlier assumption that skipping this
  // fix only risked throttling.
  function applyNTransform(url, transformFn) {
    try {
      const parsed = new URL(url);
      const n = parsed.searchParams.get("n");
      if (!n) return url;
      if (!transformFn) return null;
      const transformed = transformFn(n);
      if (typeof transformed !== "string" || !transformed || transformed === n) return null;
      parsed.searchParams.set("n", transformed);
      return parsed.toString();
    } catch {
      return null;
    }
  }

  async function fetchPlayerResponseAndHtml() {
    const html = await fetch(location.href, { cache: "no-store" }).then((r) => r.text());
    return { playerResponse: extractBalancedJson(html, "ytInitialPlayerResponse"), html };
  }

  async function extract() {
    const { playerResponse, html } = await fetchPlayerResponseAndHtml();
    if (!playerResponse) return { available: false, reason: "no-player-data" };
    if (playerResponse.playabilityStatus?.status !== "OK") {
      return { available: false, reason: "not-playable" };
    }

    // Progressive formats only (audio+video already combined) -- the
    // only kind this can save without a muxing step it has no way to
    // perform (no ffmpeg access from a browser extension).
    const candidates = (playerResponse.streamingData?.formats || [])
      .filter((f) => f.mimeType && f.mimeType.includes("video/mp4"))
      .sort((a, b) => (b.width || 0) - (a.width || 0));
    if (candidates.length === 0) return { available: false, reason: "no-progressive-format" };

    let playerJs = null;
    let cipherOps;
    let nTransform;
    async function ensurePlayerJs() {
      if (playerJs !== null) return;
      const jsUrl = findPlayerJsUrl(html);
      playerJs = jsUrl ? await fetch(jsUrl, { cache: "no-store" }).then((r) => r.text()).catch(() => "") : "";
      cipherOps = playerJs ? findCipherOperations(playerJs) : null;
      nTransform = playerJs ? findNTransform(playerJs) : null;
    }

    for (const format of candidates) {
      let url = format.url || null;

      if (!url && format.signatureCipher) {
        await ensurePlayerJs();
        if (!cipherOps) continue; // couldn't locate the decipher for this player build

        const params = new URLSearchParams(format.signatureCipher);
        const cipheredSig = params.get("s");
        const baseUrl = params.get("url");
        const spName = params.get("sp") || "signature";
        if (!cipheredSig || !baseUrl) continue;

        const built = new URL(baseUrl);
        built.searchParams.set(spName, applyCipherOperations(cipheredSig, cipherOps));
        url = built.toString();
      }

      if (!url) continue;

      // A resolved URL -- with or without a signature that needed
      // deciphering -- can still carry a throttling "n" param that must
      // also be transformed; see applyNTransform's comment for why a
      // format is skipped entirely rather than downloaded with it left
      // as-is.
      if (new URL(url).searchParams.get("n")) {
        await ensurePlayerJs();
        const fixed = applyNTransform(url, nTransform);
        if (!fixed) continue;
        url = fixed;
      }

      return {
        available: true,
        url,
        title: playerResponse.videoDetails?.title || document.title,
        ext: format.mimeType.includes("mp4") ? "mp4" : "webm",
      };
    }

    return { available: false, reason: "no-usable-format" };
  }

  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message?.type !== "ytdlx.extract") return false;
    extract()
      .then(sendResponse)
      .catch(() => sendResponse({ available: false, reason: "error" }));
    return true;
  });
})();
