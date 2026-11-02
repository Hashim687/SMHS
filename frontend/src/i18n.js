import i18n from "i18next";
import {initReactI18next} from "react-i18next";
import en from "./locales/en.json";
import ks from "./locales/ks.json";
import ur from "./locales/ur.json";

export const RTL = new Set(["ur", "ks"]);

export const applyLang = l => {
  document.documentElement.lang = l;
  document.documentElement.dir = RTL.has(l) ? "rtl" : "ltr";
  localStorage.setItem("lang", l);
};

const lng = localStorage.getItem("lang") || "en";
i18n.use(initReactI18next).init({
  resources: {en: {translation: en}, ur: {translation: ur}, ks: {translation: ks}},
  lng,
  fallbackLng: {ks: ["ur", "en"], default: ["en"]},
  interpolation: {escapeValue: false},
  react: {bindI18nStore: "added"}
});
applyLang(lng);

const overrides = async l => {
  try {
    const r = await fetch("/api/public/translations/" + l);
    if (!r.ok) return;
    Object.entries(await r.json()).forEach(([k, v]) => i18n.addResource(l, "translation", k, v));
  } catch {}
};
overrides(lng);
if (lng === "ks") overrides("ur");
i18n.on("languageChanged", l => { overrides(l); if (l === "ks") overrides("ur"); });
export default i18n;
