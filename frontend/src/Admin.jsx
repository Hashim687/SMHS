import {useState} from "react";
import {post} from "./api";
import Crud from "./Crud.jsx";
import Dashboard from "./Dashboard.jsx";
import Directory from "./Directory.jsx";
import Reports from "./Reports.jsx";
import Translations from "./Translations.jsx";
import {errText} from "./ui.js";

const ROLES = ["patient", "doctor", "nurse", "admin", "lab", "reception", "cashier"].map(r => [r, r]);
const CAT = [["", "—"], ["medical", "medical"], ["surgical", "surgical"]];
const user = {src: "/api/admin/users", label: u => `${u.username} (${u.role})`};
const dept = {src: "/api/admin/departments", label: d => d.name_en};
const loc = {src: "/api/admin/locations", label: l => l.name_en};

const NAV = [
  ["Overview", [["dashboard", "📊", "Dashboard"]]],
  ["People", [["directory", "🩺", "Doctors & staff"], ["accounts", "👥", "All accounts"], ["assign", "🔗", "Assignments"]]],
  ["Hospital", [["departments", "🏥", "Departments"], ["beds", "🛏️", "Beds"], ["ambulances", "🚑", "Ambulances"], ["locations", "📍", "Locations"]]],
  ["Money & lab", [["pricing", "💰", "Ticket prices"], ["labtests", "🧪", "Lab tests"]]],
  ["Triage", [["symptoms", "🤒", "Symptoms"], ["rules", "🧭", "Triage rules"]]],
  ["Insights", [["reports", "📈", "Reports"], ["feedback", "⭐", "Feedback"]]],
  ["System", [["notifications", "💬", "SMS / message log"], ["translations", "🌐", "Translations"], ["security", "🔐", "Security & audit"]]],
];
const ALL = NAV.flatMap(([, l]) => l);

