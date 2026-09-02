/* ===========================================================================
   app.js — tabs, search, theme, deep links, and the page that explains itself.
   ========================================================================= */

const VIEWS = [
  { id: "fold",    label: "The fold",     render: renderFold },
  { id: "bracket", label: "Break rounds", render: renderBracket },
  { id: "sim",     label: "Simulator",    render: renderSim },
  { id: "rounds",  label: "Round by round", render: renderRounds },
  // The speaker tab appears only when the tournament has released it. Building
  // the tab list from the payload rather than showing an empty view means a
  // reader never clicks through to "not released yet".
  ...((DATA.speaker_scores || null) ? [{ id: "speaks", label: "Speaker tab", render: renderSpeaks }] : []),
  { id: "teams",   label: "Teams",        render: renderTeams },
  { id: "judges",  label: "Judges",       render: renderJudges },
  { id: "schools", label: "Schools",      render: renderSchools },
  { id: "shown",   label: "What's shown", render: renderShown },
];

let current = null;
const drawn = new Set();

function show(id, push) {
  const v = VIEWS.find(x => x.id === id) || VIEWS[0];
  current = v.id;
  for (const x of VIEWS) {
    q("#v-" + x.id).hidden = x.id !== v.id;
    const t = q("#tab-" + x.id);
    if (t) t.setAttribute("aria-selected", String(x.id === v.id));
  }
  if (v.id === "sim" || !drawn.has(v.id)) { v.render(); drawn.add(v.id); }
  if (push !== false) history.replaceState(null, "", "#" + v.id);
  scrollTo({ top: 0, behavior: "instant" });
}

/** Re-render a view next time it is shown — used when the data view changes. */
function invalidate(id) { drawn.delete(id); if (current === id) { VIEWS.find(v => v.id === id).render(); drawn.add(id); } }

/* -------------------------------------------------------------- what's shown */

function renderShown() {
  const root = clear(q("#v-shown"));
  const g = DATA.gate;
  root.append(el("div", { class: "head" },
    el("h2", { text: "What this site shows, and what it will not" }),
    el("p", { text: "This page is built from the tournament's public pages and nothing else. "
      + "Every time it is rebuilt it re-reads the tab's own public-feature switches and follows them — "
      + "so it can never be ahead of what the room already knows." })));

  root.append(el("div", { class: "cards", style: "grid-template-columns:repeat(auto-fit,minmax(320px,1fr))" },
    el("div", { class: "card" },
      el("h3", {}, "On the page", el("span", { class: "pill ok", text: "public" })),
      el("div", { class: "body" }, el("ul", { style: "margin:0;padding-left:18px" },
        (g.shown || []).map(s => el("li", { text: s, style: "margin-bottom:7px" }))))),
    el("div", { class: "card" },
      el("h3", {}, "Deliberately not on the page", el("span", { class: "pill warm", text: "held back" })),
      el("div", { class: "body" }, el("ul", { style: "margin:0;padding-left:18px" },
        (g.withheld || []).map(s => el("li", { text: s, style: "margin-bottom:7px" })))))));

  const rows = DATA.rounds.map(r => ({ r }));
  root.append(el("div", { style: "margin-top:20px" }, dataTable(rows, [
    { k: "abbr", label: "Round", get: x => x.r.seq, cell: x => el("b", { text: x.r.abbr }) },
    { k: "name", label: "", get: x => x.r.name, w: "26%" },
    { k: "draw", label: "Rooms and panel", get: x => x.r.draw_public ? 1 : 0,
      cell: x => el("span", { class: "pill " + (x.r.draw_public ? "ok" : "mute") + (x.r.draw_public ? "" : " lock"),
        text: x.r.draw_public ? "shown" : x.r.draw_status.toLowerCase() }) },
    { k: "res", label: "Rankings", get: x => x.r.results_public ? 1 : 0,
      cell: x => el("span", { class: "pill " + (x.r.results_public ? "ok" : (x.r.silent ? "gold" : "mute")),
        text: x.r.results_public ? "shown" : (x.r.silent ? "silent" : "not yet") }) },
    { k: "mot", label: "Motion", get: x => x.r.motion ? 1 : 0,
      cell: x => el("span", { class: "pill " + (x.r.motion ? "ok" : "mute"), text: x.r.motion ? "shown" : "unreleased" }) },
  ], { title: "Round by round, switch by switch", unit: "round", sort: "abbr", dir: 1,
       placeholder: "Filter rounds…" })));

  root.append(el("div", { class: "card", style: "margin-top:20px" },
    el("h3", {}, "How it is built"),
    el("div", { class: "body" },
      el("p", { style: "margin:0 0 10px", text:
        "A script on the adjudication core's machine reads the tab over a connection that can only ever issue GET requests, "
        + "keeps the handful of fields listed above, and writes this single file. The page you are reading holds no login, "
        + "makes no requests of its own and has no hidden data behind a flag — what is not in the list above was never written into it." }),
      el("p", { style: "margin:0 0 10px", text:
        "Break-round panels are drafted by the adjudication core long before they are announced. Those drafts live in a separate "
        + "tool that never touches this site, so a locked room here is genuinely empty rather than merely hidden." }),
      el("p", { style: "margin:0 0 10px", text:
        "The Simulator is your own guess and nothing more. Your picks are kept in your browser and put into the link when you "
        + "press Share; they are never sent to us, they are not visible to anyone else, and they have no bearing on the real draw. "
        + "Rooms after the first break round are folded by the format's convention, not read off the tab." }),
      DATA.tournament.staff ? el("div", {},
        el("h4", { text: "Run by" }),
        el("p", { class: "tiny", style: "margin:0;white-space:pre-line", text: DATA.tournament.staff })) : null,
      el("p", { class: "tiny dim", style: "margin:12px 0 0",
        text: `Tab read ${DATA.pulled_at} · page built ${DATA.built_at} · current round per tab: R${g.current_round}` }))));
}

