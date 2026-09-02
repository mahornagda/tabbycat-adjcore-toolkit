import crypto from "node:crypto";

const SECRET = () => process.env.AUTH_SECRET || "change-me";

export function mintToken() {
  return crypto.createHmac("sha256", SECRET()).update("adjcore-v1").digest("hex");
}

export function checkAuth(req) {
  // No passphrase configured => the dashboard is open. Set ADJCORE_PASSWORD
  // in the Netlify env to switch the login back on.
  if (!process.env.ADJCORE_PASSWORD) return true;
  const hdr = req.headers.get("authorization") || "";
  const got = hdr.replace(/^Bearer\s+/i, "").trim();
  const want = mintToken();
  if (got.length !== want.length) return false;
  try {
    return crypto.timingSafeEqual(Buffer.from(got), Buffer.from(want));
  } catch { return false; }
}

export const deny = () =>
  new Response(JSON.stringify({ error: "unauthorised" }), {
    status: 401, headers: { "content-type": "application/json" },
  });

export const json = (obj, status = 200) =>
  new Response(JSON.stringify(obj), {
    status, headers: { "content-type": "application/json", "cache-control": "no-store" },
  });
