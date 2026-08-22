import { localizeDocument, setLanguageOverride } from "../lib/i18n.js";

await localizeDocument();

const select = document.getElementById("language");
const { language } = await chrome.storage.sync.get("language");
select.value = language || "";

select.addEventListener("change", async () => {
  await setLanguageOverride(select.value || null);
});
