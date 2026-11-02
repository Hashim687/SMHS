import {useCallback, useEffect, useMemo, useState} from "react";
import {del, get, patch, post} from "./api";
import Modal from "./Modal.jsx";
import {useToast} from "./Toast.jsx";
import {csvDownload, errText, human, when} from "./ui.js";

const PAGE = 10;
const DATES = ["created", "sent_at", "updated", "at"];

export default function Crud({title, desc, url, fields, pk = "id", create = true, canDel = false, ro = false, extra, cols}) {
  const toast = useToast();
  const [rows, setRows] = useState(null);
  const [opts, setOpts] = useState({});
  const [q, setQ] = useState("");
  const [sort, setSort] = useState({k: null, d: 1});
  const [page, setPage] = useState(0);
  const [form, setForm] = useState(null);
  const [errs, setErrs] = useState({});
  const [ask, setAsk] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    const r = await get(url + "/?limit=500", true);
    setRows(r.status === 200 ? (r.data.results || r.data) : []);
  }, [url]);
  useEffect(() => {
    load();
    fields.filter(f => f.src).forEach(async f => {
      const r = await get(f.src + "/?limit=500", true);
      if (r.status === 200) setOpts(o => ({...o, [f.k]: r.data.results || r.data}));
    });
  }, [load]);

  const lookup = (f, v) => { const o = (opts[f.k] || []).find(x => x.id === v); return o ? f.label(o) : ""; };
  const plain = (f, v) => {
    if (v === null || v === undefined || v === "") return "";
    if (f.src) return lookup(f, v);
    if (f.type === "checkbox") return v ? "active yes" : "inactive no";
    if (DATES.includes(f.k)) return when(v);
    return String(v);
  };
  const cell = (f, r) => {
    const v = r[f.k];
    if (f.type === "checkbox") {
      const lab = f.k === "totp_enabled" ? (v ? "Enabled" : "Not set") : (v ? "Active" : "Inactive");
      const click = !ro && !f.ro ? async () => { const x = await patch(`${url}/${r[pk]}/`, {[f.k]: !v}, true); x.status < 400 ? (toast(`${human(f.k)} updated`), load()) : toast(errText(x.data), "err"); } : undefined;
      return <button type="button" className={"spill " + (v ? "on" : "off")} onClick={click} disabled={!click} title={click ? "Click to toggle" : ""}>{lab}</button>;
    }
    const s = plain(f, v);
    if (!s) return <span className="muted">—</span>;
    if (f.choices) return <span className={"tag t-" + String(v).replace(/\W/g, "")}>{s}</span>;
    if (f.k === "status") return <span className={"tag t-" + s}>{s}</span>;
    if (["amount", "price"].includes(f.k)) return <b>₹{s}</b>;
    return <span dir="auto">{s}</span>;
  };

  const shown = cols ? fields.filter(f => cols.includes(f.k)) : fields.filter(f => f.type !== "password").slice(0, 7);
  const view = useMemo(() => {
    let l = rows || [];
    if (q.trim()) { const s = q.toLowerCase(); l = l.filter(r => fields.some(f => plain(f, r[f.k]).toLowerCase().includes(s))); }
    if (sort.k) {
      const f = fields.find(x => x.k === sort.k);
      l = [...l].sort((a, b) => {
        const x = plain(f, a[sort.k]), y = plain(f, b[sort.k]);
        return (isNaN(x) || isNaN(y) ? String(x).localeCompare(String(y)) : x - y) * sort.d;
      });
    }
    return l;
  }, [rows, q, sort, opts]);
  useEffect(() => setPage(0), [q, sort]);
  const pages = Math.max(1, Math.ceil(view.length / PAGE));
  const slice = view.slice(page * PAGE, page * PAGE + PAGE);

  const open = r => { setErrs({}); setForm(r ? {row: r, data: Object.fromEntries(fields.map(f => [f.k, r[f.k]]))} : {row: null, data: Object.fromEntries(fields.filter(f => f.type === "checkbox" && !f.ro).map(f => [f.k, true]))}); };
  const setv = (k, v) => setForm(o => ({...o, data: {...o.data, [k]: v}}));
  const submit = async e => {
    e.preventDefault();
    const edit = !!form.row;
    const body = {};
    fields.filter(f => !f.ro).forEach(f => {
      let v = form.data[f.k];
      if (f.type === "password") { if (v) body[f.k] = v; return; }
      if (v === "" || v === undefined) { if (!edit) return; v = f.type === "number" || f.src || f.choices ? null : ""; }
      body[f.k] = v;
    });
    setBusy(true);
    const x = edit ? await patch(`${url}/${form.row[pk]}/`, body, true) : await post(url + "/", body, true);
    setBusy(false);
    if (x.status >= 400) { setErrs(typeof x.data === "object" ? x.data : {}); return toast(errText(x.data), "err"); }
    toast(edit ? "Changes saved" : "Created successfully");
    setForm(null);
    load();
  };
  const remove = async () => {
    const x = await del(`${url}/${ask[pk]}/`, true);
    x.status < 400 ? toast("Deleted") : toast(errText(x.data), "err");
    setAsk(null);
    load();
  };
  const exportCsv = () => csvDownload(title.replace(/\W+/g, "-"), shown.map(f => human(f.k)), view.map(r => shown.map(f => plain(f, r[f.k]))));
  const input = f => {
    const v = form.data[f.k];
    if (f.type === "checkbox") return <label className="switch"><input type="checkbox" checked={!!v} onChange={e => setv(f.k, e.target.checked)} /><span /></label>;
    if (f.choices || f.src) {
      const list = f.choices || (opts[f.k] || []).map(o => [o.id, f.label(o)]);
      return <select value={v ?? ""} onChange={e => setv(f.k, e.target.value === "" ? null : (f.src ? Number(e.target.value) : e.target.value))}><option value="">— none —</option>{list.filter(([a]) => a !== "").map(([a, b]) => <option key={a} value={a}>{b}</option>)}</select>;
    }
    return <input type={f.type || "text"} step={f.type === "number" ? "any" : undefined} value={v ?? ""} onChange={e => setv(f.k, e.target.value)} autoComplete="off" placeholder={f.type === "password" && form.row ? "Leave blank to keep current" : ""} />;
  };
  const rowName = r => plain(shown[0], r[shown[0].k]) || plain(shown[1] || shown[0], r[(shown[1] || shown[0]).k]);

  return (
    <section className="crud panel">
      <div className="phead">
        <div><h3>{title}{rows && <span className="count">{view.length}</span>}</h3>{desc && <p className="desc">{desc}</p>}</div>
        <div className="tools">
          <label className="search"><span>🔍</span><input value={q} onChange={e => setQ(e.target.value)} placeholder="Search…" aria-label="Search" /></label>
          <button type="button" className="ghost" onClick={exportCsv} disabled={!view.length}>⬇ CSV</button>
          {create && !ro && <button type="button" onClick={() => open(null)}>＋ Add new</button>}
        </div>
      </div>
      <div className="scroll flat">
        <table>
          <thead><tr>{shown.map(f => <th key={f.k} onClick={() => setSort(s => ({k: f.k, d: s.k === f.k ? -s.d : 1}))} className="sortable">{human(f.k)}{sort.k === f.k ? (sort.d > 0 ? " ▲" : " ▼") : ""}</th>)}{(!ro || extra) && <th />}</tr></thead>
          <tbody>
            {rows === null && [0, 1, 2].map(i => <tr key={i}>{shown.map(f => <td key={f.k}><span className="skel" /></td>)}<td /></tr>)}
            {slice.map(r => (
              <tr key={r[pk]}>
                {shown.map(f => <td key={f.k}>{cell(f, r)}</td>)}
                {(!ro || extra) && <td className="acts">
                  {!ro && <button type="button" className="mini" onClick={() => open(r)} title="Edit">✏️ Edit</button>}
                  {canDel && !ro && <button type="button" className="mini bad" onClick={() => setAsk(r)} title="Delete">🗑</button>}
                  {extra && extra(r, load, toast)}
                </td>}
              </tr>
            ))}
          </tbody>
        </table>
        {rows && !view.length && <div className="empty"><span>🗂️</span><p>{q ? "No results match your search." : "Nothing here yet."}</p>{create && !ro && !q && <button type="button" onClick={() => open(null)}>＋ Add the first one</button>}</div>}
      </div>
      {view.length > PAGE && <div className="pager"><span>{page * PAGE + 1}–{Math.min(view.length, page * PAGE + PAGE)} of {view.length}</span><div><button type="button" className="ghost mini" disabled={page === 0} onClick={() => setPage(p => p - 1)}>‹ Prev</button><button type="button" className="ghost mini" disabled={page >= pages - 1} onClick={() => setPage(p => p + 1)}>Next ›</button></div></div>}

      {form && (
        <Modal title={(form.row ? "Edit " : "Add ") + title.replace(/ \(.*\)/, "").replace(/s$/, "")} onClose={() => setForm(null)}>
          <form onSubmit={submit} className="mform">
            <div className="fgrid">
              {fields.filter(f => !f.ro).map(f => (
                <label key={f.k} className={f.type === "checkbox" ? "inline" : ""}>
                  <span>{human(f.k)}</span>{input(f)}
                  {errs[f.k] && <em className="ferr">{[].concat(errs[f.k]).join(" ")}</em>}
                </label>
              ))}
            </div>
            <div className="mfoot"><button type="button" className="ghost" onClick={() => setForm(null)}>Cancel</button><button disabled={busy}>{busy ? "Saving…" : "Save"}</button></div>
          </form>
        </Modal>
      )}
      {ask && (
        <Modal title="Delete this item?" onClose={() => setAsk(null)}>
          <p>You are about to delete <b>{rowName(ask)}</b>. This cannot be undone.</p>
          <div className="mfoot"><button type="button" className="ghost" onClick={() => setAsk(null)}>Cancel</button><button type="button" className="danger" onClick={remove}>Yes, delete</button></div>
        </Modal>
      )}
    </section>
  );
}
