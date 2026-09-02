/* ============================================================================
   Your Feedback — a judge's consolidated feedback, keyed by their private URL.

   The whole page is one lookup. A judge pastes their private URL, the browser
   hashes the key out of it, and the hash names a file on this origin. No key
   is ever sent anywhere: the request path carries a SHA-256 digest, and there
   is no list of judges, no index and no search — a page is reachable only from
   the key that produces it.
   ========================================================================== */

const $ = (s) => document.querySelector(s);

/* ------------------------------------------------------------------- theme -- */

const THEME = "adjcore-fb-theme";
function setTheme(t) {
  document.documentElement.dataset.theme = t;
  try { localStorage.setItem(THEME, t); } catch (e) { /* private window */ }
}
(function initTheme() {
  let t = null;
  try { t = localStorage.getItem(THEME); } catch (e) { /* ignore */ }
  setTheme(t || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"));
})();
$("#btn-theme").onclick = () =>
  setTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark");

/* --------------------------------------------------------------------- key -- */

/* Tabbycat private URLs look like
     https://<your-tab>/<slug>/privateurls/xxxxxxxx/
   — that example key is deliberately fake; the gate check that scans dist/ for
   a real url_key caught the first version of this comment, which used one.
   and people paste the lot, sometimes with a trailing feedback path. Take the
   longest run of key-shaped characters and be forgiving about the rest. */
function extractKey(raw) {
  const s = (raw || "").trim();
  if (!s) return null;
  const m = s.match(/privateurls?\/([A-Za-z0-9_-]{5,})/i);
  if (m) return m[1];
  const parts = s.replace(/[?#].*$/, "").split(/[/\s]+/).filter(Boolean);
  const cand = parts.reverse().find((p) => /^[A-Za-z0-9_-]{5,}$/.test(p) && !/^https?:$/i.test(p));
  return cand || null;
}

async function digest(key) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(key));
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

/* ------------------------------------------------------------------ render -- */

const esc = (s) => String(s == null ? "" : s)
  .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

function list(items) {
  return (items || []).map((x) => `<li>${esc(x)}</li>`).join("");
}

function render(d) {
  const thin = d.thin && (!d.strengths || d.strengths.length < 2);
  const blocks = [];

  blocks.push(`
    <div class="who">
      <h2>${esc(d.name)}</h2>
      <span class="tag">consolidated &middot; anonymous &middot; no scores</span>
    </div>
    <div class="card${thin ? " thin" : ""}">
      <p class="kicker">The read</p>
      <p class="overview">${esc(d.overview)}</p>
    </div>`);

  if (d.strengths && d.strengths.length) {
    blocks.push(`<div class="card block">
      <h3><span class="dot"></span>What came through strongly</h3>
      <ul class="pts">${list(d.strengths)}</ul></div>`);
  }
  if (d.growth && d.growth.length) {
    blocks.push(`<div class="card block grow">
      <h3><span class="dot"></span>What to work on</h3>
      <ul class="pts">${list(d.growth)}</ul></div>`);
  }
  if (d.themes && d.themes.length) {
    blocks.push(`<div class="card">
      <h3>What people wrote about</h3>
      <div class="chips">${(d.themes || [])
        .map((t) => `<span class="chip">${esc(t)}</span>`).join("")}</div></div>`);
  }

  blocks.push(`<div class="card">
      <p class="fine" style="margin:0;padding:0;border:0">
      Drawn from every written comment left about your judging, paraphrased throughout.
      Nobody is named, nothing is attributed, and nothing here tells you which debate a
      point came from &mdash; that is deliberate. If something reads as unfair or
      unclear, take it to the CAP; they would rather hear it than not.</p>
      <p style="margin:16px 0 0"><button class="ghost again" id="btn-again">Look up a different key</button></p>
    </div>`);

  $("#v-fb").innerHTML = blocks.join("");
  $("#v-gate").hidden = true;
  $("#v-fb").hidden = false;
  $("#btn-again").onclick = () => {
    $("#v-fb").hidden = true;
    $("#v-gate").hidden = false;
    $("#key").value = "";
    $("#key").focus();
  };
  window.scrollTo(0, 0);
}

/* ------------------------------------------------------------------- lookup -- */

function fail(msg) {
  const e = $("#err");
  e.innerHTML = msg;
  e.hidden = false;
}

async function lookup(raw) {
  $("#err").hidden = true;
  const key = extractKey(raw);
  if (!key) {
    fail("That does not look like a private URL. Paste the whole link from your " +
         "confirmation message, or just the code at the end of it.");
    return;
  }
  if (!crypto.subtle) {
    fail("This browser will not let the page hash your key. Try a different browser.");
    return;
  }
  const go = $("#go");
  go.disabled = true;
  go.textContent = "Looking…";
  try {
    const h = await digest(key);
    const r = await fetch(`f/${h}.json`, { cache: "no-store" });
    if (!r.ok) throw new Error(String(r.status));
    render(await r.json());
  } catch (err) {
    fail("No feedback found for that key. Two things it usually is: the link is " +
         "not quite the one you were sent, or nobody wrote anything about your " +
         "judging — which happens, and is not a verdict. The CAP can check for you.");
  } finally {
    go.disabled = false;
    go.textContent = "Show my feedback";
  }
}

$("#form").onsubmit = (e) => { e.preventDefault(); lookup($("#key").value); };

/* A judge who is already holding their private URL can be handed
   .../#<their key> and land straight on their page. The hashchange listener is
   not optional: arriving at #key from a page that is already open is a
   same-document navigation, so nothing re-runs without it. */
function fromHash() {
  if (location.hash.length > 1) lookup(decodeURIComponent(location.hash.slice(1)));
}
addEventListener("hashchange", fromHash);
fromHash();

$("#footnote").innerHTML =
  `<p>${esc(TOURNAMENT)} &middot; adjudication feedback &middot; built ${esc(BUILT)}</p>
   <p>This page holds no scores and no names. It makes no request except for your
   own summary, and your key is hashed in your browser before it is used.</p>`;
