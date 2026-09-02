/* ===========================================================================
   core.js — the indexes and the derivations every view reads from.

   Everything here is computed from DATA, and DATA only ever contains what
   gate.py let through. There is no fetch in this file, or in any other: the
   page is the data. If a round's results are not public, `pts` is null and
   every derivation below simply has nothing to say about it.
   ========================================================================= */

const SIDE_LABEL = { og: "OG", oo: "OO", cg: "CG", co: "CO", aff: "PROP", neg: "OPP", bye: "BYE" };
const SIDE_FULL = {
  og: "Opening Government", oo: "Opening Opposition",
  cg: "Closing Government", co: "Closing Opposition",
  aff: "Proposition", neg: "Opposition", bye: "Bye",
};
const POS_FULL = { C: "Chair", P: "Panellist", T: "Trainee" };
const ORD = ["4th", "3rd", "2nd", "1st"];            // indexed by BP points
const REMARK = {
  C: "capped", D: "broke in another category", d: "disqualified",
  t: "lost the coin toss", w: "withdrew", "": null,
};

/* ------------------------------------------------------------------ lookup -- */

const T = new Map(DATA.teams.map(t => [t.id, t]));
const J = new Map(DATA.judges.map(j => [j.id, j]));
const R = new Map(DATA.rounds.map(r => [r.seq, r]));
const ST = new Map(DATA.standings.map(s => [s.t, s]));
const CAT = new Map(DATA.categories.map(c => [c.slug, c]));

const PRELIMS = DATA.rounds.filter(r => !r.outround).sort((a, b) => a.seq - b.seq);
const ELIMS = DATA.rounds.filter(r => r.outround).sort((a, b) => a.seq - b.seq);
const SCORED = PRELIMS.filter(r => r.results_public);         // rounds with rankings out
const LAST_SCORED = SCORED.length ? SCORED[SCORED.length - 1].seq : 0;

const team = id => T.get(id) || { id, name: "—", code: "—", inst: "—", cats: [], speakers: [] };
const judge = id => J.get(id) || { id, name: "—", inst: "—", code: "—" };

/* ------------------------------------------------------- per-room derivation */

/** Rank inside a room, from BP points. Nulls when the round's results aren't out. */
function rankRoom(d) {
  const known = d.teams.filter(x => x.pts != null);
  if (known.length !== d.teams.length || !known.length) return new Map();
  const sorted = [...d.teams].sort((a, b) => b.pts - a.pts);
  const m = new Map();
  sorted.forEach((x, i) => m.set(x.t, i + 1));
  return m;
}

/**
 * Who came out of a break room. An elimination result is not a ranking: the
 * ballot says `win` true or false, two through and two out, with no order
 * between the two that advanced and none between the two that did not. So this
 * is a set, not a rank — anything that renders "1st/2nd" off it would be
 * inventing a placing tab never published.
 */
function throughRoom(d) {
  const known = d.teams.filter(x => x.win != null);
  if (known.length !== d.teams.length || !known.length) return new Set();
  return new Set(d.teams.filter(x => x.win).map(x => x.t));
}

const DEBATES = DATA.debates.map((d, i) => {
  const ranks = rankRoom(d);
  const through = throughRoom(d);
  return { ...d, key: `d${i}`, ranks, through,
           decided: ranks.size > 0 || through.size > 0 };
});

/** round seq -> its rooms, in room-name order */
const BY_ROUND = new Map();
for (const d of DEBATES) {
  if (!BY_ROUND.has(d.round)) BY_ROUND.set(d.round, []);
  BY_ROUND.get(d.round).push(d);
}
for (const list of BY_ROUND.values()) {
  list.sort((a, b) => String(a.room).localeCompare(String(b.room), undefined, { numeric: true }));
}

/* --------------------------------------------------------- per-team history --*/

/** One row per round a team appears in: side, room, rank, points, who else was there. */
function historyOf(tid) {
  const out = [];
  for (const d of DEBATES) {
    const mine = d.teams.find(x => x.t === tid);
    if (!mine) continue;
    const r = R.get(d.round) || {};
    out.push({
      seq: d.round, abbr: r.abbr, name: r.name, outround: !!r.outround,
      room: d.room, side: mine.side, pts: mine.pts,
      rank: d.ranks.get(tid) || null,
      through: d.through.size ? d.through.has(tid) : null,   // break rounds: no placing
      opponents: d.teams.filter(x => x.t !== tid),
      panel: d.panel, debate: d,
      silent: !!r.silent && !r.results_public,
    });
  }
  return out.sort((a, b) => a.seq - b.seq);
}

