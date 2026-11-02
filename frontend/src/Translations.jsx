import {useCallback, useEffect, useState} from "react";
import {useTranslation} from "react-i18next";
import {del, get, patch, post} from "./api";
import i18n from "./i18n";

const flat = (o, p = "") => Object.entries(o).flatMap(([k, v]) => typeof v === "object" ? flat(v, p + k + ".") : [[p + k, v]]);

export default function Translations() {
  const {t} = useTranslation();
  const [lang, setLang] = useState("ur");
  const [q, setQ] = useState("");
  const [ov, setOv] = useState([]);
  const [vals, setVals] = useState({});
  const load = useCallback(async () => {
    const r = await get("/api/admin/translations/", true);
    if (r.status === 200) setOv(r.data);
  }, []);
  useEffect(() => { load(); }, [load]);
  const base = flat(i18n.getResourceBundle("en", "translation") || {});
  const cur = k => i18n.getResource(lang, "translation", k) || "";
  const rows = base.filter(([k, v]) => !q || k.includes(q) || String(v).toLowerCase().includes(q.toLowerCase())).slice(0, 150);
  const save = async k => {
    const v = (vals[k] ?? cur(k)).trim();
    const e = ov.find(o => o.lang === lang && o.key === k);
    if (!v && e) await del(`/api/admin/translations/${e.id}/`, true);
    else if (e) await patch(`/api/admin/translations/${e.id}/`, {value: v}, true);
    else if (v) await post("/api/admin/translations/", {lang, key: k, value: v}, true);
    if (v) i18n.addResource(lang, "translation", k, v);
    setVals({...vals, [k]: undefined});
    load();
  };
  return (
    <section className="crud">
      <h3>{t("admin.translations")}</h3>
      <div className="row">
        <select value={lang} onChange={e => setLang(e.target.value)} aria-label={t("language")}>{["en", "ur", "ks"].map(l => <option key={l} value={l}>{l}</option>)}</select>
        <input value={q} onChange={e => setQ(e.target.value)} placeholder="search" aria-label="search" />
      </div>
      {rows.map(([k, v]) => (
        <div key={k} className="card">
          <small dir="ltr">{k}</small>
          <p dir="ltr">{String(v)}</p>
          <div className="row">
            <input value={vals[k] ?? cur(k)} onChange={e => setVals({...vals, [k]: e.target.value})} maxLength={300} aria-label={k} />
            <button onClick={() => save(k)}>{t("save")}</button>
          </div>
        </div>
      ))}
    </section>
  );
}
