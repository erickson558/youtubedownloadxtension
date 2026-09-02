import { localizeDocument, t } from "../lib/i18n.js";

await localizeDocument();

const downloadButton = document.getElementById("download");
const statusEl = document.getElementById("status");
const downloadLabel = t("downloadButton");
downloadButton.textContent = downloadLabel;

// The toolbar action's popup, not a page-injected button, is the download
// trigger (see specs/01-extension-spec.md, "Download trigger"): no content
// script runs on any page, so there is nothing for another extension's own
// page UI to collide with. `activeTab` (already granted the moment this
// popup opens from the user clicking the toolbar icon) is what lets
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

  function onMessage(message) {
    if (!message || message.requestId !== requestId) return;
    if (message.type === "download.progress") {
      // See specs/02-native-host-spec.md, "Message types" -- `percent` is
      // a plain number, not pre-formatted, so it's rendered directly
      // rather than through the i18n layer.
      statusEl.textContent = typeof message.percent === "number" ? `${Math.round(message.percent)}%` : t("downloadStarted");
      return;
    }
    if (message.type === "download.complete") {
      setStatus("downloadComplete");
    } else if (message.type === "download.error") {
      // handler.py sends the literal string "cancelled" in `message` for
      // that one case (see specs/02-native-host-spec.md, "Download flow");
      // every other value maps to the generic failed message.
      setStatus(message.message === "cancelled" ? "downloadCancelled" : "downloadFailed");
    }
    chrome.runtime.onMessage.removeListener(onMessage);
    downloadButton.disabled = false;
    downloadButton.textContent = downloadLabel;
  }
  chrome.runtime.onMessage.addListener(onMessage);

  chrome.runtime.sendMessage({ type: "download.request", url: tab.url, pageTitle: tab.title, requestId });
});