/* -------------------------------------------------------------- self-update -- */

/**
 * The build on the adjudication core's machine republishes this file every few
 * minutes; a page left open on a screen should follow it without anyone pressing
 * anything. So: reload on a timer.
 *
 * It waits for a quiet moment rather than yanking the page out from under a
 * reader — nothing open, the tab actually visible, and no click or keypress for
 * a couple of minutes. The view is in the address bar and simulator picks are in
 * localStorage, so a reload lands you back where you were.
 *
 * Note this is a navigation, not a request made by the script: the page still
 * fetches nothing, which is what lets the strict policy in netlify.toml stand.
 */
function liveReload() {
  const EVERY = 5 * 60 * 1000;      // how old a page may get before it reloads
  const QUIET = 2 * 60 * 1000;      // how long since the reader last did anything
  let touched = Date.now();
  const bump = () => { touched = Date.now(); };
  for (const ev of ["pointerdown", "keydown", "wheel", "touchstart"]) {
    addEventListener(ev, bump, { passive: true });
  }
  const loaded = Date.now();
  setInterval(() => {
    if (Date.now() - loaded < EVERY) return;
    if (Date.now() - touched < QUIET) return;
    if (document.visibilityState !== "visible") return;
    if (!q("#sheetwrap").hidden || !q("#palette").hidden) return;
    location.reload();
  }, 30 * 1000);
}

/* ------------------------------------------------------------------ search -- */

function searchIndex() {
  const out = [];
  for (const t of DATA.teams) out.push({ kind: "Team", label: t.name, sub: t.inst,
    hay: `${t.name} ${t.long} ${t.inst} ${t.region || ""} ${(t.speakers || []).join(" ")}`.toLowerCase(),
    go: () => openTeam(t.id) });
  for (const j of DATA.judges) out.push({ kind: "Judge", label: j.name, sub: j.inst,
    hay: `${j.name} ${j.inst} ${j.region || ""}`.toLowerCase(), go: () => openJudge(j.id) });
  const rooms = new Set();
  for (const d of DEBATES) if (d.room) rooms.add(d.room);
  for (const r of rooms) out.push({ kind: "Room", label: r, sub: "find this room",
    hay: r.toLowerCase(), go: () => { rdState.find = r; invalidate("rounds"); show("rounds"); } });
  for (const v of VIEWS) out.push({ kind: "View", label: v.label, sub: "open",
    hay: v.label.toLowerCase(), go: () => show(v.id) });
  return out;
}

let IDX = null, pick = 0, hits = [];

function openPalette() {
  IDX = IDX || searchIndex();
  q("#palette").hidden = false;
  const inp = q("#q");
  inp.value = ""; inp.focus();
  runSearch("");
}
function closePalette() { q("#palette").hidden = true; }

