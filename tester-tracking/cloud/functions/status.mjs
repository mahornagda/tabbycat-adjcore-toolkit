import { checkAuth, deny, json } from "./_auth.mjs";
import { readJSON } from "./_store.mjs";
export default async (req) => {
  if (!checkAuth(req)) return deny();
  const s = await readJSON("status", { running: false, log: [], error: null });
  // a run that started over 8 minutes ago is treated as dead, not stuck
  if (s.running && s.started && Date.now() - s.started > 8 * 60 * 1000) {
    return json({ ...s, running: false, error: "the read timed out — try Refresh again" });
  }
  return json(s);
};
