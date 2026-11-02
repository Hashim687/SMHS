import {useEffect, useState} from "react";
import {useTranslation} from "react-i18next";
import {applyLang} from "./i18n";
import Patient from "./Patient.jsx";
import Staff from "./Staff.jsx";

const LANGS = [["en", "EN"], ["ur", "اردو"], ["ks", "كٲشُر"]];

const Logo = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" aria-hidden="true">
    <path d="M12 4v16M4 12h16" />
  </svg>
);

export default function App() {
  const {t, i18n} = useTranslation();
  const [h, setH] = useState(location.hash);
  const [scrolled, setScrolled] = useState(false);
  const [theme, setTheme] = useState(localStorage.getItem("theme") || "");
  useEffect(() => {
    const f = () => { setH(location.hash); scrollTo({top: 0}); };
    const s = () => setScrolled(scrollY > 400 ? 2 : scrollY > 8);
    addEventListener("hashchange", f);
    addEventListener("scroll", s, {passive: true});
    return () => { removeEventListener("hashchange", f); removeEventListener("scroll", s); };
  }, []);
  useEffect(() => {
    if (theme) document.documentElement.dataset.theme = theme;
    else delete document.documentElement.dataset.theme;
  }, [theme]);
  const dark = theme ? theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
  const flip = () => { const n = dark ? "light" : "dark"; localStorage.setItem("theme", n); setTheme(n); };
  const staff = h === "#/staff";
  const lang = l => { i18n.changeLanguage(l); applyLang(l); };
  return (
    <>
      <a className="skip" href="#main">Skip to content</a>
      <header className={scrolled ? "scrolled" : ""}>
        <div className="brand">
          <div className="logo"><Logo /></div>
          <h1>{t("app")}<small>{staff ? t("staffLink") : t("patientLink")}</small></h1>
        </div>
        <nav>
          <a className="pill" href={staff ? "#/" : "#/staff"}>{staff ? "🏥" : "🔐"} {t(staff ? "patientLink" : "staffLink")}</a>
          <div className="seg" role="group" aria-label={t("language")}>
            {LANGS.map(([k, n]) => <button key={k} type="button" className={i18n.language === k ? "on" : ""} aria-pressed={i18n.language === k} onClick={() => lang(k)}>{n}</button>)}
          </div>
          <button type="button" className="iconbtn" onClick={flip} aria-label="Toggle dark mode" title="Dark / light">{dark ? "☀️" : "🌙"}</button>
        </nav>
      </header>
      {!staff && (
        <div className="hero">
          <h2>{t("heroTitle", {defaultValue: "Fast, simple care for everyone"})}</h2>
          <p>{t("heroSub", {defaultValue: "Get your ticket, pay online and know exactly where to go. No queues, no confusion."})}</p>
          <div className="chips">
            <span className="chip"><span className="pulse" /> {t("heroOpen", {defaultValue: "Open 24 × 7"})}</span>
            <span className="chip">🌐 {t("heroLang", {defaultValue: "English · اردو · كٲشُر"})}</span>
            <span className="chip">🔊 {t("heroVoice", {defaultValue: "Voice guidance"})}</span>
          </div>
        </div>
      )}
      <main id="main">{staff ? <Staff /> : <Patient />}</main>
      <footer>🚑 {t("footEmerg", {defaultValue: "In a life-threatening emergency, call"})} <strong>112</strong></footer>
      {scrolled === 2 && <button className="totop" type="button" aria-label="Back to top" onClick={() => scrollTo({top: 0, behavior: "smooth"})}>↑</button>}
    </>
  );
}
