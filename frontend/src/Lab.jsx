import {useCallback, useEffect, useState} from "react";
import {useTranslation} from "react-i18next";
import {get, post} from "./api";
import {pick} from "./util";

export default function Lab() {
  const {t, i18n} = useTranslation();
  const L = i18n.language;
  const [tab, setTab] = useState("queue");
  const [q, setQ] = useState([]);
  const [ready, setReady] = useState([]);
  const [v, setV] = useState({});
  const [err, setErr] = useState("");
  const load = useCallback(async () => {
    const [a, b] = await Promise.all([get("/api/lab/queue", true), get("/api/lab/ready", true)]);
    if (a.status === 200) setQ(a.data);
    if (b.status === 200) setReady(b.data);
  }, []);
  useEffect(() => {
    load();
    const i = setInterval(load, 15000);
    return () => clearInterval(i);
  }, [load]);
  const act = async (url, body) => {
    const r = await post(url, body, true);
    setErr(r.status >= 400 ? t("badInput") : "");
    load();
  };
  const set = (id, k, x) => setV({...v, [id]: {...(v[id] || {}), [k]: x}});
  return (
    <div className="ward">
      <div className="tabs" role="tablist">
        {[["queue", "tabQueue"], ["ready", "tabReady"]].map(([k, l]) => <button key={k} role="tab" aria-selected={tab === k} className={tab === k ? "tab on" : "tab"} onClick={() => setTab(k)}>{t(l)}</button>)}
      </div>
      {err && <p role="alert" className="err">{err}</p>}
      {tab === "queue" && <>
        {!q.length && <p>{t("none")}</p>}
        {q.map(i => (
          <article key={i.id} className={"card" + (i.emergency ? " emerg" : "")}>
            <h3>{i.emergency && <span className="badge red">P{i.priority}</span>} {pick(i.test, L)}<small> · {i.name} · {i.patient_uid}</small></h3>
            {i.status === "ordered" && <button onClick={() => act(`/api/lab/items/${i.id}/collect`)}>{t("collect")}</button>}
            {i.status === "collected" && (
              <div className="row">
                <input type="number" step="any" value={(v[i.id] || {}).value || ""} onChange={e => set(i.id, "value", e.target.value)} placeholder={`${t("resultValue")} ${i.unit}`} dir="ltr" />
                <input value={(v[i.id] || {}).text || ""} onChange={e => set(i.id, "text", e.target.value)} placeholder={t("orText")} maxLength={200} />
                {i.ref && <small dir="ltr">{t("range")}: {i.ref}</small>}
                <button disabled={!((v[i.id] || {}).value || (v[i.id] || {}).text)} onClick={() => act(`/api/lab/items/${i.id}/result`, v[i.id])}>{t("saveResult")}</button>
              </div>
            )}
          </article>
        ))}
      </>}
      {tab === "ready" && <>
        {!ready.length && <p>{t("none")}</p>}
        {ready.map(o => (
          <article key={o.id} className="card">
            <h3>{o.name}<small> · {o.patient_uid}</small></h3>
            <button onClick={() => act(`/api/lab/orders/${o.id}/handover`)}>{t("handover")}</button>
          </article>
        ))}
      </>}
    </div>
  );
}
