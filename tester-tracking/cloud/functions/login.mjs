import { mintToken, json } from "./_auth.mjs";
export default async (req) => {
  if (req.method !== "POST") return json({ error: "POST only" }, 405);
  let body = {};
  try { body = await req.json(); } catch {}
  const want = process.env.ADJCORE_PASSWORD || "";
  if (!want) return json({ error: "no passphrase configured" }, 500);
  if (String(body.password || "") !== want) return json({ error: "wrong passphrase" }, 401);
  return json({ token: mintToken() });
};
