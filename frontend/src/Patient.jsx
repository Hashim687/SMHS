import {useEffect, useState} from "react";
import {useTranslation} from "react-i18next";
import {get, post} from "./api";
import Portal from "./Portal.jsx";
import Stepper from "./Stepper.jsx";
import {pick} from "./util";
import {canSpeak, speak, stop} from "./voice";

const loadRzp = () => new Promise((ok, no) => {
  if (window.Razorpay) return ok();
  const s = document.createElement("script");
  s.src = "https://checkout.razorpay.com/v1/checkout.js";
  s.onload = ok;
  s.onerror = no;
  document.body.appendChild(s);
});

const blank = {name: "", phone: "", age: "", sex: "m"};

export default function Patient() {
  const {t, i18n} = useTranslation();
  const L = i18n.language;
  const [step, setStep] = useState("home");
  const [kind, setKind] = useState("opd");
  const [f, setF] = useState(blank);
  const [prices, setPrices] = useState({});
  const [order, setOrder] = useState(null);
  const [syms, setSyms] = useState([]);
  const [sel, setSel] = useState([]);
  const [res, setRes] = useState(null);
  const [err, setErr] = useState("");
  const [info, setInfo] = useState({beds: [], amb: 0});
  const [voice, setVoice] = useState(sessionStorage.getItem("voice") === "1");
  const [h, setH] = useState({uid: "", phone: "", code: "", token: "", visits: [], ref: ""});
  const set = k => e => setF({...f, [k]: e.target.value});
  const setHh = k => e => setH({...h, [k]: e.target.value});

  useEffect(() => {
    get("/api/public/prices").then(r => setPrices(r.data));
    get("/api/public/symptoms").then(r => Array.isArray(r.data) && setSyms(r.data));
    Promise.all([get("/api/public/beds"), get("/api/public/ambulances")]).then(([b, a]) =>
      setInfo({beds: Array.isArray(b.data) ? b.data : [], amb: Array.isArray(a.data) ? a.data.filter(x => x.status === "available").length : 0}));
  }, []);

  const say = () => speak(t("voice." + step, {dept: res && res.department ? pick(res.department, L) : "", n: res ? res.token_no : ""}), L);
  useEffect(() => { if (voice) say(); else stop(); }, [voice, step, L, res]);
  const toggleVoice = () => { const v = !voice; sessionStorage.setItem("voice", v ? "1" : "0"); setVoice(v); };

  const start = k => { setKind(k); setStep("form"); setErr(""); };
  const create = async e => {
    e.preventDefault();
    const r = await post("/api/public/tickets", {...f, age: Number(f.age), kind, language: L});
    if (r.status === 201) { setOrder(r.data); setStep("pay"); setErr(""); } else setErr(t(r.status === 503 ? "unavailable" : "badInput"));
  };
  const verify = async (pid, sig) => {
    const r = await post(`/api/public/tickets/${order.ref}/verify`, {razorpay_payment_id: pid, razorpay_signature: sig});
    if (r.status === 200) { setRes(r.data); setStep("sym"); setErr(""); } else setErr(t("payFail"));
  };
  const pay = async () => {
    if (order.mock) return verify(order.mock_payment_id, order.mock_signature);
    try {
      await loadRzp();
      new window.Razorpay({key: order.key_id, order_id: order.order_id, amount: order.amount, currency: "INR", name: t("app"),
        prefill: {name: f.name, contact: f.phone}, handler: r => verify(r.razorpay_payment_id, r.razorpay_signature)}).open();
    } catch { setErr(t("unavailable")); }
  };
  const toggle = k => setSel(sel.includes(k) ? sel.filter(x => x !== k) : [...sel, k]);
  const submit = async () => {
    const r = await post(`/api/public/tickets/${order.ref}/symptoms`, {symptoms: sel});
    if (r.status === 200) { setRes(r.data); setStep("done"); setErr(""); } else setErr(t("badInput"));
  };
  useEffect(() => {
    if (step !== "done" || !order) return;
    const i = setInterval(async () => {
      const r = await get(`/api/public/tickets/${order.ref}`);
      if (r.status === 200) setRes(r.data);
    }, 15000);
    return () => clearInterval(i);
  }, [step, order]);
  const reset = () => { setF(blank); setSel([]); setOrder(null); setRes(null); setH({uid: "", phone: "", code: "", token: "", visits: [], ref: ""}); setStep("home"); setErr(""); };

  const otpReq = async e => {
    e.preventDefault();
    await post("/api/public/patient/otp/request", {uid: h.uid.trim(), phone: h.phone});
    setStep("hotp");
  };
  const otpVer = async e => {
    e.preventDefault();
    const r = await post("/api/public/patient/otp/verify", {uid: h.uid.trim(), phone: h.phone, code: h.code});
    if (r.status !== 200) return setErr(t("invalid"));
    const v = await fetch("/api/public/patient/history", {headers: {"X-Patient-Token": r.data.token}});
    setH({...h, token: r.data.token, visits: v.ok ? await v.json() : []});
    setErr("");
    setStep("hlist");
  };

  return (
    <>
      <Stepper step={step} />
      {canSpeak() && (
        <div className="row voice">
          <button type="button" aria-pressed={voice} className={"tile small" + (voice ? " on" : "")} onClick={toggleVoice}>🔊 {t("voiceOn")}</button>
          <button type="button" onClick={say}>▶ {t("listen")}</button>
        </div>
      )}
      {step === "home" && (
        <section>
          <h2>{t("home")}</h2>
          <button className="big action" onClick={() => start("opd")}>🩺 {t("opd")} {prices.opd && `₹${Number(prices.opd)}`}</button>
          <button className="big action danger" onClick={() => start("emergency")}>🚑 {t("emergency")} {prices.emergency && `₹${Number(prices.emergency)}`}</button>
          <button className="big action" onClick={() => { setStep("hreq"); setErr(""); }}>📋 {t("prevVisits")}</button>
          {(info.beds.length > 0 || info.amb > 0) && (
            <div className="info">
              {info.beds.length > 0 && <><strong>🛏️ {t("beds")}</strong>{info.beds.map(b => <p key={b.code}>{pick(b, L)}: {t("freeOf", {free: b.free, total: b.total})}</p>)}</>}
              <p>🚑 {t("ambAvail", {n: info.amb})}</p>
            </div>
          )}
        </section>
      )}
      {step === "form" && (
        <form onSubmit={create}>
          <h2>{t(kind)}</h2>
          <label>{t("name")}<input value={f.name} onChange={set("name")} minLength={2} maxLength={80} autoComplete="name" required /></label>
          <label>{t("phone")}<input value={f.phone} onChange={set("phone")} inputMode="numeric" pattern="[6-9][0-9]{9}" maxLength={10} autoComplete="tel" dir="ltr" required /></label>
          <label>{t("age")}<input value={f.age} onChange={set("age")} type="number" min="0" max="120" inputMode="numeric" required /></label>
          <label>{t("sex")}<select value={f.sex} onChange={set("sex")}>{["m", "f", "o"].map(x => <option key={x} value={x}>{t(x)}</option>)}</select></label>
          <button>{t("next")}</button>
        </form>
      )}
      {step === "pay" && order && (
        <section>
          <h2>{t("amount")}: ₹{order.amount / 100}</h2>
          <button className="big" onClick={pay}>💳 {t(order.mock ? "testPay" : "pay")}</button>
        </section>
      )}
      {step === "sym" && (
        <section>
          <p>{t("yourId")}: <strong dir="ltr">{res.patient_uid}</strong></p>
          <h2>{t("pickSym")}</h2>
          <div className="grid" role="group" aria-label={t("pickSym")}>
            {syms.map(s => (
              <button key={s.key} type="button" aria-pressed={sel.includes(s.key)} className={"tile" + (sel.includes(s.key) ? " on" : "")} onClick={() => toggle(s.key)}>
                <span aria-hidden="true">{s.icon}</span>{t("sym." + s.key)}
              </button>
            ))}
          </div>
          <button disabled={!sel.length} onClick={submit}>{t("find")}</button>
        </section>
      )}
      {step === "done" && res && (
        <section>
          <div className="success" aria-hidden="true">✓</div>
          {res.escalate && <p role="alert" className="err">⚠️ {t("advise")}</p>}
          <p>{t("yourId")}: <strong dir="ltr">{res.patient_uid}</strong></p>
          <h2>{t("goTo")}: {pick(res.department, L)}</h2>
          <p className="center">{t("tokenNo")}</p><div className="token" role="status">{res.token_no}</div>
          <p>{t("state." + res.state)}</p>
          {res.admission && <p role="status"><strong>{t("adm." + res.admission.status)}{res.admission.ward ? ` · ${res.admission.ward}` : ""}</strong></p>}
          {res.category && <p>{t("category")}: {t(res.category)} · {t("priority")} {res.priority}</p>}
          <Portal tref={order.ref} who={f} />
          <button onClick={reset}>{t("again")}</button>
        </section>
      )}
      {step === "hreq" && (
        <form onSubmit={otpReq}>
          <h2>{t("prevVisits")}</h2>
          <label>{t("yourId")}<input value={h.uid} onChange={setHh("uid")} dir="ltr" maxLength={16} required /></label>
          <label>{t("phone")}<input value={h.phone} onChange={setHh("phone")} inputMode="numeric" pattern="[6-9][0-9]{9}" maxLength={10} dir="ltr" required /></label>
          <button>{t("otpSend")}</button>
          <button type="button" onClick={reset}>{t("back")}</button>
        </form>
      )}
      {step === "hotp" && (
        <form onSubmit={otpVer}>
          <p>{t("otpSent")}</p>
          <input value={h.code} onChange={setHh("code")} inputMode="numeric" pattern="[0-9]{6}" maxLength={6} autoComplete="one-time-code" dir="ltr" required aria-label={t("otp")} />
          <button>{t("verify")}</button>
          <button type="button" onClick={reset}>{t("back")}</button>
        </form>
      )}
      {step === "hlist" && (
        <section>
          <h2>{t("prevVisits")}</h2>
          {!h.visits.length && <p>{t("none")}</p>}
          {h.visits.map(v => (
            <button key={v.ref} className="big action" onClick={() => { setH({...h, ref: v.ref}); setStep("visit"); }}>
              {new Date(v.date).toLocaleDateString(L)} · {t(v.kind)} · {v.department ? pick(v.department, L) : "—"}
            </button>
          ))}
          <button onClick={reset}>{t("back")}</button>
        </section>
      )}
      {step === "visit" && (
        <section>
          <Portal tref={h.ref} who={{name: "", phone: ""}} summary />
          <button onClick={() => setStep("hlist")}>{t("back")}</button>
        </section>
      )}
      {err && <p role="alert" className="err">{err}</p>}
    </>
  );
}
