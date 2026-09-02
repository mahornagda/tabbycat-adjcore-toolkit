import { getStore } from "@netlify/blobs";
export const store = () => getStore({ name: "adjcore", consistency: "strong" });

export const DEFAULT_STATE = { extra_testers: [], panel_size: {}, notes: {}, manual_tests: [] };

export async function readJSON(key, fallback) {
  try { const v = await store().get(key, { type: "json" }); return v ?? fallback; }
  catch { return fallback; }
}
export async function writeJSON(key, val) { await store().setJSON(key, val); }
