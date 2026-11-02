import {useCallback, useEffect, useState} from "react";
import {useTranslation} from "react-i18next";
import {get, openPdf, post} from "./api";
import {pick} from "./util";

export default function LabPanel({role, p, onClose}) {
  const {t, i18n} = useTranslation();
  const L = i18n.language;
  const [orders, setOrders] = useState([]);
  const [cat, setCat] = useState([]);
  const [sel, setSel] = useState([]);
  const [when, setWhen] = useState("");
  const [note, setNote] = useState("");
  const [mode, setMode] = useState("in_person");
  const [msg, setMsg] = useState("");
  const load = useCallback(async () => {
    const r = await get(`/api/staff/patients/${p.id}/lab`, true);
    if (r.status === 200) setOrders(r.data);
  }, [p.id]);
  useEffect(() => {
    load();
    if (role === "doctor") get("/api/staff/lab-catalog", true).then(r => r.status === 200 && setCat(r.data));
    const i = setInterval(load, 15000);
    return () => clearInterval(i);
  }, [load, role]);
  const tog = c => setSel(sel.includes(c) ? sel.filter(x => x !== c) : [...sel, c]);
  const order = async () => {
    const r = await post(`/api/staff/patients/${p.id}/lab-orders`, {tests: sel}, true);
    setMsg(r.status === 201 ? "" : t("badInput"));
    if (r.status === 201) { setSel([]); load(); }
  };
  const book = async () => {
    const r = await post(`/api/staff/patients/${p.id}/appointments`, {when, note, mode}, true);
    setMsg(r.status === 201 ? t("saved") : t("badInput"));
    if (r.status === 201) { setWhen(""); setNote(""); }
  };
  return (
    <aside className="card">
      <h3>{p.name} · {t("testsAndFollow")}</h3>
      {role === "doctor" && <>
        <div className="grid" role="group" aria-label={t("orderTests")}>
          {cat.map(c => (
            <button key={c.code} type="button" aria-pressed={sel.includes(c.code)} className={"tile small" + (sel.includes(c.code) ? " on" : "")} onClick={() => tog(c.code)}>
              {pick(c, L)}<small>₹{Number(c.price)}</small>
            </button>
          ))}
        </div>
        <button disabled={!sel.length} onClick={order}>{t("orderTests")}</button>
      </>}
      {orders.map(o => (
        <div key={o.id} className="item">
          <p><span className={"badge" + (o.paid ? "" : " red")}>{t(o.paid ? "paidTag" : "unpaidTag")}</span> ₹{Number(o.total)}</p>
          {o.items.map(i => (
            <p key={i.id}>{pick(i.test, L)} · {t("lstep." + i.step)}
              {i.status === "resulted" && <strong dir="ltr"> · {i.value ?? i.text} {i.unit} {i.flag && i.flag !== "N" && <span className="badge red">{i.flag}</span>}</strong>}
            </p>
          ))}
          {role === "doctor" && o.pdf_ready && <button onClick={() => openPdf(`/api/staff/lab-orders/${o.id}/report.pdf`)}>📄 {t("downloadPdf")}</button>}
        </div>
      ))}
      {role === "doctor" && (
        <div className="row">
          <input type="datetime-local" value={when} onChange={e => setWhen(e.target.value)} aria-label={t("when")} />
          <input value={note} onChange={e => setNote(e.target.value)} placeholder={t("note")} maxLength={200} />
          <select value={mode} onChange={e => setMode(e.target.value)} aria-label={t("mode.tele")}><option value="in_person">{t("mode.in_person")}</option><option value="tele">{t("mode.tele")}</option></select>
          <button disabled={!when} onClick={book}>{t("followUp")}</button>
        </div>
      )}
      {msg && <p role="status">{msg}</p>}
      <button onClick={onClose}>{t("close")}</button>
    </aside>
  );
}
