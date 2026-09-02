import { checkAuth, deny, json } from "./_auth.mjs";
import { readJSON } from "./_store.mjs";
export default async (req) => {
  if (!checkAuth(req)) return deny();
  const url = new URL(req.url);
  if (url.searchParams.get("probe")) return json({ ok: true });
  const d = await readJSON("data", null);
  if (!d) return json({ error: "No data yet — press Refresh." }, 200);
  return json(d);
};
