/**
 * READ-ONLY Tabbycat reader. The only POST it ever makes is the login form.
 * Every tournament read goes through get(), which hardcodes method GET.
 */
const BASE = () => (process.env.TABBY_BASE || "").replace(/\/$/, "");
const SLUG = () => process.env.TABBY_SLUG || "";

export async function login() {
  const url = `${BASE()}/accounts/login/`;
  const r1 = await fetch(url);
  const html = await r1.text();
  const tok = (html.match(/name="csrfmiddlewaretoken" value="([^"]+)"/) || [])[1];
  if (!tok) throw new Error("could not read the login form");
  const jar = parseCookies(r1.headers);
  const body = new URLSearchParams({
    csrfmiddlewaretoken: tok,
    username: process.env.TABBY_USER || "",
    password: process.env.TABBY_PASS || "",
    next: `/${SLUG()}/`,
  });
  const r2 = await fetch(url, {
    method: "POST", redirect: "manual",
    headers: { "content-type": "application/x-www-form-urlencoded",
               referer: url, cookie: cookieHeader(jar) },
    body,
  });
  Object.assign(jar, parseCookies(r2.headers));
  if (!jar.sessionid) throw new Error("Tabbycat login failed — check the credentials");
  return cookieHeader(jar);
}

function parseCookies(headers) {
  const out = {};
  const raw = headers.getSetCookie ? headers.getSetCookie() : [];
  for (const c of raw) {
    const [kv] = c.split(";");
    const i = kv.indexOf("=");
    if (i > 0) out[kv.slice(0, i).trim()] = kv.slice(i + 1).trim();
  }
  return out;
}
const cookieHeader = jar => Object.entries(jar).map(([k, v]) => `${k}=${v}`).join("; ");

export function makeClient(cookie) {
  const get = async (url) => {
    const r = await fetch(url, { method: "GET", headers: { cookie } });   // GET only, always
    if (!r.ok) throw new Error(`${r.status} on ${url}`);
    return r;
  };
  const api = async (path, { paginate = false, tournament = true } = {}) => {
    const root = `${BASE()}/api/v1`;
    let url = /^https?:/.test(path) ? path
      : (() => { const p = path.replace(/^\/|\/$/g, "");
                 const b = tournament ? `${root}/tournaments/${SLUG()}` : root;
                 return p ? `${b}/${p}` : b; })();
    const out = [];
    while (url) {
      const r = await get(url);
      const d = await r.json();
      if (!paginate) return d;
      out.push(...(Array.isArray(d) ? d : [d]));
      url = nextLink(r.headers.get("link") || "");
    }
    return out;
  };
  const vuedata = async (page) => {
    const r = await get(`${BASE()}/${SLUG()}/${page.replace(/^\//, "")}`);
    const html = await r.text();
    const i = html.indexOf("window.vueData");
    if (i < 0) return {};
    const body = html.slice(html.indexOf("{", i) + 1);
    const out = {};
    const re = /['"]?(\w+)['"]?\s*:/g;
    let m;
    while ((m = re.exec(body))) {
      const rest = body.slice(m.index + m[0].length).replace(/^\s+/, "");
      if (rest[0] !== "[" && rest[0] !== "{") continue;
      if (out[m[1]] !== undefined) continue;
      const val = scanJSON(rest);
      if (val !== undefined) out[m[1]] = val;
    }
    return out;
  };
  return { api, vuedata };
}

function nextLink(link) {
  for (const part of link.split(",")) {
    const m = part.match(/\s*<([^>]+)>;\s*rel="next"/);
    if (m) return m[1];
  }
  return null;
}

/** Read one complete JSON value from the front of a string. */
function scanJSON(s) {
  const open = s[0], close = open === "[" ? "]" : "}";
  let depth = 0, inStr = false, escNext = false;
  for (let i = 0; i < s.length; i++) {
    const c = s[i];
    if (escNext) { escNext = false; continue; }
    if (c === "\\") { escNext = true; continue; }
    if (c === '"') { inStr = !inStr; continue; }
    if (inStr) continue;
    if (c === open) depth++;
    else if (c === close) { depth--; if (!depth) {
      try { return JSON.parse(s.slice(0, i + 1)); } catch { return undefined; } } }
  }
  return undefined;
}
