import {useState} from "react";
import {useTranslation} from "react-i18next";
import {post} from "./api";
import Crud from "./Crud.jsx";
import Reports from "./Reports.jsx";
import Translations from "./Translations.jsx";

const ROLES = ["patient", "doctor", "nurse", "admin", "lab", "reception", "cashier"].map(r => [r, r]);
const CAT = [["", "—"], ["medical", "medical"], ["surgical", "surgical"]];
const user = {src: "/api/admin/users", label: u => `${u.username} (${u.role})`};
const dept = {src: "/api/admin/departments", label: d => d.name_en};
const loc = {src: "/api/admin/locations", label: l => l.name_en};
const TABS = ["users", "departments", "pricing", "triage", "translations", "reports", "security"];

export default function Admin() {
  const {t} = useTranslation();
  const [tab, setTab] = useState("users");
  return (
    <div className="ward">
      <div className="tabs" role="tablist">
        {TABS.map(k => <button key={k} role="tab" aria-selected={tab === k} className={tab === k ? "tab on" : "tab"} onClick={() => setTab(k)}>{t("admin." + k)}</button>)}
      </div>
      {tab === "users" && <>
        <Crud title="users" url="/api/admin/users" canDel fields={[{k: "username"}, {k: "first_name"}, {k: "role", choices: ROLES}, {k: "staff_id"}, {k: "phone"}, {k: "is_active", type: "checkbox"}, {k: "password", type: "password"}, {k: "totp_enabled", ro: true}]}
          extra={(r, load) => r.role !== "patient" && <button onClick={async () => { await post(`/api/admin/users/${r.id}/reset_2fa/`, {}, true); load(); }}>2FA ↺</button>} />
        <Crud title="staff assignments" url="/api/admin/staff-assignments" canDel fields={[{k: "user", ...user}, {k: "department", ...dept}]} />
      </>}
      {tab === "departments" && <>
        <Crud title="departments" url="/api/admin/departments" fields={[{k: "code"}, {k: "name_en"}, {k: "name_ur"}, {k: "name_ks"}, {k: "head", ...user}, {k: "emergency_category", choices: CAT}, {k: "is_active", type: "checkbox"}]} />
        <Crud title="beds" url="/api/admin/beds" canDel fields={[{k: "department", ...dept}, {k: "label"}, {k: "is_active", type: "checkbox"}]} />
        <Crud title="ambulances" url="/api/staff/ambulances" canDel fields={[{k: "label"}, {k: "status", choices: ["available", "dispatched", "at_scene", "returning", "offline"].map(x => [x, x])}, {k: "note"}]} />
      </>}
      {tab === "pricing" && <>
        <Crud title="ticket prices (min ₹10)" url="/api/admin/prices" pk="kind" create={false} fields={[{k: "kind", ro: true}, {k: "amount", type: "number"}]} />
        <Crud title="lab tests" url="/api/admin/lab-tests" fields={[{k: "code"}, {k: "name_en"}, {k: "name_ur"}, {k: "name_ks"}, {k: "price", type: "number"}, {k: "unit"}, {k: "ref_low", type: "number"}, {k: "ref_high", type: "number"}, {k: "turnaround_minutes", type: "number"}, {k: "per_sample_minutes", type: "number"}, {k: "pay_at", ...loc}, {k: "sample_at", ...loc}, {k: "report_at", ...loc}, {k: "is_active", type: "checkbox"}]} />
        <Crud title="locations" url="/api/admin/locations" canDel fields={[{k: "code"}, {k: "name_en"}, {k: "name_ur"}, {k: "name_ks"}]} />
      </>}
      {tab === "triage" && <>
        <Crud title="symptoms" url="/api/admin/symptoms" canDel fields={[{k: "key"}, {k: "icon"}, {k: "emergency_category", choices: CAT}, {k: "severity", type: "number"}, {k: "is_active", type: "checkbox"}]} />
        <Crud title="triage rules" url="/api/admin/triage-rules" canDel fields={[{k: "symptom", src: "/api/admin/symptoms", label: s => s.key}, {k: "department", ...dept}, {k: "weight", type: "number"}]} />
      </>}
      {tab === "translations" && <Translations />}
      {tab === "reports" && <><Reports mode="reports" /><Crud title="feedback" url="/api/admin/feedback" ro fields={[{k: "rating"}, {k: "comment"}, {k: "created"}]} /></>}
      {tab === "security" && <Reports mode="security" />}
    </div>
  );
}
