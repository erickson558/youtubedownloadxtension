// Background service worker (Chrome) / event page (Firefox). Relays
// download requests from content scripts to the native host, and relays
// the native host's progress/completion messages back out to whichever UI
// (popup) is listening. See specs/01-extension-spec.md, "Messaging
// contract", and specs/02-native-host-spec.md for the message shapes.
import { sendToNativeHost } from "../lib/native-messaging.js";

// Tracks in-flight requestIds so a popup opened after the download started
// can still be told the latest known status.
const requestStatus = new Map();

function handleNativeMessage(message) {
  if (message && message.requestId) {
    requestStatus.set(message.requestId, message);
  }
  // Best-effort relay to any open popup/options page; if none is open this
  // simply has no listener, which is fine — requestStatus above is the
  // source of truth a newly-opened popup can poll on demand.
  chrome.runtime.sendMessage(message).catch(() => {});
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type === "download.request") {
    sendToNativeHost(message, handleNativeMessage);
    sendResponse({ ok: true });
    return true;
  }

  if (message?.type === "status.query") {
    sendResponse(requestStatus.get(message.requestId) || null);
    return true;
  }

  return false;
});

// Open the options page once on first install, showing the disclaimer
// required by specs/00-project-spec.md.
chrome.runtime.onInstalled.addListener((details) => {
  if (details.reason === "install") {
    chrome.runtime.openOptionsPage();
  }
});