export default function Admin() {
  const [sec, setSec] = useState("dashboard");
  const [menu, setMenu] = useState(false);
  const go = k => { setSec(k); setMenu(false); scrollTo({top: 0, behavior: "smooth"}); };
  const cur = ALL.find(x => x[0] === sec);
  return (
    <div className="console">
      <aside className={"side" + (menu ? " open" : "")}>
        <button type="button" className="burger" onClick={() => setMenu(m => !m)} aria-expanded={menu}>☰ <span>{cur[1]} {cur[2]}</span></button>
        <nav aria-label="Admin sections">
          {NAV.map(([g, items]) => (
            <div key={g} className="grp"><h4>{g}</h4>
              {items.map(([k, i, l]) => <button type="button" key={k} className={"nav" + (sec === k ? " on" : "")} aria-current={sec === k ? "page" : undefined} onClick={() => go(k)}><span>{i}</span>{l}</button>)}
            </div>
          ))}
        </nav>
      </aside>
      <div className="content">
        <div className="crumb">Admin <i>›</i> <b>{cur[2]}</b></div>
        {sec === "dashboard" && <Dashboard go={go} />}
        {sec === "directory" && <Directory />}
        {sec === "accounts" && <Crud title="All accounts" desc="Every login in the system, including patients. Click Active to enable or disable an account." url="/api/admin/users" canDel
          cols={["username", "first_name", "role", "staff_id", "phone", "is_active", "totp_enabled"]}
          fields={[{k: "username"}, {k: "first_name"}, {k: "last_name"}, {k: "role", choices: ROLES}, {k: "staff_id"}, {k: "phone"}, {k: "is_active", type: "checkbox"}, {k: "password", type: "password"}, {k: "totp_enabled", type: "checkbox", ro: true}]}
          extra={(r, load, toast) => r.role !== "patient" && <button type="button" className="mini ghost" onClick={async () => { const x = await post(`/api/admin/users/${r.id}/reset_2fa/`, {}, true); x.status < 400 ? toast("2FA reset") : toast(errText(x.data), "err"); load(); }}>2FA ↺</button>} />}
        {sec === "assign" && <Crud title="Staff assignments" desc="Which staff work in which department." url="/api/admin/staff-assignments" canDel fields={[{k: "user", ...user}, {k: "department", ...dept}]} />}
        {sec === "departments" && <Crud title="Departments" desc="Clinical departments patients are routed to." url="/api/admin/departments" cols={["code", "name_en", "name_ur", "head", "emergency_category", "is_active"]} fields={[{k: "code"}, {k: "name_en"}, {k: "name_ur"}, {k: "name_ks"}, {k: "head", ...user}, {k: "emergency_category", choices: CAT}, {k: "is_active", type: "checkbox"}]} />}
        {sec === "beds" && <Crud title="Beds" desc="Ward beds that can be assigned to admitted patients." url="/api/admin/beds" canDel fields={[{k: "department", ...dept}, {k: "label"}, {k: "is_active", type: "checkbox"}]} />}
        {sec === "ambulances" && <Crud title="Ambulances" desc="Live status shown to patients on the public site." url="/api/staff/ambulances" canDel cols={["label", "status", "note", "updated"]} fields={[{k: "label"}, {k: "status", choices: ["available", "dispatched", "at_scene", "returning", "offline"].map(x => [x, x])}, {k: "note"}, {k: "updated", ro: true}]} />}
        {sec === "locations" && <Crud title="Locations" desc="Counters and rooms used for lab payment, sampling and report pick-up." url="/api/admin/locations" canDel fields={[{k: "code"}, {k: "name_en"}, {k: "name_ur"}, {k: "name_ks"}]} />}
        {sec === "pricing" && <Crud title="Ticket prices (min ₹10)" desc="What a patient pays for an OPD or emergency ticket." url="/api/admin/prices" pk="kind" create={false} fields={[{k: "kind", ro: true}, {k: "amount", type: "number"}]} />}
        {sec === "labtests" && <Crud title="Lab tests" desc="Tests, prices, reference ranges and where each step happens." url="/api/admin/lab-tests" cols={["code", "name_en", "price", "unit", "turnaround_minutes", "is_active"]} fields={[{k: "code"}, {k: "name_en"}, {k: "name_ur"}, {k: "name_ks"}, {k: "price", type: "number"}, {k: "unit"}, {k: "ref_low", type: "number"}, {k: "ref_high", type: "number"}, {k: "turnaround_minutes", type: "number"}, {k: "per_sample_minutes", type: "number"}, {k: "pay_at", ...loc}, {k: "sample_at", ...loc}, {k: "report_at", ...loc}, {k: "is_active", type: "checkbox"}]} />}
        {sec === "symptoms" && <Crud title="Symptoms" desc="Tiles patients tick while registering." url="/api/admin/symptoms" canDel fields={[{k: "key"}, {k: "icon"}, {k: "emergency_category", choices: CAT}, {k: "severity", type: "number"}, {k: "is_active", type: "checkbox"}]} />}
        {sec === "rules" && <Crud title="Triage rules" desc="Which department a symptom points to, and how strongly." url="/api/admin/triage-rules" canDel fields={[{k: "symptom", src: "/api/admin/symptoms", label: s => s.key}, {k: "department", ...dept}, {k: "weight", type: "number"}]} />}
        {sec === "reports" && <Reports mode="reports" />}
        {sec === "feedback" && <Crud title="Patient feedback" desc="Ratings and comments left after a visit." url="/api/admin/feedback" ro fields={[{k: "rating"}, {k: "comment"}, {k: "created"}]} />}
        {sec === "notifications" && <Crud title="SMS / message log" desc="Pending or failed messages mean the SMS provider is not set up, so patients will not get OTPs." url="/api/admin/notifications" ro cols={["to", "channel", "status", "attempts", "created", "sent_at"]} fields={[{k: "to"}, {k: "channel"}, {k: "status"}, {k: "attempts"}, {k: "created"}, {k: "sent_at"}]} />}
        {sec === "translations" && <Translations />}
        {sec === "security" && <Reports mode="security" />}
      </div>
    </div>
  );
}
