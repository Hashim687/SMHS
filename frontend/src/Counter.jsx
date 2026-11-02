import {useCallback, useEffect, useState} from "react";
import {useTranslation} from "react-i18next";
import {get, post} from "./api";
import {pick} from "./util";

const blank = {kind: "opd", name: "", phone: "", age: "", sex: "m"};

export default function Counter() {
  const {t, i18n} = useTranslation();
  const L = i18n.language;
  const [f, setF] = useState(blank);
  const [tk, setTk] = useState(null);
  const [syms, setSyms] = useState([]);
  const [sel, setSel] = useState([]);
  const [res, setRes] = useState(null);
  const [unpaid, setUnpaid] = useState([]);
  const [err, setErr] = useState("");
  const set = k => e => setF({...f, [k]: e.target.value});
  const load = useCallback(async () => {
    const r = await get("/api/staff/lab-orders/unpaid", true);
    if (r.status === 200) setUnpaid(r.data);
  }, []);
  useEffect(() => {
    load();
    get("/api/public/symptoms").then(r => Array.isArray(r.data) && setSyms(r.data));
    const i = setInterval(load, 15000);
    return () => clearInterval(i);
  }, [load]);
  const create = async e => {
    e.preventDefault();
    const r = await post("/api/staff/tickets/cash", {...f, age: Number(f.age), language: L}, true);
    if (r.status === 201) { setTk(r.data); setErr(""); } else setErr(t("badInput"));
  };
  const triage = async () => {
    const r = await post(`/api/public/tickets/${tk.ref}/symptoms`, {symptoms: sel});
    if (r.status === 200) { setRes(r.data); setErr(""); } else setErr(t("badInput"));
  };
  const reset = () => { setF(blank); setTk(null); setSel([]); setRes(null); };
  const cash = async id => {
    const r = await post(`/api/staff/lab-orders/${id}/cash`, {}, true);
    setErr(r.status === 200 ? "" : t("badInput"));
    load();
  };
  return (
    <div className="ward">
      <h2>{t("walkin")}</h2>
      {!tk && (
        <form onSubmit={create}>
          <label>{t("ticketType")}
            <select value={f.kind} onChange={set("kind")}><option value="opd">{t("opd")}</option><option value="emergency">{t("emergency")}</option></select>
          </label>
          <label>{t("name")}<input value={f.name} onChange={set("name")} minLength={2} maxLength={80} required /></label>
          <label>{t("phone")}<input value={f.phone} onChange={set("phone")} inputMode="numeric" pattern="[6-9][0-9]{9}" maxLength={10} dir="ltr" required /></label>
          <label>{t("age")}<input value={f.age} onChange={set("age")} type="number" min="0" max="120" required /></label>
          <label>{t("sex")}<select value={f.sex} onChange={set("sex")}>{["m", "f", "o"].map(x => <option key={x} value={x}>{t(x)}</option>)}</select></label>
          <button>{t("receive")}</button>
        </form>
      )}
      {tk && !res && (
        <section>
          <p>{t("yourId")}: <strong dir="ltr">{tk.patient_uid}</strong></p>
          <h3>{t("pickSym")}</h3>
          <div className="grid">
            {syms.map(s => <button key={s.key} type="button" aria-pressed={sel.includes(s.key)} className={"tile" + (sel.includes(s.key) ? " on" : "")} onClick={() => setSel(sel.includes(s.key) ? sel.filter(x => x !== s.key) : [...sel, s.key])}><span aria-hidden="true">{s.icon}</span>{t("sym." + s.key)}</button>)}
          </div>
          <button disabled={!sel.length} onClick={triage}>{t("find")}</button>
        </section>
      )}
      {res && (
        <section>
          {res.escalate && <p role="alert" className="err">⚠️ {t("advise")}</p>}
          <p>{t("yourId")}: <strong dir="ltr">{res.patient_uid}</strong></p>
          <h3>{t("goTo")}: {pick(res.department, L)}</h3>
          <p>{t("tokenNo")}: <strong>{res.token_no}</strong></p>
          <button onClick={reset}>{t("again")}</button>
        </section>
      )}
      <h2>{t("unpaidOrders")}</h2>
      {!unpaid.length && <p>{t("none")}</p>}
      {unpaid.map(o => (
        <article key={o.id} className="card">
          <h3>{o.name}<small> · {o.patient_uid} · ₹{Number(o.total)}</small></h3>
          <button onClick={() => cash(o.id)}>{t("receive")}</button>
        </article>
      ))}
      {err && <p role="alert" className="err">{err}</p>}
    </div>
  );
}