const HIST = new Map();
const hist = tid => {
  if (!HIST.has(tid)) HIST.set(tid, historyOf(tid));
  return HIST.get(tid);
};

/** Rounds a judge sat on, with the position held. */
const JHIST = new Map();
for (const d of DEBATES) {
  for (const p of d.panel) {
    if (!JHIST.has(p.j)) JHIST.set(p.j, []);
    JHIST.get(p.j).push({ seq: d.round, abbr: (R.get(d.round) || {}).abbr, pos: p.pos, debate: d });
  }
}
for (const l of JHIST.values()) l.sort((a, b) => a.seq - b.seq);
const jhist = jid => JHIST.get(jid) || [];

/* ----------------------------------------------------------------- the fold --*/

/** Cumulative points for a team up to and including round `upto`. */
function ptsTo(tid, upto) {
  const by = (ST.get(tid) || {}).by_round || {};
  let n = 0;
  for (const k in by) if (+k <= upto) n += by[k];
  return n;
}

/** How many scored rounds a team actually has by `upto` — catches swings and byes. */
function roundsTo(tid, upto) {
  const by = (ST.get(tid) || {}).by_round || {};
  return Object.keys(by).filter(k => +k <= upto).length;
}

const BREAK_RANK = new Map();     // "slug:teamId" -> break_rank
const BREAK_REMARK = new Map();
for (const slug in DATA.breaks || {}) {
  for (const e of DATA.breaks[slug]) {
    if (e.break_rank != null) BREAK_RANK.set(slug + ":" + e.t, e.break_rank);
    if (e.remark) BREAK_REMARK.set(slug + ":" + e.t, e.remark);
  }
}
const breakRank = (slug, tid) => BREAK_RANK.get(slug + ":" + tid) ?? null;
const announced = slug => (DATA.breaks || {})[slug]?.some(e => e.break_rank != null) || false;

/**
 * The fold for one break category at the end of round `upto`.
 * Teams grouped by points, brackets high to low. Inside a bracket, the announced
 * break order when we have it (that ordering is public), otherwise alphabetical —
 * we never invent a within-bracket order out of numbers we are not allowed to see.
 */
function fold(slug, upto) {
  const cat = CAT.get(slug) || {};
  const rows = DATA.teams
    .filter(t => t.cats.includes(slug))
    .map(t => ({
      t, pts: ptsTo(t.id, upto), rounds: roundsTo(t.id, upto),
      br: breakRank(slug, t.id), remark: BREAK_REMARK.get(slug + ":" + t.id) || null,
    }));

  rows.sort((a, b) =>
    b.pts - a.pts ||
    (a.br == null) - (b.br == null) ||
    (a.br ?? 0) - (b.br ?? 0) ||
    a.t.name.localeCompare(b.t.name));

  rows.forEach((r, i) => { r.pos = i + 1; });

  const brackets = [];
  for (const r of rows) {
    let b = brackets[brackets.length - 1];
    if (!b || b.pts !== r.pts) { b = { pts: r.pts, rows: [] }; brackets.push(b); }
    b.rows.push(r);
  }

  const official = announced(slug) && upto >= LAST_SCORED;
  const size = cat.break_size || 0;
  const breaking = rows.filter(r => r.br != null).length;

  // Where the line sits. The fold is stacked by POINTS, and in a sub-category the
  // top of that stack is not the top of the break: a team that broke Open is out
  // of the EFL break however many points it has, and EFL #7 and #8 then sit below
  // it. So the line goes after the LAST team that actually broke, not after the
  // first `breaking` positions — otherwise real breaking teams end up under it.
  // Each chip still says for itself whether it broke.
  let cut = Math.min(size, rows.length);
  if (official) {
    cut = 0;
    rows.forEach((r, i) => { if (r.br != null) cut = i + 1; });
  }
  const passedOver = official ? cut - breaking : 0;   // above the line, not breaking

  return { cat, rows, brackets, cut, official, size, breaking, passedOver };
}

/**
 * The first break round's rooms, projected from the announced break ranks.
 *
 * British Parliamentary breaks fold inward: with 8 rooms, room 1 is seeds
 * 1-16-17-32, room 2 is 2-15-18-31, and so on down to room 8 with 8-9-24-25.
 * In general room `i` of `R` takes seed `i`, then `2R+1-i`, `2R+i`, `4R+1-i`.
 *
 * This is the format's convention applied to public break ranks — not the tab's
 * draw. It is a projection until tab releases the real thing, and every view
 * that shows it has to say so. Returns null unless the break is fully announced
 * and divides evenly into rooms, because a partial break has no defined fold.
 */
