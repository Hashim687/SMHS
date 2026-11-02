import {useCallback, useEffect, useMemo, useState} from "react";
import {del, get, patch, post} from "./api";
import Modal from "./Modal.jsx";
import {useToast} from "./Toast.jsx";
import {errText, initials, listOf} from "./ui.js";

const ROLES = ["doctor", "nurse", "lab", "reception", "cashier", "admin"];
const ICON = {doctor: "🩺", nurse: "💉", lab: "🧪", reception: "🛎️", cashier: "💳", admin: "🛡️"};
const blank = {username: "", first_name: "", last_name: "", role: "doctor", staff_id: "", phone: "", password: "", is_active: true};

export default function Directory() {
  const toast = useToast();
  const [users, setUsers] = useState(null);
  const [depts, setDepts] = useState([]);
  const [asg, setAsg] = useState([]);
  const [role, setRole] = useState("all");
  const [dep, setDep] = useState("");
  const [q, setQ] = useState("");
  const [form, setForm] = useState(null);
  const [errs, setErrs] = useState({});
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    const [u, d, a] = await Promise.all([get("/api/admin/users/?limit=500", true), get("/api/admin/departments/?limit=500", true), get("/api/admin/staff-assignments/?limit=500", true)]);
    setUsers(listOf(u).filter(x => x.role !== "patient"));
    setDepts(listOf(d));
    setAsg(listOf(a));
  }, []);
  useEffect(() => { load(); }, [load]);

  const deptsOf = id => asg.filter(a => a.user === id).map(a => depts.find(d => d.id === a.department)).filter(Boolean);
  const counts = useMemo(() => Object.fromEntries(ROLES.map(r => [r, (users || []).filter(u => u.role === r).length])), [users]);
  const list = useMemo(() => (users || []).filter(u => {
    if (role !== "all" && u.role !== role) return false;
    if (dep && !asg.some(a => a.user === u.id && String(a.department) === dep)) return false;
    const s = q.trim().toLowerCase();
    return !s || [u.username, u.first_name, u.last_name, u.staff_id, u.phone].join(" ").toLowerCase().includes(s);
  }).sort((a, b) => (a.first_name || a.username).localeCompare(b.first_name || b.username)), [users, role, dep, q, asg]);

  const open = u => { setErrs({}); setForm(u ? {id: u.id, d: {...blank, ...u, password: ""}, depts: deptsOf(u.id).map(x => x.id)} : {id: null, d: {...blank}, depts: []}); };
  const setd = (k, v) => setForm(f => ({...f, d: {...f.d, [k]: v}}));
  const toggleDept = id => setForm(f => ({...f, depts: f.depts.includes(id) ? f.depts.filter(x => x !== id) : [...f.depts, id]}));

  const save = async e => {
    e.preventDefault();
    const body = {...form.d};
    ["id", "totp_enabled", "email", "language"].forEach(k => delete body[k]);
    if (!body.password) delete body.password;
    setBusy(true);
    const r = form.id ? await patch(`/api/admin/users/${form.id}/`, body, true) : await post("/api/admin/users/", body, true);
    if (r.status >= 400) { setBusy(false); setErrs(typeof r.data === "object" ? r.data : {}); return toast(errText(r.data), "err"); }
    const uid = r.data.id;
    const have = asg.filter(a => a.user === uid);
    for (const a of have) if (!form.depts.includes(a.department)) await del(`/api/admin/staff-assignments/${a.id}/`, true);
    for (const d of form.depts) if (!have.some(a => a.department === d)) await post("/api/admin/staff-assignments/", {user: uid, department: d}, true);
    setBusy(false);
    toast(form.id ? "Staff member updated" : "Staff member added");
    setForm(null);
    load();
  };
  const flip = async u => { const r = await patch(`/api/admin/users/${u.id}/`, {is_active: !u.is_active}, true); r.status < 400 ? (toast(u.is_active ? `${u.username} deactivated` : `${u.username} activated`), load()) : toast(errText(r.data), "err"); };
  const reset2fa = async u => { const r = await post(`/api/admin/users/${u.id}/reset_2fa/`, {}, true); r.status < 400 ? (toast("2FA reset. They will set it up again at next login."), load()) : toast(errText(r.data), "err"); };

  return (
    <section className="panel">
      <div className="phead">
        <div><h3>Doctors &amp; staff<span className="count">{list.length}</span></h3><p className="desc">Everyone who can sign in to the hospital system, with their departments.</p></div>
        <div className="tools">
          <label className="search"><span>🔍</span><input value={q} onChange={e => setQ(e.target.value)} placeholder="Name, ID, phone…" aria-label="Search staff" /></label>
          <select value={dep} onChange={e => setDep(e.target.value)} aria-label="Department"><option value="">All departments</option>{depts.map(d => <option key={d.id} value={d.id}>{d.name_en}</option>)}</select>
          <button type="button" onClick={() => open(null)}>＋ Add staff</button>
        </div>
      </div>
      <div className="chips2" role="tablist">
        <button type="button" className={"chip2" + (role === "all" ? " on" : "")} onClick={() => setRole("all")}>All <b>{(users || []).length}</b></button>
        {ROLES.map(r => <button type="button" key={r} className={"chip2" + (role === r ? " on" : "")} onClick={() => setRole(r)}>{ICON[r]} {r} <b>{counts[r]}</b></button>)}
      </div>
      {users === null && <div className="cards">{[0, 1, 2].map(i => <div key={i} className="scard"><span className="skel tall" /></div>)}</div>}
      {users && !list.length && <div className="empty"><span>👩‍⚕️</span><p>No staff match these filters.</p><button type="button" onClick={() => open(null)}>＋ Add staff</button></div>}
      <div className="cards">
        {list.map(u => (
          <article key={u.id} className={"scard" + (u.is_active ? "" : " off")}>
            <div className="shead">
              <div className={"avatar a-" + u.role}>{initials(u.first_name ? `${u.first_name} ${u.last_name}` : u.username)}</div>
              <div className="who"><strong dir="auto">{[u.first_name, u.last_name].filter(Boolean).join(" ") || u.username}</strong><small>@{u.username}</small></div>
              <span className={"tag t-" + u.role}>{ICON[u.role]} {u.role}</span>
            </div>
            <dl className="meta">
              <div><dt>Staff ID</dt><dd>{u.staff_id || "—"}</dd></div>
              <div><dt>Phone</dt><dd dir="ltr">{u.phone || "—"}</dd></div>
              <div><dt>2FA</dt><dd>{u.totp_enabled ? "🔒 Enabled" : "⚠️ Not set"}</dd></div>
            </dl>
            <div className="dchips">{deptsOf(u.id).length ? deptsOf(u.id).map(d => <span key={d.id} className="dchip">{d.name_en}</span>) : <span className="muted">No department assigned</span>}</div>
            <div className="sfoot">
              <label className="switch" title={u.is_active ? "Active — click to deactivate" : "Inactive — click to activate"}><input type="checkbox" checked={u.is_active} onChange={() => flip(u)} /><span /></label>
              <div>
                <button type="button" className="mini" onClick={() => open(u)}>✏️ Edit</button>
                <button type="button" className="mini ghost" onClick={() => reset2fa(u)} title="Reset two-factor">2FA ↺</button>
              </div>
            </div>
          </article>
        ))}
      </div>

      {form && (
        <Modal title={form.id ? "Edit staff member" : "Add staff member"} onClose={() => setForm(null)} wide>
          <form onSubmit={save} className="mform">
            <div className="fgrid">
              {[["username", "Username", "text", !!form.id], ["first_name", "First name"], ["last_name", "Last name"], ["staff_id", "Staff ID"], ["phone", "Phone", "tel"], ["password", form.id ? "New password" : "Password", "password"]].map(([k, l, t = "text", dis]) => (
                <label key={k}><span>{l}</span><input type={t} value={form.d[k] ?? ""} onChange={e => setd(k, e.target.value)} disabled={dis} required={k === "username" || (k === "password" && !form.id)} autoComplete="off" placeholder={k === "password" && form.id ? "Leave blank to keep current" : ""} />{errs[k] && <em className="ferr">{[].concat(errs[k]).join(" ")}</em>}</label>
              ))}
              <label><span>Role</span><select value={form.d.role} onChange={e => setd("role", e.target.value)}>{ROLES.map(r => <option key={r} value={r}>{r}</option>)}</select></label>
              <label className="inline"><span>Active</span><span className="switch"><input type="checkbox" checked={!!form.d.is_active} onChange={e => setd("is_active", e.target.checked)} /><span /></span></label>
            </div>
            <div><span className="lbl">Departments</span>
              <div className="dchips pick">{depts.map(d => <button type="button" key={d.id} className={"dchip" + (form.depts.includes(d.id) ? " on" : "")} onClick={() => toggleDept(d.id)}>{form.depts.includes(d.id) ? "✓ " : ""}{d.name_en}</button>)}{!depts.length && <span className="muted">Create departments first.</span>}</div>
            </div>
            <div className="mfoot"><button type="button" className="ghost" onClick={() => setForm(null)}>Cancel</button><button disabled={busy}>{busy ? "Saving…" : "Save"}</button></div>
          </form>
        </Modal>
      )}
    </section>
  );
}
