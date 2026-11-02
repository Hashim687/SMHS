import {useEffect, useRef, useState} from "react";
import {get} from "./api";
import {listOf, money, when} from "./ui.js";

function useCount(n) {
  const [v, setV] = useState(0);
  const raf = useRef();
  useEffect(() => {
    const t0 = performance.now();
    const step = t => { const p = Math.min(1, (t - t0) / 700); setV(n * (1 - Math.pow(1 - p, 3))); if (p < 1) raf.current = requestAnimationFrame(step); };
    raf.current = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf.current);
  }, [n]);
  return Math.round(v);
}
const Kpi = ({icon, label, value, sub, fmt = x => x.toLocaleString("en-IN"), tone, onClick}) => {
  const v = useCount(value);
  return <button type="button" className={"kpi " + (tone || "")} onClick={onClick}><span className="kicon">{icon}</span><span className="kval">{fmt(v)}</span><span className="klab">{label}</span>{sub && <small>{sub}</small>}</button>;
};

export default function Dashboard({go}) {
  const [d, setD] = useState(null);
  const [hov, setHov] = useState(null);
  useEffect(() => {
    (async () => {
      const A = u => get(u, true);
      const [us, de, be, am, lb, nt, tx] = await Promise.all([A("/api/admin/users/?limit=500"), A("/api/admin/departments/?limit=500"), A("/api/admin/beds/?limit=500"), A("/api/staff/ambulances/?limit=500"), A("/api/admin/lab-tests/?limit=500"), A("/api/admin/notifications/?limit=200"), A("/api/admin/transactions")]);
      setD({users: listOf(us), depts: listOf(de), beds: listOf(be), amb: listOf(am), labs: listOf(lb), notes: listOf(nt), tx: tx.status === 200 ? tx.data : {totals: [], rows: [], feedback: {}}});
    })();
  }, []);
  if (!d) return <div className="kpis">{[0, 1, 2, 3, 4, 5].map(i => <div key={i} className="kpi"><span className="skel tall" /></div>)}</div>;

  const staff = d.users.filter(u => u.role !== "patient");
  const revenue = d.tx.totals.reduce((s, x) => s + Number(x.sum), 0);
  const paid = d.tx.totals.reduce((s, x) => s + x.count, 0);
  const roles = ["doctor", "nurse", "lab", "reception", "cashier", "admin"].map(r => [r, staff.filter(u => u.role === r).length]);
  const maxRole = Math.max(1, ...roles.map(r => r[1]));
  const days = [...Array(7)].map((_, i) => { const x = new Date(); x.setDate(x.getDate() - (6 - i)); return x.toDateString(); });
  const series = days.map(k => d.tx.rows.filter(p => new Date(p.at).toDateString() === k).reduce((s, p) => s + Number(p.amount), 0));
  const maxS = Math.max(1, ...series);
  const ok = d.notes.filter(n => n.status === "sent").length, bad = d.notes.filter(n => n.status === "failed").length, wait = d.notes.filter(n => n.status === "pending").length;
  const amb = d.amb.filter(a => a.status === "available").length;
  const hour = new Date().getHours();

  return (
    <div className="dash">
      <div className="welcome"><div><h2>{hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening"} 👋</h2><p>Here is what is happening at SMHS today.</p></div>
        <div className="qa"><button type="button" onClick={() => go("directory")}>＋ Add staff</button><button type="button" className="ghost light" onClick={() => go("departments")}>Departments</button><button type="button" className="ghost light" onClick={() => go("reports")}>Reports</button></div></div>
      <div className="kpis">
        <Kpi icon="💰" label="Revenue collected" value={revenue} fmt={money} sub={`${paid} payments`} tone="k1" onClick={() => go("reports")} />
        <Kpi icon="🩺" label="Active staff" value={staff.filter(u => u.is_active).length} sub={`${staff.length} total`} tone="k2" onClick={() => go("directory")} />
        <Kpi icon="🏥" label="Departments" value={d.depts.filter(x => x.is_active).length} sub={`${d.depts.length} total`} tone="k3" onClick={() => go("departments")} />
        <Kpi icon="🛏️" label="Beds" value={d.beds.filter(b => b.is_active).length} tone="k4" onClick={() => go("departments")} />
        <Kpi icon="🚑" label="Ambulances free" value={amb} sub={`of ${d.amb.length}`} tone="k5" onClick={() => go("departments")} />
        <Kpi icon="🧪" label="Lab tests offered" value={d.labs.filter(x => x.is_active).length} tone="k6" onClick={() => go("pricing")} />
      </div>
      <div className="dgrid">
        <section className="panel">
          <div className="phead"><div><h3>Revenue · last 7 days</h3><p className="desc">{hov === null ? "Hover a bar to see the amount" : `${days[hov].slice(0, 10)} — ${money(series[hov])}`}</p></div></div>
          <svg viewBox="0 0 420 180" className="bars" role="img" aria-label="Revenue last 7 days" onMouseLeave={() => setHov(null)}>
            {series.map((v, i) => { const h = Math.max(3, (v / maxS) * 130); return (
              <g key={i} onMouseEnter={() => setHov(i)} onClick={() => setHov(i)}>
                <rect x={i * 58 + 14} y={150 - h} width="38" height={h} rx="8" className={hov === i ? "bar hot" : "bar"} />
                <text x={i * 58 + 33} y="170" textAnchor="middle" className="axis">{days[i].slice(0, 3)}</text>
              </g>); })}
          </svg>
        </section>
        <section className="panel">
          <div className="phead"><div><h3>Staff by role</h3></div></div>
          <div className="hbars">{roles.map(([r, n]) => <div key={r} className="hb"><span>{r}</span><div><i style={{width: (n / maxRole) * 100 + "%"}} className={"t-bg-" + r} /></div><b>{n}</b></div>)}</div>
        </section>
        <section className="panel">
          <div className="phead"><div><h3>Messages (SMS)</h3><p className="desc">Last {d.notes.length} notifications</p></div><button type="button" className="mini ghost" onClick={() => go("notifications")}>View log</button></div>
          <div className="msgs"><div className="m ok"><b>{ok}</b>sent</div><div className="m wait"><b>{wait}</b>pending</div><div className="m bad"><b>{bad}</b>failed</div></div>
          {(bad > 0 || wait > 0) && <p className="warn">⚠️ Some messages did not go out. Patients will not receive OTP/SMS until an SMS provider is connected in the server settings.</p>}
        </section>
        <section className="panel">
          <div className="phead"><div><h3>Recent payments</h3><p className="desc">★ {d.tx.feedback.average ?? "–"} patient rating ({d.tx.feedback.count || 0})</p></div></div>
          <ul className="feed">{d.tx.rows.slice(0, 6).map(p => <li key={p.id}><span className={"tag t-" + p.method}>{p.method}</span><span dir="ltr">{p.patient_uid}</span><small>{p.kind} · {when(p.at)}</small><b>{money(p.amount)}</b></li>)}{!d.tx.rows.length && <li className="muted">No payments yet.</li>}</ul>
        </section>
      </div>
    </div>
  );
}
