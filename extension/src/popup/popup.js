import { localizeDocument, t } from "../lib/i18n.js";

await localizeDocument();

const downloadButton = document.getElementById("download");
const statusEl = document.getElementById("status");
const downloadLabel = t("downloadButton");
downloadButton.textContent = downloadLabel;

// The toolbar action's popup is the download trigger — it sends the
// active tab's URL to the desktop companion app (native host) over
// WebExtensions native messaging, which asks where to save and downloads
// with yt-dlp (any of the ~1800 sites it supports, full quality). See
// specs/01-extension-spec.md, "Messaging contract". `activeTab` (already
// granted the moment this popup opens from the toolbar icon) is what lets
// chrome.tabs.query() below see the current tab's real `url`/`title` --
// no `host_permissions` needed for that.
async function currentTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return tab;
}

function setStatus(key) {
  statusEl.textContent = t(key);
}

downloadButton.addEventListener("click", async () => {
  const tab = await currentTab();
  if (!tab || !tab.url) {
    setStatus("popupNoActiveDownload");
    return;
  }

  downloadButton.disabled = true;
  downloadButton.textContent = t("downloadStarted");
  setStatus("downloadStarted");

  const requestId = `${Date.now()}-${Math.random().toString(36).slice(2)}`;

  // Safety net for whatever background.js doesn't explicitly detect (e.g.
  // the service worker itself dying) -- without this, such a failure
  // leaves the button disabled and "Downloading…" on screen forever, with
  // no way out short of closing and reopening the popup. The native host's
  // own folder-picker dialog is expected to steal focus and close this
  // popup before this could ever fire while the user is just taking their
  // time on it; 20s is generous for everything up to that point (opening
  // the connection, launching the process) without waiting so long that a
  // genuine hang feels broken. Any real signal (progress included) pushes
  // this back out, so a long-running download is never cut off by it.
  const TIMEOUT_MS = 20000;
  let timeoutId = null;
  function resetTimeout() {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => finish("popupHostUnreachable"), TIMEOUT_MS);
  }

  function finish(statusKey) {
    clearTimeout(timeoutId);
    setStatus(statusKey);
    chrome.runtime.onMessage.removeListener(onMessage);
    downloadButton.disabled = false;
    downloadButton.textContent = downloadLabel;
  }

  function onMessage(message) {
    if (!message || message.requestId !== requestId) return;
    if (message.type === "download.progress") {
      resetTimeout();
      // See specs/02-native-host-spec.md, "Message types" -- `percent` is
      // a plain number, not pre-formatted, so it's rendered directly
      // rather than through the i18n layer.
      statusEl.textContent = typeof message.percent === "number" ? `${Math.round(message.percent)}%` : t("downloadStarted");
      return;
    }
    if (message.type === "download.complete") {
      finish("downloadComplete");
    } else if (message.type === "download.error") {
      // handler.py sends the literal string "cancelled" in `message` for
      // that one case (see specs/02-native-host-spec.md, "Download flow");
      // "host-unreachable" is synthesized entirely on the extension side
      // (see background.js) when the native host connection itself fails
      // -- it never crosses the native-messaging wire. Every other value
      // maps to the generic failed message.
      if (message.message === "cancelled") finish("downloadCancelled");
      else if (message.message === "host-unreachable") finish("popupHostUnreachable");
      else finish("downloadFailed");
    }
  }
  chrome.runtime.onMessage.addListener(onMessage);
  resetTimeout();

  chrome.runtime.sendMessage({ type: "download.request", url: tab.url, pageTitle: tab.title, requestId });
});
