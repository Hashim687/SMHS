let tokens = null;

export const setTokens = t => { tokens = t; };

const call = async (method, url, body, auth, retry = true) => {
  const headers = {"Content-Type": "application/json"};
  if (auth && tokens) headers.Authorization = "Bearer " + tokens.access;
  const r = await fetch(url, {method, headers, body: method === "GET" ? undefined : JSON.stringify(body || {})});
  if (r.status === 401 && auth && retry && tokens && tokens.refresh) {
    const rr = await fetch("/api/auth/refresh", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({refresh: tokens.refresh})});
    if (rr.ok) {
      const d = await rr.json();
      tokens = {...tokens, access: d.access, refresh: d.refresh || tokens.refresh};
      return call(method, url, body, auth, false);
    }
    tokens = null;
    window.dispatchEvent(new Event("session-expired"));
  }
  return {status: r.status, data: await r.json().catch(() => ({}))};
};

export const post = (url, body, auth) => call("POST", url, body, auth);
export const get = (url, auth) => call("GET", url, null, auth);

export const openPdf = async url => {
  const w = window.open("", "_blank");
  if (tokens) await call("GET", "/api/staff/profile", null, true);
  const r = await fetch(url, {headers: tokens ? {Authorization: "Bearer " + tokens.access} : {}});
  if (!r.ok) { if (w) w.close(); return r.status; }
  const u = URL.createObjectURL(await r.blob());
  if (w) w.location = u; else window.open(u, "_blank");
  return 200;
};

export const patch = (url, body, auth) => call("PATCH", url, body, auth);
export const del = (url, auth) => call("DELETE", url, null, auth);
