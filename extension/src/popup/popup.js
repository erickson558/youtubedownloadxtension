import { localizeDocument, t } from "../lib/i18n.js";

await localizeDocument();

const downloadButton = document.getElementById("download");
const statusEl = document.getElementById("status");
const downloadLabel = t("downloadButton");
downloadButton.textContent = downloadLabel;

// Standalone download: the toolbar popup asks the YouTube content script
// (src/content/youtube-extract.js) to extract a direct file URL for the
// current tab's video, then hands it straight to the browser's own
// downloads API -- no desktop companion app, no native messaging. See
// specs/01-extension-spec.md, "Direct download (experimental, YouTube
// only)" for why this only ever works for some videos, not all: it is a
// deliberate, accepted trade-off for not requiring a separate install.
async function currentTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return tab;
}

function setStatus(key) {
  statusEl.textContent = t(key);
}

function isYouTubeUrl(url) {
  try {
    const { hostname } = new URL(url);
    return hostname === "youtube.com" || hostname.endsWith(".youtube.com") || hostname === "youtu.be";
  } catch {
    return false;
  }
}

function sanitizeFilename(name) {
  return (
    name
      .replace(/[\\/:*?"<>|]+/g, " ")
      .trim()
      .slice(0, 150) || "video"
  );
}

downloadButton.addEventListener("click", async () => {
  const tab = await currentTab();
  if (!tab || !tab.url) {
    setStatus("popupNoActiveDownload");
    return;
  }

  if (!isYouTubeUrl(tab.url)) {
    setStatus("popupYoutubeOnly");
    return;
  }

  downloadButton.disabled = true;
  downloadButton.textContent = t("downloadStarted");
  setStatus("downloadStarted");

  let result = null;
  try {
    result = await chrome.tabs.sendMessage(tab.id, { type: "ytdlx.extract" });
  } catch {
    // Content script not present in this tab (e.g. the page loaded
    // before the extension did) -- handled the same as "not available"
    // below, since there is nothing else to try.
  }

  if (result?.available) {
    const filename = `${sanitizeFilename(result.title)}.${result.ext}`;
    try {
      await chrome.downloads.download({ url: result.url, filename, saveAs: true });
      setStatus("popupDownloadStartedBrowser");
    } catch {
      setStatus("downloadFailed");
    }
  } else {
    setStatus("popupVideoNotAvailable");
  }

  downloadButton.disabled = false;
  downloadButton.textContent = downloadLabel;
});