function foldInto(ordered, perRoom) {
  const n = ordered.length;
  if (!n || n % perRoom !== 0) return null;
  const rooms_ = n / perRoom, out = [];
  for (let i = 1; i <= rooms_; i++) {
    const seats = [];
    for (let k = 0; k < perRoom; k++) {
      const pos = (k % 2 === 0) ? i + k * rooms_ : (k + 1) * rooms_ + 1 - i;
      seats.push(ordered[pos - 1]);
    }
    if (seats.some(s => s == null)) return null;
    out.push(seats);
  }
  return out;
}

/** The first break round's rooms, folded straight out of the announced ranks. */
function seedRooms(slug, perRoom) {
  const cat = CAT.get(slug) || {};
  const ranked = ((DATA.breaks || {})[slug] || [])
    .filter(e => e.break_rank != null)
    .sort((a, b) => a.break_rank - b.break_rank);
  if (!ranked.length || ranked.length !== cat.break_size) return null;
  return foldInto(ranked.map(e => ({ seed: e.break_rank, t: e.t })), perRoom);
}

/** Break seed per team, for re-seeding survivors in the simulator. */
const SEED = new Map();
for (const slug in DATA.breaks || {}) {
  for (const e of DATA.breaks[slug]) {
    if (e.break_rank != null) SEED.set(slug + ":" + e.t, e.break_rank);
  }
}
const seedOf = (slug, tid) => SEED.get(slug + ":" + tid) ?? 9999;

/**
 * The order rooms have to be DRAWN in, column by column, so the bracket reads.
 *
 * The rooms pair by folding — room 1 meets room 8, not room 2 — so listing them
 * 1,2,3…8 makes every connector cross something and the whole thing looks broken
 * even when it is right. Working back from the final instead: each room in a
 * column is immediately followed by the room it meets, which puts every pair
 * next to each other and every line straight.
 *
 * counts [8,4,2,1] gives [[1,8,4,5,2,7,3,6], [1,4,2,3], [1,2], [1]].
 *
 * Falls back to plain order for any column that does not exactly halve into the
 * next, since the fold is then undefined.
 */
function bracketOrder(counts) {
  const last = counts.length - 1;
  const orders = counts.map(n => Array.from({ length: n }, (_, i) => i + 1));
  for (let c = last - 1; c >= 0; c--) {
    if (counts[c] !== 2 * counts[c + 1]) break;
    const P = counts[c], out = [];
    for (const p of orders[c + 1]) out.push(p, P + 1 - p);
    orders[c] = out;
  }
  return orders;
}

/**
 * Which room of the fold each one is, from the best break seed sitting in it.
 * The fold puts the best surviving team in room 1, the next in room 2 and so on,
 * so the lowest seed present names the room — and that holds for a released draw
 * as well as a projected one, whatever the venue happens to be called.
 */
function assignFoldIndex(nodes) {
  const known = nodes.length && nodes.every(n =>
    n.seats && n.seats.length && n.seats.every(s => s.seed != null && s.seed < 9999));
  if (!known) { nodes.forEach((n, i) => { n.fi = i + 1; }); return nodes; }
  const mins = nodes.map(n => Math.min(...n.seats.map(s => s.seed)));
  const sorted = [...mins].slice().sort((a, b) => a - b);
  nodes.forEach((n, i) => { n.fi = sorted.indexOf(mins[i]) + 1; });
  return nodes;
}

/**
 * Name each room by its position in the FIXED tree, not by who is standing in it.
 *
 * `assignFoldIndex` is right for the FIRST break round only, where the seeds are
 * the fold. After that it breaks the moment a top seed loses: seed 1 went out in
 * the octofinals, so the quarter fed by rooms 1 and 8 held nothing better than
 * seed 8 and got called "room 4" — which then reordered the column and crossed
 * every connector. A room's number comes from the rooms that feed it: the room
 * fed by `p` and `P+1-p` is room `min(p, P+1-p)`.
 *
 * Returns false, having changed nothing that matters, when the feeders cannot be
 * read off the teams — an unreleased draw — so the caller can fall back.
 */
