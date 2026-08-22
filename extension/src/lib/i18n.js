// Thin wrapper over chrome.i18n so popup/options code doesn't call the raw
// API directly in more than one place. See specs/04-i18n-spec.md for the
// fallback chain (requested locale -> en -> the literal key).
//
// chrome.i18n.getMessage() always follows the *browser's* UI language and
// offers no way to force a different one at runtime, but the options page
// lets a user pick a language independent of their browser's locale. To
// support that override, a chosen locale's messages.json is fetched and
// read directly instead of going through chrome.i18n for that call.
let overrideMessages = null;
let overrideLoadPromise = null;

async function loadOverride() {
  if (overrideLoadPromise) return overrideLoadPromise;
  overrideLoadPromise = (async () => {
    const { language } = await chrome.storage.sync.get("language");
    if (!language) return;
    try {
      const url = chrome.runtime.getURL(`_locales/${language}/messages.json`);
      const response = await fetch(url);
      const data = await response.json();
      overrideMessages = Object.fromEntries(
        Object.entries(data).map(([key, entry]) => [key, entry.message])
      );
    } catch (err) {
      // Missing/invalid locale file: fall back to chrome.i18n silently,
      // per the fallback chain in specs/04-i18n-spec.md.
      overrideMessages = null;
    }
  })();
  return overrideLoadPromise;
}

export function t(key, substitutions) {
  if (overrideMessages && overrideMessages[key]) return overrideMessages[key];
  return chrome.i18n.getMessage(key, substitutions) || key;
}

/** Replaces every element with a data-i18n="key" attribute with t(key). */
export async function localizeDocument(root = document) {
  await loadOverride();
  root.querySelectorAll("[data-i18n]").forEach((el) => {
    el.textContent = t(el.getAttribute("data-i18n"));
  });
}

/** Re-reads the stored language override and re-localizes. Used by the
 * options page immediately after the user changes the language select. */
export async function setLanguageOverride(language, root = document) {
  if (language) {
    await chrome.storage.sync.set({ language });
  } else {
    await chrome.storage.sync.remove("language");
  }
  overrideMessages = null;
  overrideLoadPromise = null;
  await localizeDocument(root);
}
