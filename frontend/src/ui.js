const NAMES = {name_en: "Name (EN)", name_ur: "Name (UR)", name_ks: "Name (KS)", staff_id: "Staff ID", is_active: "Active", totp_enabled: "2FA", ref_low: "Ref. low", ref_high: "Ref. high",
  turnaround_minutes: "Turnaround (min)", per_sample_minutes: "Per sample (min)", pay_at: "Pay at", sample_at: "Sample at", report_at: "Report at", emergency_category: "Emergency category", sent_at: "Sent at"};
export const human = k => NAMES[k] || (k.charAt(0).toUpperCase() + k.slice(1).replace(/_/g, " "));
export const errText = d => {
  if (!d) return "Something went wrong";
  if (typeof d === "string") return d.slice(0, 200);
  if (d.detail) return String(d.detail);
  return Object.entries(d).map(([k, v]) => `${human(k)}: ${Array.isArray(v) ? v.join(" ") : v}`).join(" · ").slice(0, 220);
};
export const listOf = r => (r.status === 200 ? (r.data.results || r.data) : []);
export const initials = s => (s || "?").split(/[\s._-]+/).filter(Boolean).slice(0, 2).map(w => w[0].toUpperCase()).join("") || "?";
export const when = x => (x ? new Date(x).toLocaleString() : "");
export const money = n => "₹" + Number(n || 0).toLocaleString("en-IN", {maximumFractionDigits: 0});
export const csvDownload = (name, head, rows) => {
  const q = v => `"${String(v ?? "").replace(/"/g, '""')}"`;
  const blob = new Blob(["\ufeff" + [head, ...rows].map(r => r.map(q).join(",")).join("\r\n")], {type: "text/csv;charset=utf-8"});
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = name + ".csv";
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
};
