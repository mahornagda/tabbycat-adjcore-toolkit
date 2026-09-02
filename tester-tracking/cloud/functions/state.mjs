import { checkAuth, deny, json } from "./_auth.mjs";
import { readJSON, writeJSON, DEFAULT_STATE } from "./_store.mjs";
export default async (req) => {
  if (!checkAuth(req)) return deny();
  if (req.method === "GET") return json(await readJSON("state", DEFAULT_STATE));
  if (req.method !== "POST") return json({ error: "POST only" }, 405);
  let body = {};
  try { body = await req.json(); } catch {}
  const clean = {
    extra_testers: (body.extra_testers || []).map(Number).filter(Number.isFinite),
    panel_size: body.panel_size && typeof body.panel_size === "object" ? body.panel_size : {},
    notes: body.notes && typeof body.notes === "object" ? body.notes : {},
    manual_tests: Array.isArray(body.manual_tests) ? body.manual_tests : [],
  };
  await writeJSON("state", clean);
  // ?quiet=1 -> just store it. Used by cell comments: nothing derived depends
  // on them, so re-reading the tab would be waste.
  const url = new URL(req.url);
  if (url.searchParams.get("quiet") === "1") return json({ ok: true });
  // kick the background read so the numbers follow the change
  fetch(`${url.origin}/.netlify/functions/refresh-background`, {
    method: "POST", headers: { authorization: req.headers.get("authorization") || "" },
  }).catch(() => {});
  await writeJSON("status", { running: true, started: Date.now(), log: ["recalculating"], error: null });
  return json({ ok: true });
};