function runSearch(s) {
  s = s.trim().toLowerCase();
  hits = (s ? IDX.filter(x => x.hay.includes(s)) : IDX.filter(x => x.kind === "View")).slice(0, 40);
  pick = 0;
  const ul = clear(q("#qres"));
  if (!hits.length) { ul.append(el("li", { class: "dim", text: "Nothing matches." })); return; }
  hits.forEach((h, i) => ul.append(el("li", {
    role: "option", "aria-selected": String(i === pick),
    onclick: () => { closePalette(); h.go(); },
  }, el("span", { class: "t", text: h.kind }), el("span", { text: h.label }),
     el("span", { class: "dim tiny", text: h.sub }))));
}
function movePick(d) {
  if (!hits.length) return;
  pick = (pick + d + hits.length) % hits.length;
  const items = q("#qres").children;
  for (let i = 0; i < items.length; i++) items[i].setAttribute("aria-selected", String(i === pick));
  items[pick].scrollIntoView({ block: "nearest" });
}

/* -------------------------------------------------------------------- boot -- */

/** #fold · #team-123 · #judge-456 · #sim=open.0132… */
function openHash(h, live) {
  if (!h) { if (!live) show("fold", false); return; }
  if (h.startsWith("sim=")) {
    if (simFromCode(h.slice(4))) { invalidate("sim"); show("sim", false); }
    return;
  }
  const m = /^(team|judge)-(\d+)$/.exec(h);
  if (m) {
    if (!live) show("fold", false);
    (m[1] === "team" ? openTeam : openJudge)(+m[2]);
    return;
  }
  if (VIEWS.some(v => v.id === h)) show(h, false);
  else if (!live) show("fold", false);
}

function boot() {
  const t = DATA.tournament;
  document.title = "The Fold — " + (t.short || t.name);
  q("#tname").textContent = "The Fold";
  q("#tsub").textContent = t.name;

  const tabs = q("#tabs");
  for (const v of VIEWS) {
    tabs.append(el("button", {
      class: "tab", id: "tab-" + v.id, role: "tab", "aria-selected": "false",
      text: v.label, onclick: () => show(v.id),
    }));
  }

  q("#footnote").append(
    el("span", {}, "Built from the public tab only — see ",
      el("a", { class: "linkish", href: "#shown", onclick: e => { e.preventDefault(); show("shown"); } },
        "what's shown")),
    el("span", { class: "mono", text: "tab read " + DATA.pulled_at }),
    el("span", { text: "rebuilt from the tab every few minutes — this page reloads itself" }),
    el("span", {}, plural(DATA.teams.length, "team") + " · " + plural(DATA.judges.length, "judge")
      + " · " + plural(DATA.debates.length, "room")),
    t.site ? el("a", { class: "linkish", href: t.site, target: "_blank", rel: "noopener",
      text: "the tournament's own tab ↗" }) : null);

  // theme
  const saved = localStorage.getItem("fold-theme");
  if (saved) document.documentElement.dataset.theme = saved;
  else if (matchMedia("(prefers-color-scheme: dark)").matches) document.documentElement.dataset.theme = "dark";
  q("#btn-theme").onclick = () => {
    const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem("fold-theme", next); } catch (e) { /* private window */ }
  };

  liveReload();
  q("#btn-search").onclick = openPalette;
  q("#q").oninput = e => runSearch(e.target.value);
  q("#q").onkeydown = e => {
    if (e.key === "ArrowDown") { e.preventDefault(); movePick(1); }
    else if (e.key === "ArrowUp") { e.preventDefault(); movePick(-1); }
    else if (e.key === "Enter" && hits[pick]) { e.preventDefault(); closePalette(); hits[pick].go(); }
  };
  for (const n of document.querySelectorAll("[data-close]")) {
    n.onclick = () => { closePalette(); closeSheet(); };
  }
  addEventListener("keydown", e => {
    if (e.key === "Escape") { closePalette(); closeSheet(); return; }
    const typing = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement.tagName);
    if (typing) return;
    if (e.key === "/" || ((e.metaKey || e.ctrlKey) && e.key === "k")) { e.preventDefault(); openPalette(); }
    const n = "12345678".indexOf(e.key);
    if (n >= 0 && VIEWS[n]) show(VIEWS[n].id);
  });

  simRestore();
  openHash(location.hash.slice(1), false);
  // Someone pasting a shared link while already here changes only the hash, which
  // reloads nothing — so act on it ourselves.
  addEventListener("hashchange", () => openHash(location.hash.slice(1), true));
}

boot();
