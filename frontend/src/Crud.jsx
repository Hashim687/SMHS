import {useCallback, useEffect, useState} from "react";
import {del, get, patch, post} from "./api";

export default function Crud({title, url, fields, pk = "id", create = true, canDel = false, ro = false, extra}) {
  const [rows, setRows] = useState([]);
  const [ed, setEd] = useState({});
  const [nw, setNw] = useState({});
  const [opts, setOpts] = useState({});
  const [err, setErr] = useState("");
  const load = useCallback(async () => {
    const r = await get(url + "/", true);
    if (r.status === 200) setRows(r.data.results || r.data);
  }, [url]);
  useEffect(() => {
    load();
    fields.filter(f => f.src).forEach(async f => {
      const r = await get(f.src + "/", true);
      if (r.status === 200) setOpts(o => ({...o, [f.k]: r.data.results || r.data}));
    });
  }, [load]);

  const field = (f, v, on) => {
    if (f.ro || ro) return <span>{v === null || v === undefined ? "" : f.src ? (opts[f.k] || []).map(o => f.label(o) && o.id === v ? f.label(o) : null) : String(v)}</span>;
    if (f.type === "checkbox") return <input type="checkbox" checked={!!v} onChange={e => on(e.target.checked)} aria-label={f.k} />;
    if (f.choices || f.src) {
      const list = f.choices || (opts[f.k] || []).map(o => [o.id, f.label(o)]);
      return <select value={v ?? ""} onChange={e => on(e.target.value === "" ? null : e.target.value)} aria-label={f.k}><option value="" />{list.map(([a, b]) => <option key={a} value={a}>{b}</option>)}</select>;
    }
    return <input type={f.type || "text"} value={v ?? ""} onChange={e => on(e.target.value)} aria-label={f.k} autoComplete="off" />;
  };
  const clean = o => Object.fromEntries(Object.entries(o).filter(([k, v]) => !(fields.find(f => f.k === k) || {}).type?.startsWith("pass") || v));
  const fail = r => setErr(r.status >= 400 ? JSON.stringify(r.data).slice(0, 200) : "");
  const save = async r => { const x = await patch(`${url}/${r[pk]}/`, clean(ed[r[pk]] || {}), true); fail(x); if (x.status < 400) { setEd({...ed, [r[pk]]: {}}); load(); } };
  const add = async () => { const x = await post(url + "/", clean(nw), true); fail(x); if (x.status < 400) { setNw({}); load(); } };
  const rm = async r => { const x = await del(`${url}/${r[pk]}/`, true); fail(x); load(); };

  return (
    <section className="crud">
      <h3>{title}</h3>
      {err && <p role="alert" className="err">{err}</p>}
      <div className="scroll">
        <table>
          <thead><tr>{fields.map(f => <th key={f.k}>{f.k}</th>)}<th /></tr></thead>
          <tbody>
            {create && !ro && (
              <tr className="new">{fields.filter(f => !f.ro).length ? fields.map(f => <td key={f.k}>{f.ro ? null : field(f, nw[f.k], v => setNw({...nw, [f.k]: v}))}</td>) : null}<td><button onClick={add}>+</button></td></tr>
            )}
            {rows.map(r => (
              <tr key={r[pk]}>
                {fields.map(f => <td key={f.k}>{field(f, (ed[r[pk]] || {})[f.k] ?? r[f.k], v => setEd({...ed, [r[pk]]: {...(ed[r[pk]] || {}), [f.k]: v}}))}</td>)}
                <td className="acts">
                  {!ro && <button disabled={!Object.keys(ed[r[pk]] || {}).length} onClick={() => save(r)}>✔</button>}
                  {canDel && <button className="danger" onClick={() => rm(r)}>✖</button>}
                  {extra && extra(r, load)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
