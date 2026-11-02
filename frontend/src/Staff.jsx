import {useEffect, useState} from "react";
import {useTranslation} from "react-i18next";
import {post, setTokens} from "./api";
import Admin from "./Admin.jsx";
import Counter from "./Counter.jsx";
import Lab from "./Lab.jsx";
import Qr from "./Qr.jsx";
import Ward from "./Ward.jsx";

export default function Staff() {
  const {t} = useTranslation();
  const [step, setStep] = useState("login");
  const [f, setF] = useState({username: "", password: "", code: ""});
  const [mfa, setMfa] = useState("");
  const [sess, setSess] = useState(null);
  const [setup, setSetup] = useState(null);
  const [err, setErr] = useState("");
  useEffect(() => {
    const f = () => out();
    window.addEventListener("session-expired", f);
    return () => window.removeEventListener("session-expired", f);
  }, []);
  const set = k => e => setF({...f, [k]: e.target.value});

  const done = d => {
    setTokens(d);
    setSess(d);
    setErr("");
    setStep(d.enroll_required ? "enroll" : "home");
  };
  const bad = s => setErr(t(s === 423 ? "locked" : "invalid"));

  const login = async e => {
    e.preventDefault();
    const r = await post("/api/auth/login", {username: f.username, password: f.password});
    if (r.status !== 200) return bad(r.status);
    if (r.data.mfa_required) { setMfa(r.data.mfa_token); setStep("otp"); setErr(""); } else done(r.data);
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

  return (
    <>
      <>
        {step === "login" && (
          <form onSubmit={login}>
            <h2>{t("login")}</h2>
            <label>{t("username")}<input value={f.username} onChange={set("username")} autoComplete="username" required /></label>
            <label>{t("password")}<input type="password" value={f.password} onChange={set("password")} autoComplete="current-password" required /></label>
            <button>{t("signIn")}</button>
          </form>
        )}
        {step === "otp" && (
          <form onSubmit={otp}>
            <h2>{t("otp")}</h2>
            <input value={f.code} onChange={set("code")} inputMode="numeric" pattern="\d{6}" maxLength={6} autoComplete="one-time-code" required aria-label={t("otp")} />
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
              <input value={f.code} onChange={set("code")} inputMode="numeric" pattern="\d{6}" maxLength={6} required aria-label={t("otp")} />
              <button>{t("confirm")}</button>
            </>}
          </form>
        )}
        {step === "home" && sess && (
          <section>
            <h2>{t("welcome")}</h2>
            <p>{t("role")}: {t("roles." + sess.role)}</p>
            <button onClick={out}>{t("logout")}</button>
          </section>
        )}
        {step === "home" && sess && (sess.role === "doctor" || sess.role === "nurse") && <Ward role={sess.role} />}
        {step === "home" && sess && sess.role === "lab" && <Lab />}
        {step === "home" && sess && sess.role === "admin" && <Admin />}
        {step === "home" && sess && (sess.role === "reception" || sess.role === "cashier") && <Counter />}
        {err && <p role="alert" className="err">{err}</p>}
      </>
    </>
  );
}
