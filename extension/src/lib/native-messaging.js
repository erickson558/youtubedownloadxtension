// Thin wrapper around chrome.runtime.connectNative, used only from the
// background service worker (the popup cannot call native-messaging APIs
// directly — see specs/01-extension-spec.md, "Messaging contract").
//
// Loaded as an ES module (manifest.json declares background.type =
// "module"), which Chrome's MV3 service worker and Firefox's MV3 event
// page both support — this lets one background.js work unmodified on both
// browsers instead of needing importScripts() (a worker-only API Firefox's
// event page context doesn't have).

const NATIVE_HOST_NAME = "com.erickson558.ytdlx";

/**
 * Holds the current native-messaging Port, reconnecting lazily. A
 * long-lived Port (rather than one-shot sendNativeMessage calls) is
 * required because the native host streams download.progress messages
 * back — a request/response API can't do that.
 *
 * The MV3 background service worker can be suspended by the browser after
 * ~30s of inactivity, which silently drops any open Port. Callers must not
 * cache the return value across turns of the event loop; always call
 * getPort() again right before use.
 */
let currentPort = null;

// Callers register here (see onNativeHostError) to be told when the port
// drops with an error -- e.g. the popup is waiting on a specific
// requestId and would otherwise hang forever with no signal at all if the
// native host was never reachable in the first place (missing/misconfigured
// manifest, app not installed, etc.). One port can be shared across
// several in-flight requests, so this is a plain list of listeners rather
// than a per-call callback.
const disconnectListeners = [];

function getPort(onMessage) {
  if (currentPort) return currentPort;

  currentPort = chrome.runtime.connectNative(NATIVE_HOST_NAME);
  currentPort.onMessage.addListener(onMessage);
  currentPort.onDisconnect.addListener(() => {
    // chrome.runtime.lastError is set here if the native host manifest is
    // missing/misconfigured (e.g. allowed_origins doesn't include this
    // extension's id) — surfacing it helps debug that class of silent
    // failure instead of the request just vanishing.
    const err = chrome.runtime.lastError;
    currentPort = null;
    if (err) {
      console.warn("[ytdlx] native host disconnected:", err.message);
      disconnectListeners.forEach((listener) => listener(err));
    }
  });

  return currentPort;
}

function onNativeHostError(listener) {
  disconnectListeners.push(listener);
}

function sendToNativeHost(message, onMessage) {
  const port = getPort(onMessage);
  port.postMessage(message);
}

export { sendToNativeHost, onNativeHostError, NATIVE_HOST_NAME };
