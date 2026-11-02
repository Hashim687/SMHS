import {useCallback, useEffect, useState} from "react";
import {useTranslation} from "react-i18next";
import {get, post} from "./api";
import {payLab} from "./pay";
import {pick} from "./util";

export default function Portal({tref, who, summary}) {
  const {t, i18n} = useTranslation();
  const [d, setD] = useState(null);
  const [err, setErr] = useState("");
  const [card, setCard] = useState({card_no: "", holder: ""});
  const [fb, setFb] = useState({rating: 0, comment: ""});
  const L = i18n.language;
  const load = useCallback(async () => {
    const r = await get(`/api/public/tickets/${tref}/portal`);
    if (r.status === 200) setD(r.data);
  }, [tref]);
  useEffect(() => {
    load();
    const i = setInterval(load, 15000);
    return () => clearInterval(i);
  }, [load]);
  if (!d) return null;
  const when = x => new Date(x).toLocaleString(L);
  const send = async (path, body) => {
    const r = await post(`/api/public/tickets/${tref}/${path}`, body);
    setErr(r.status === 201 ? "" : t("badInput"));
    load();
  };
  const tk = d.ticket;
  return (
    <div className="portal">
      {summary && (
        <article className="card">
          {tk.department && <p>{t("goTo")}: <strong>{pick(tk.department, L)}</strong> · #{tk.token_no}</p>}
          <p>{t("state." + tk.state)}</p>
          {tk.admission && <p role="status"><strong>{t("adm." + tk.admission.status)}{tk.admission.ward ? ` · ${tk.admission.ward}` : ""}</strong></p>}
        </article>
      )}
      <h2>{t("tests")}</h2>
      {!d.lab.length && <p>{t("noTests")}</p>}
      {d.lab.map(o => (
        <article key={o.ref} className="card">
          <p><strong>₹{Number(o.total)}</strong> · <span className={"badge" + (o.paid ? "" : " red")}>{t(o.paid ? "paidTag" : "unpaidTag")}</span></p>
          {o.items.map(i => (
            <div key={i.id} className="item">
              <h3>{pick(i.test, L)}</h3>
              <p>{t("lstep." + i.step)}{i.go_to ? `: ${pick(i.go_to, L)}` : ""}</p>
              {i.status !== "resulted" && <p>{t("minLeft", {n: i.minutes_left})}</p>}
              {i.status === "resulted" && <p>{t("result")}: <strong dir="ltr">{i.value ?? i.text} {i.unit}</strong> {i.flag && i.flag !== "N" && <span className="badge red">{i.flag}</span>}</p>}
            </div>
          ))}
          <div className="row">
            {!o.paid && <button onClick={() => payLab(o.ref, who, t("app"), load, k => setErr(t(k)))}>💳 {t("pay")}</button>}
            {o.pdf_ready && <a className="btn" href={`/api/public/lab-orders/${o.ref}/report.pdf`} target="_blank" rel="noopener noreferrer">📄 {t("downloadPdf")}</a>}
          </div>
        </article>
      ))}
      <h2>{t("appointments")}</h2>
      {!d.appointments.length && <p>{t("none")}</p>}
      {d.appointments.map((a, i) => (
        <p key={i}>📅 {when(a.at)} · {pick(a, L)}{a.note && ` · ${a.note}`} · {t("mode." + a.mode)}
          {a.meeting_url && <> · <a href={a.meeting_url} target="_blank" rel="noopener noreferrer">🎥 {t("join")}</a></>}</p>
      ))}
      {tk.department && <>
        <h2>{t("golden")}</h2>
        {d.golden && d.golden.status !== "rejected" ? (
          <p>•••• {d.golden.last4} · {t("gc." + d.golden.status)}{d.golden.status === "verified" && d.golden.claim_status !== "none" ? ` · ${t("claim." + d.golden.claim_status)}` : ""}</p>
        ) : (
          <form onSubmit={e => { e.preventDefault(); send("golden-card", card); }}>
            {d.golden && <p className="err">{t("gc.rejected")}</p>}
            <label>{t("cardNo")}<input value={card.card_no} onChange={e => setCard({...card, card_no: e.target.value})} dir="ltr" minLength={8} maxLength={24} autoComplete="off" required /></label>
            <label>{t("holder")}<input value={card.holder} onChange={e => setCard({...card, holder: e.target.value})} maxLength={80} /></label>
            <button>{t("sendCard")}</button>
          </form>
        )}
        <h2>{t("rate")}</h2>
        {d.feedback ? <p>{t("thanks")}</p> : (
          <div className="row">
            {[1, 2, 3, 4, 5].map(n => <button key={n} type="button" aria-pressed={fb.rating === n} className={"tile small" + (fb.rating === n ? " on" : "")} onClick={() => setFb({...fb, rating: n})}>{"★".repeat(n)}</button>)}
            <input value={fb.comment} onChange={e => setFb({...fb, comment: e.target.value})} maxLength={300} placeholder={t("note")} />
            <button disabled={!fb.rating} onClick={() => send("feedback", fb)}>{t("save")}</button>
          </div>
        )}
      </>}
      <h2>{t("payments")}</h2>
      {d.payments.map((p, i) => <p key={i}>₹{Number(p.amount)} · {t("kind." + p.kind)} · {t("method." + p.method)} · {when(p.at)}</p>)}
      {err && <p role="alert" className="err">{err}</p>}
    </div>
  );
}
