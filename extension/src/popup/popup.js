import { localizeDocument } from "../lib/i18n.js";

await localizeDocument();

// Minimal status display for the currently active tab's most recent
// download request, if any. The background worker is the source of truth
// (see background.js, requestStatus map); this popup just polls it once on
// open rather than keeping a persistent connection, since MV3 popups are
// themselves short-lived.
async function refreshStatus() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab) return;
  // The popup doesn't track requestIds per tab in this minimal version; a
  // fuller queue view is a fast-follow (see specs/02-native-host-spec.md,
  // "queue.list" / "queue.snapshot" message types) once the tray/queue UI
  // lands on the backend side.
}

refreshStatus();
