import {useEffect, useState} from "react";
import {useTranslation} from "react-i18next";
import {post, setTokens} from "./api";
import Admin from "./Admin.jsx";
import Counter from "./Counter.jsx";
import Lab from "./Lab.jsx";
import Qr from "./Qr.jsx";
import Ward from "./Ward.jsx";
import {initials} from "./ui.js";

export default function Staff() {
  const {t} = useTranslation();
  const [step, setStep] = useState("login");
  const [f, setF] = useState({username: "", password: "", code: ""});
  const [mfa, setMfa] = useState("");
  const [sess, setSess] = useState(null);
  const [setup, setSetup] = useState(null);
  const [err, setErr] = useState("");
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    const f = () => out();
    window.addEventListener("session-expired", f);
    return () => window.removeEventListener("session-expired", f);
  }, []);
  const set = k => e => setF({...f, [k]: e.target.value});

  const done = d => {
    setTokens(d);
    setSess({...d, username: d.username || f.username});
    setErr("");
    setStep(d.enroll_required ? "enroll" : "home");
  };
  const bad = s => setErr(t(s === 423 ? "locked" : "invalid"));

  const login = async e => {
    e.preventDefault();
    setBusy(true);
    const r = await post("/api/auth/login", {username: f.username, password: f.password});
    setBusy(false);
    if (r.status !== 200) return bad(r.status);
    if (r.data.mfa_required) { setMfa(r.data.mfa_token); setStep("otp"); setErr(""); setF({...f, code: ""}); } else done(r.data);
  };
  const otp = async e => {
    e.preventDefault();
    const r = await post("/api/auth/otp", {mfa_token: mfa, code: f.code});
    r.status === 200 ? done(r.data) : bad(r.status);
  };
  const begin = async () => {
    const r = await post("/api/auth/2fa/setup", {}, true);
    if (r.status === 200) setSetup(r.data);
  };
  const confirm = async e => {
    e.preventDefault();
    const r = await post("/api/auth/2fa/confirm", {code: f.code}, true);
    r.status === 200 ? (setErr(""), setStep("home")) : bad(r.status);
  };
  const out = () => { setTokens(null); setSess(null); setSetup(null); setStep("login"); setF({username: "", password: "", code: ""}); };
  const gate = step !== "home" || !sess;

  return (
    <>
      {gate && (
        <div className="auth">
          <div className="authside">
            <div className="logo big"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round"><path d="M12 4v16M4 12h16" /></svg></div>
            <h2>Staff portal</h2>
            <p>Doctors, nurses, lab, reception and administrators sign in here.</p>
            <ul><li>🔒 Protected with two-factor authentication</li><li>📋 Every action is recorded in the audit log</li><li>⚡ Live queues, wards and reports</li></ul>
          </div>
          <div className="authbox">
            {step === "login" && (
              <form onSubmit={login}>
                <h2>{t("login")}</h2>
                <label>{t("username")}<input value={f.username} onChange={set("username")} autoComplete="username" required autoFocus /></label>
                <label>{t("password")}<span className="pw"><input type={show ? "text" : "password"} value={f.password} onChange={set("password")} autoComplete="current-password" required /><button type="button" className="iconbtn" onClick={() => setShow(s => !s)} aria-label="Show password">{show ? "🙈" : "👁️"}</button></span></label>
                <button disabled={busy}>{busy ? "Signing in…" : t("signIn")}</button>
              </form>
            )}
            {step === "otp" && (
              <form onSubmit={otp}>
                <h2>{t("otp")}</h2>
                <p className="desc">Open your authenticator app and enter the 6-digit code.</p>
                <input className="code" value={f.code} onChange={set("code")} inputMode="numeric" pattern="\d{6}" maxLength={6} autoComplete="one-time-code" required autoFocus aria-label={t("otp")} />
                <button>{t("verify")}</button>
              </form>
            )}
            {step === "enroll" && (
              <form onSubmit={confirm}>
                <h2>{t("enroll")}</h2>
                {!setup && <button type="button" onClick={begin}>{t("enroll")}</button>}
                {setup && <>
                  {setup.uri && <Qr uri={setup.uri} label={t("scanQr", {defaultValue: "Scan with Google Authenticator, Microsoft Authenticator or Authy"})} />}
                  <p>{t("secret")}</p>
                  <code dir="ltr">{setup.secret}</code>
                  <input className="code" value={f.code} onChange={set("code")} inputMode="numeric" pattern="\d{6}" maxLength={6} required aria-label={t("otp")} />
                  <button>{t("confirm")}</button>
                </>}
              </form>
            )}
            {err && <p role="alert" className="err">{err}</p>}
          </div>
        </div>
      )}
      {!gate && (
        <>
          <div className="sessionbar">
            <div className="avatar a-admin">{initials(sess.username)}</div>
            <div className="who"><strong>{t("welcome")}{sess.username ? `, ${sess.username}` : ""}</strong><small>{t("role")}: {t("roles." + sess.role)}</small></div>
            <button type="button" className="ghost" onClick={out}>⏻ {t("logout")}</button>
          </div>
          {err && <p role="alert" className="err">{err}</p>}
          {sess.role === "admin" && <Admin />}
          <div className="stage">
            {(sess.role === "doctor" || sess.role === "nurse") && <Ward role={sess.role} />}
            {sess.role === "lab" && <Lab />}
            {(sess.role === "reception" || sess.role === "cashier") && <Counter />}
          </div>
        </>
      )}
    </>
  );
}
