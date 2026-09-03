// Background service worker (Chrome) / event page (Firefox). Relays
// download requests from the popup to the native host, and relays the
// native host's progress/completion messages back out to whichever UI
// (popup) is listening. See specs/01-extension-spec.md, "Messaging
// contract", and specs/02-native-host-spec.md for the message shapes.
import { sendToNativeHost, onNativeHostError } from "../lib/native-messaging.js";

// Tracks in-flight requestIds so a popup opened after the download started
// can still be told the latest known status.
const requestStatus = new Map();

// Requests still waiting on a first response from the native host. Needed
// so a connection failure (host not installed/registered, manifest
// misconfigured) can be turned into a real download.error for whichever
// specific requestId(s) were waiting on it — without this, the popup
// would wait forever for a message that can now never arrive, since a
// failed connectNative() otherwise only logs a console warning (see
// native-messaging.js).
const pendingRequestIds = new Set();

function handleNativeMessage(message) {
  if (message && message.requestId) {
    requestStatus.set(message.requestId, message);
    if (message.type !== "download.progress") {
      pendingRequestIds.delete(message.requestId);
    }
  }
  // Best-effort relay to any open popup/options page; if none is open this
  // simply has no listener, which is fine — requestStatus above is the
  // source of truth a newly-opened popup can poll on demand.
  chrome.runtime.sendMessage(message).catch(() => {});
}

onNativeHostError(() => {
  pendingRequestIds.forEach((requestId) => {
    handleNativeMessage({ type: "download.error", requestId, message: "host-unreachable" });
  });
  pendingRequestIds.clear();
});

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type === "download.request") {
    pendingRequestIds.add(message.requestId);
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
