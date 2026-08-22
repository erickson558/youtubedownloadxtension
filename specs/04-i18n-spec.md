# 04 — Internationalization Spec

Depends on [[00-project-spec]]. Implemented in `extension/_locales/*/messages.json`
(WebExtensions i18n) and `backend/ytdlx_backend/i18n/locales/*.json` (custom
JSON loader for the Python app).

## Supported locales

`es` and `en` are equal-priority primaries (the maintainer and the initial
audience are Spanish-speaking; `en` is the standard for OSS/GitHub
discoverability). `pt` and `fr` are additionally supported. `en` is always
the final fallback if a key is missing from every other requested locale.

Fallback chain: `requested locale → es/en (whichever is the browser/OS
default) → en → the literal key name` (a missing key must never render as a
blank string or crash the UI — showing the key itself is preferable, it is
visibly a bug rather than silently wrong).

## Two separate formats, one shared key vocabulary

The extension and the desktop app use different i18n mechanisms because they
run in different runtimes:

- Extension: native `chrome.i18n` / `_locales/<lang>/messages.json`
  (WebExtensions standard format, required for the `__MSG_x__` substitutions
  used in `manifest.json` itself, e.g. `__MSG_extName__`).
- Desktop app: a small JSON key→string loader
  (`backend/ytdlx_backend/i18n/translator.py`) reading
  `locales/<lang>.json` flat maps. A custom loader is used instead of
  stdlib `gettext` because `gettext` needs `.mo` compilation and
  locale-directory discovery that gets awkward inside a PyInstaller
  one-file frozen build; a flat JSON file bundled as PyInstaller `datas`
  is simpler and equally correct for this app's small string set.

Even though the file formats differ, the two locale sets should stay
*semantically* mirrored — the same string that appears in both, e.g. the
"Download" button label, is a separate key in each file (`downloadButton` in
`messages.json`, `download_button` in the Python JSON — snake_case there to
match Python convention) but a translator working on one should always check
whether the same string exists in the other.

## Minimum key set for the first milestone

- `extName`, `extDescription` (manifest substitutions)
- `downloadButton`, `donateButton`
- `optionsTitle`, `languageLabel`
- `firstRunDisclaimerTitle`, `firstRunDisclaimerBody` (canonical text from [[00-project-spec]])
- `downloadStarted`, `downloadComplete`, `downloadFailed`, `downloadCancelled`
- `chooseFolderPrompt`

## Related specs

[[00-project-spec]] · [[01-extension-spec]] · [[02-native-host-spec]]
