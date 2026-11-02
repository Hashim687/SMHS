import {useCallback, useEffect, useState} from "react";
import {useTranslation} from "react-i18next";
import {get} from "./api";

export default function Reports({mode}) {
  const {t} = useTranslation();
  const [f, setF] = useState({from: "", to: "", method: ""});
  const [tx, setTx] = useState(null);
  const [rv, setRv] = useState(null);
  const [au, setAu] = useState([]);
  const [flt, setFlt] = useState("");
  const loadTx = useCallback(async () => {
    const qs = new URLSearchParams(Object.entries(f).filter(([, v]) => v)).toString();
    const r = await get("/api/admin/transactions?" + qs, true);
    if (r.status === 200) setTx(r.data);
  }, [f]);
  useEffect(() => {
    if (mode === "reports") loadTx();
    if (mode === "security") {
      get("/api/admin/self-review", true).then(r => r.status === 200 && setRv(r.data));
      get("/api/admin/audit/?limit=200", true).then(r => r.status === 200 && setAu(r.data.results));
    }
  }, [mode, loadTx]);
  const set = k => e => setF({...f, [k]: e.target.value});
  const when = x => new Date(x).toLocaleString();
  if (mode === "reports") return (
    <section className="crud">
      <h3>{t("admin.reports")}</h3>
      <div className="row">
        <input type="date" value={f.from} onChange={set("from")} aria-label="from" />
        <input type="date" value={f.to} onChange={set("to")} aria-label="to" />
        <select value={f.method} onChange={set("method")} aria-label="method"><option value="">all</option><option value="online">online</option><option value="cash">cash</option></select>
      </div>
      {tx && <>
        <p>{tx.totals.map(x => `${x.kind}/${x.method}: ${x.count} · ₹${x.sum}`).join("  |  ") || t("none")}</p>
        <p>★ {tx.feedback.average ?? "-"} ({tx.feedback.count})</p>
        <div className="scroll"><table><thead><tr><th>time</th><th>patient</th><th>kind</th><th>method</th><th>₹</th><th>by</th></tr></thead>
          <tbody>{tx.rows.map(p => <tr key={p.id}><td>{when(p.at)}</td><td dir="ltr">{p.patient_uid}</td><td>{p.kind}</td><td>{p.method}</td><td>{p.amount}</td><td>{p.by}</td></tr>)}</tbody></table></div>
      </>}
    </section>
  );
  return (
    <section className="crud">
      <h3>{t("admin.security")}</h3>
      {rv && <>
        <h4>{t("admin.review")}</h4>
        <ul className="plain">{rv.requirements.map(x => <li key={x.id}>{x.ok ? "✅" : "❌"} {x.text}{x.detail && !x.ok ? ` — ${x.detail}` : ""}</li>)}</ul>
        <h4>{t("admin.expert")}</h4>
        <ul className="plain">{rv.recommendations.map(x => <li key={x.name}><strong>{x.name}</strong> · {x.status} — {x.note}</li>)}</ul>
      </>}
      <h4>{t("admin.audit")}</h4>
      <input value={flt} onChange={e => setFlt(e.target.value)} placeholder="filter (action, path, ip)" aria-label="filter" />
      <div className="scroll"><table><thead><tr><th>time</th><th>user</th><th>action</th><th>path</th><th>status</th><th>ip</th></tr></thead>
        <tbody>{au.filter(a => !flt || [a.action, a.path, a.ip, a.detail].join(" ").includes(flt)).map(a => <tr key={a.id}><td>{when(a.at)}</td><td>{a.user ?? ""}</td><td>{a.action}</td><td dir="ltr">{a.method} {a.path}</td><td>{a.status ?? ""}</td><td dir="ltr">{a.ip}</td></tr>)}</tbody></table></div>
    </section>
  );
}
