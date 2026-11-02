import {useCallback, useEffect, useState} from "react";
import {useTranslation} from "react-i18next";
import {get, post} from "./api";
import LabPanel from "./LabPanel.jsx";

const STATES = {nurse: ["waiting", "vitals", "observation"], doctor: ["vitals", "in_consult", "observation", "done"]};

export default function Ward({role}) {
  const {t, i18n} = useTranslation();
  const [tab, setTab] = useState("patients");
  const [me, setMe] = useState(null);
  const [rows, setRows] = useState([]);
  const [adm, setAdm] = useState([]);
  const [mine, setMine] = useState(false);
  const [hist, setHist] = useState(null);
  const [lab, setLab] = useState(null);
  const [gc, setGc] = useState([]);
  const [beds, setBeds] = useState([]);
  const [form, setForm] = useState({});
  const [err, setErr] = useState("");

  const dn = d => [d["name_" + i18n.language], i18n.language === "ks" && d.name_ur, d.name_en].find(Boolean);
  const load = useCallback(async () => {
    const [p, a, g, b] = await Promise.all([get("/api/staff/patients" + (mine ? "?mine=1" : ""), true), get("/api/staff/admissions", true), get("/api/staff/golden-cards", true), get("/api/staff/beds/free", true)]);
    if (p.status === 200) setRows(p.data);
    if (a.status === 200) setAdm(a.data);
    if (g.status === 200) setGc(g.data);
    if (b.status === 200) setBeds(b.data);
    setErr(p.status === 403 ? t("noDept") : "");
  }, [mine, t]);

  useEffect(() => { get("/api/staff/profile", true).then(r => r.status === 200 && setMe(r.data)); }, []);
  useEffect(() => {
    load();
    const i = setInterval(load, 15000);
    return () => clearInterval(i);
  }, [load]);

  const act = async (url, body) => {
    const r = await post(url, body, true);
    setErr(r.status >= 400 ? t("badInput") : "");
    await load();
    return r;
  };
  const f = (id, k) => (form[id] || {})[k] || "";
  const setF = (id, k, v) => setForm({...form, [id]: {...(form[id] || {}), [k]: v}});
  const showHist = async uid => {
    const r = await get("/api/staff/patients/history/" + uid, true);
    if (r.status === 200) setHist({uid, rows: r.data});
  };
  const syms = s => s.map(k => t("sym." + k)).join("، ");

  return (
    <div className="ward">
      {me && me.department && <p>{t("deptLabel")}: <strong>{dn(me.department)}</strong> {me.is_head && <span className="badge">{t("headBadge")}</span>}</p>}
      <div className="tabs" role="tablist">
        {["patients", "admissions", "golden"].map(k => (
          <button key={k} role="tab" aria-selected={tab === k} className={tab === k ? "tab on" : "tab"} onClick={() => setTab(k)}>
            {t({patients: "tabPatients", admissions: "tabAdmissions", golden: "tabGolden"}[k])}
          </button>
        ))}
      </div>
      {err && <p role="alert" className="err">{err}</p>}

      {tab === "patients" && <>
        {role === "nurse" && <label className="row"><input type="checkbox" checked={mine} onChange={e => setMine(e.target.checked)} />{t("mine")}</label>}
        {!rows.length && <p>{t("none")}</p>}
        {rows.map(p => (
          <article key={p.id} className={"card" + (p.kind === "emergency" ? " emerg" : "")}>
            <h3>
              {p.kind === "emergency" && <span className="badge red">P{p.priority} · {t(p.category)}</span>} {p.name}
              <small> · {p.age} · {p.patient_uid} · #{p.token_no}</small>
            </h3>
            <p>{syms(p.symptoms)}</p>
            <p>{t("state." + p.state)}{p.nurse && ` · ${t("nurseLabel")}: ${p.nurse}`}{p.admission && ` · ${t("adm." + p.admission.status)}`}</p>
            {p.state !== "admitted" && (
              <div className="row">
                <select value={f(p.id, "st")} onChange={e => setF(p.id, "st", e.target.value)} aria-label={t("setStatus")}>
                  <option value="">{t("setStatus")}</option>
                  {STATES[role].map(s => <option key={s} value={s}>{t("state." + s)}</option>)}
                </select>
                <input value={f(p.id, "note")} onChange={e => setF(p.id, "note", e.target.value)} placeholder={t("note")} maxLength={200} />
                <button disabled={!f(p.id, "st")} onClick={() => act(`/api/staff/patients/${p.id}/status`, {status: f(p.id, "st"), note: f(p.id, "note")}).then(() => setF(p.id, "st", ""))}>{t("save")}</button>
              </div>
            )}
            <div className="row">
              {role === "nurse" && <button onClick={() => act(`/api/staff/patients/${p.id}/claim`)}>{t("claim")}</button>}
              <button onClick={() => setLab(p)}>{t("testsAndFollow")}</button>
              {role === "doctor" && <button onClick={() => showHist(p.patient_uid)}>{t("history")}</button>}
              {role === "doctor" && (!p.admission || ["rejected", "discharged"].includes(p.admission.status)) && (
                <>
                  <input value={f(p.id, "reason")} onChange={e => setF(p.id, "reason", e.target.value)} placeholder={t("reason")} maxLength={200} />
                  <button disabled={f(p.id, "reason").length < 3} onClick={() => act(`/api/staff/patients/${p.id}/admit-request`, {reason: f(p.id, "reason")}).then(() => setF(p.id, "reason", ""))}>{t("requestAdmit")}</button>
                </>
              )}
            </div>
          </article>
        ))}
        {lab && <LabPanel role={role} p={lab} onClose={() => setLab(null)} />}
        {hist && (
          <aside className="card">
            <h3>{t("history")} · {hist.uid}</h3>
            {hist.rows.map((h, i) => <p key={i}>{new Date(h.date).toLocaleDateString(i18n.language)} · {syms(h.symptoms)} · {t("state." + h.state)}</p>)}
            <button onClick={() => setHist(null)}>{t("close")}</button>
          </aside>
        )}
      </>}

      {tab === "golden" && <>
        {!gc.length && <p>{t("none")}</p>}
        {gc.map(g => (
          <article key={g.id} className="card">
            <h3>{g.name}<small> · {g.patient_uid}</small></h3>
            <p dir="ltr"><strong>{g.number}</strong> {g.holder && `· ${g.holder}`}</p>
            <div className="row">
              <button onClick={() => act(`/api/staff/golden-cards/${g.id}/decide`, {action: "verify"})}>{t("verifyCard")}</button>
              <button className="danger" onClick={() => act(`/api/staff/golden-cards/${g.id}/decide`, {action: "reject"})}>{t("reject")}</button>
            </div>
          </article>
        ))}
      </>}

      {tab === "admissions" && <>
        {!adm.length && <p>{t("none")}</p>}
        {adm.map(a => (
          <article key={a.id} className="card">
            <h3>{a.patient.name}<small> · {a.patient.age} · {a.patient.uid}</small></h3>
            <p>{a.reason} · {a.requested_by}</p>
            <p><strong>{t("adm." + a.status)}{a.ward && ` · ${a.ward}`}</strong></p>
            {role === "doctor" && me && a.status === "requested" && me.is_head && (
              <div className="row">
                <select value={f("a" + a.id, "bed")} onChange={e => setF("a" + a.id, "bed", e.target.value)} aria-label={t("bedLabel")}>
                  <option value="">{t("bedLabel")}</option>
                  {beds.map(b => <option key={b.id} value={b.id}>{b.label}</option>)}
                </select>
                <input value={f("a" + a.id, "ward")} onChange={e => setF("a" + a.id, "ward", e.target.value)} placeholder={t("wardName")} maxLength={40} />
                <button disabled={!f("a" + a.id, "ward") && !f("a" + a.id, "bed")} onClick={() => act(`/api/staff/admissions/${a.id}/decide`, {action: "admit", ward: f("a" + a.id, "ward"), bed: f("a" + a.id, "bed") || undefined})}>{t("admit")}</button>
                <button className="danger" onClick={() => act(`/api/staff/admissions/${a.id}/decide`, {action: "reject"})}>{t("reject")}</button>
              </div>
            )}
            {role === "doctor" && a.status === "admitted" && <button onClick={() => act(`/api/staff/admissions/${a.id}/discharge`)}>{t("discharge")}</button>}
          </article>
        ))}
      </>}
    </div>
  );
}
