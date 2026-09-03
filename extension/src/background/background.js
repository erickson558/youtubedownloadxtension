// Background service worker (Chrome) / event page (Firefox).
//
// Downloads no longer go through here: the popup extracts a direct file
// URL itself via the YouTube content script and hands it straight to
// chrome.downloads (see specs/01-extension-spec.md, "Direct download").
// This file's only remaining job is the first-run disclaimer.
chrome.runtime.onInstalled.addListener((details) => {
  if (details.reason === "install") {
    chrome.runtime.openOptionsPage();
  }
});