function assignFoldIndexFromFeeders(nodes, prev) {
  const P = prev.length;
  if (!P || !nodes.length) return false;
  const fis = [];
  for (const n of nodes) {
    const ids = new Set((n.seats || []).map(s => s.t));
    if (!ids.size) return false;
    const kids = prev.filter(p => (p.seats || []).some(s => ids.has(s.t)));
    if (kids.length !== 2) return false;
    fis.push(Math.min(...kids.map(k => Math.min(k.fi, P + 1 - k.fi))));
  }
  if (new Set(fis).size !== nodes.length) return false;   // not a clean pairing
  nodes.forEach((n, i) => { n.fi = fis[i]; });
  return true;
}

/**
 * The plain-English version of the rule, for wherever a projection is shown.
 *
 * Derived from the same snake `foldInto` uses, for however many teams are in a
 * room — so a two-team break reads "room 1 is 1-8" and a four-team break reads
 * "room 1 is 1-16-17-32". Writing the four-team version out by hand was the last
 * thing in the fold engine that assumed a format.
 */
function seedRule(rooms_, perRoom) {
  const seats = perRoom || (DATA.tournament && DATA.tournament.teams_per_debate) || 4;
  if (rooms_ < 2) return "the break folds into one room";
  const ex = i => {
    const out = [];
    for (let k = 0; k < seats; k++) {
      out.push((k % 2 === 0) ? i + k * rooms_ : (k + 1) * rooms_ + 1 - i);
    }
    return out.join("-");
  };
  return `the break folds inward: room 1 is ${ex(1)}, room 2 is ${ex(2)}, `
       + `down to room ${rooms_} at ${ex(rooms_)}`;
}

/* ---------------------------------------------------------- little helpers --*/

const el = (tag, attrs, ...kids) => {
  const n = document.createElement(tag);
  for (const k in (attrs || {})) {
    const v = attrs[k];
    if (v == null || v === false) continue;
    if (k === "class") n.className = v;
    else if (k === "text") n.textContent = v;
    else if (k === "html") n.innerHTML = v;
    else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
    else if (k.startsWith("data") || k === "role" || k.startsWith("aria")) n.setAttribute(k, v);
    else n.setAttribute(k, v);
  }
  for (const c of kids.flat()) {
    if (c == null || c === false) continue;
    n.append(c.nodeType ? c : document.createTextNode(String(c)));
  }
  return n;
};
const q = sel => document.querySelector(sel);
const clear = n => { while (n.firstChild) n.removeChild(n.firstChild); return n; };
const plural = (n, one, many) => `${n} ${n === 1 ? one : (many || one + "s")}`;
const ordinal = pts => (pts == null ? null : ORD[pts] || `${pts}pt`);

function toast(msg) {
  const t = q("#toast");
  t.textContent = msg; t.hidden = false;
  clearTimeout(toast._h);
  toast._h = setTimeout(() => { t.hidden = true; }, 2200);
}

/** Chip for a team, clickable straight into its sheet. */
function teamChip(t, opts) {
  const o = opts || {};
  return el("button", {
    class: "tchip" + (o.breaks ? " breaks" : "") + (o.out ? " out" : "") + (o.me ? " me" : ""),
    title: `${t.long || t.name}${o.title ? " · " + o.title : ""}`,
    onclick: e => { e.stopPropagation(); openTeam(t.id); },
  },
    o.rk != null ? el("span", { class: "rk", text: String(o.rk) }) : null,
    flagMark(t.region),
    el("span", { class: "nm", text: t.name }),
    o.right ? el("span", { class: "rg", text: o.right }) : null);
}

function judgeChip(p, extra) {
  const j = judge(p.j);
  return el("button", {
    class: "jchip " + (p.pos || ""),
    title: `${POS_FULL[p.pos] || "On the panel"} · ${j.inst}`,
    onclick: e => { e.stopPropagation(); openJudge(j.id); },
  }, p.pos ? el("b", { text: p.pos }) : null, j.name,
     extra ? el("span", { class: "rg", text: extra }) : null);
}

/** The big invitation to the simulator. Worth shouting about; it is the fun bit. */
function simCTA(sub) {
  return el("div", { class: "cta" },
    el("div", { class: "cup", "aria-hidden": "true", text: "🏆" }),
    el("div", { class: "txt" },
      el("h3", { text: "Run your own break" }),
      el("p", { text: sub || "Pick who goes through and watch the next round redraw itself, "
        + "all the way to your champion. Yours alone, and shareable as a link." })),
    el("button", { class: "big", onclick: () => { show("sim"); },
      text: "Start picking →" }));
}

function rankBadge(rank) {
  if (!rank) return el("span", { class: "dim tiny", text: "—" });
  return el("span", { class: "rk" + rank, text: ORD[4 - rank] });
}
