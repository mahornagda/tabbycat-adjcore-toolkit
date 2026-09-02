import { checkAuth, deny, json } from "./_auth.mjs";
import { readJSON, writeJSON, DEFAULT_STATE } from "./_store.mjs";
import { buildData } from "./_derive.mjs";

export default async (req) => {
  if (!checkAuth(req)) return deny();
  const log = [];
  await writeJSON("status", { running: true, started: Date.now(), log: ["starting"], error: null });
  try {
    const state = await readJSON("state", DEFAULT_STATE);
    const data = await buildData(state, m => log.push(String(m)));
    await writeJSON("data", data);
    await writeJSON("status", { running: false, started: null, log, error: null,
                                finished_at: new Date().toISOString() });
  } catch (e) {
    await writeJSON("status", { running: false, started: null, log,
                                error: `${e.name}: ${e.message}` });
  }
  return json({ ok: true });
};
