/* ===========================================================================
   sim.js — "who do you think goes through?"

   A separate tab on purpose. The Break rounds view is only ever what tab has
   said; this one is only ever the reader's own guess, and nothing here is written
   anywhere but their own browser. Picks live in localStorage and in a short code
   they can put in a link.

   The bracket is FIXED the moment the break is announced. The break folds once,
   into the first break round's rooms, and after that it is the ROOMS that fold:
   room `i` of a round and room `P+1-i` feed room `i` of the next one, all the way
   to the final. Nobody is re-seeded between rounds — a team carries its break seed
   with it and its path is knowable from the start. Where tab HAS published a
   result, the sim locks that round to what actually happened instead of asking.
   ========================================================================= */

const simState = { slug: null, adv: {} };
const SIM_KEY = "fold-sim-v1";

function simRounds(slug) { return ELIMS.filter(r => r.cat === slug); }

/** How many of a room's teams go through — one, in the final. */
function advPerRoom(slug, k) {
  return k === simRounds(slug).length - 1 ? 1 : 2;
}

/**
 * The rooms of break round `k`: the real draw, else the break fold for the first
 * round, else the fixed bracket applied to the round before it.
 *
 * The fold happens ONCE, at the break. After that the bracket is a fixed tree and
 * it is the rooms that fold into each other: room `i` and room `P+1-i` of a round
 * with `P` rooms both feed room `i` of the next. Survivors are not re-seeded and
 * not re-sorted into new brackets — that would make a team's path unknowable, and
 * it is not how the tournament is run.
 *
 * Returns an array with one entry per room, `null` for a room whose feeders are
 * not settled yet, so half a round can still fill in the half of the next round
 * it decides.
 */
function simRoomsAt(slug, k) {
  const rounds = simRounds(slug);
  const perRoom = DATA.tournament.teams_per_debate;
  const r = rounds[k];
  if (!r) return null;

  // A released draw has to come back in the bracket's own order, so index 0 is
  // room 1 whatever the venue is called. For the first break round that is the
  // best seed in the room. After that it is the two rooms feeding it — naming by
  // seed renumbers the whole column the moment a top seed is knocked out.
  const real = BY_ROUND.get(r.seq) || [];
  if (r.draw_public && real.length) {
    const nodes = real.map(d =>
      ({ seats: d.teams.map(x => ({ t: x.t, seed: seedOf(slug, x.t), side: x.side })) }));
    const prev = k ? simRoomsAt(slug, k - 1) : null;
    const prevNodes = prev && prev.every(Boolean)
      ? prev.map((seats, i) => ({ seats, fi: i + 1 })) : null;
    if (!prevNodes || !assignFoldIndexFromFeeders(nodes, prevNodes)) {
      nodes.forEach(n => { n.fi = Math.min(...n.seats.map(s => s.seed)); });
      const order = [...nodes].sort((a, b) => a.fi - b.fi);
      nodes.forEach(n => { n.fi = order.indexOf(n) + 1; });
    }
    return [...nodes].sort((a, b) => a.fi - b.fi).map(n => n.seats);
  }
  if (k === 0) {
    const seeded = seedRooms(slug, perRoom);
    return seeded && seeded.map(rm => rm.map(s => ({ t: s.t, seed: s.seed })));
  }

  const prev = simRoomsAt(slug, k - 1);
  const adv = simRoomAdvancers(slug, k - 1);
  if (!prev || !adv) return null;
  const P = prev.length;
  if (P < 2 || P % 2) return null;

  const out = [];
  for (let i = 1; i <= P / 2; i++) {
    const a = adv[i - 1], b = adv[P - i];          // room i meets room P+1-i
    if (!a || !b) { out.push(null); continue; }
    const seats = [...a, ...b]
      .map(t => ({ t, seed: seedOf(slug, t) }))
      .sort((x, y) => x.seed - y.seed);
    out.push(seats.length === perRoom ? seats : null);
  }
  return out;
}

/**
 * Who leaves each room of round `k`, room by room — tab's answer where it has
 * published one, otherwise the reader's picks. A room that is not settled yet
 * comes back as `null`; the rooms around it still resolve.
 */
function simRoomAdvancers(slug, k) {
  const rounds = simRounds(slug), r = rounds[k];
  if (!r) return null;
  const rooms = simRoomsAt(slug, k);
  if (!rooms) return null;
  const want = advPerRoom(slug, k);
  const real = simResult(slug, k);
  const picked = new Set(simState.adv[r.abbr] || []);

  return rooms.map(seats => {
    if (!seats) return null;
    const here = simRoomDecided(real, seats)
      ? seats.filter(s => real.get(s.t))                // tab has actually answered
      : seats.filter(s => picked.has(s.t));             // still the reader's to guess
    return here.length === want ? here.map(s => s.t) : null;
  });
}

/**
 * team -> rank for round `k`, but ONLY where a result really exists.
 *
 * `results_public` is not the same thing as "the result is in". On 27 Aug tab
 * un-silenced the octofinals before a single ballot was confirmed: the round read
 * as public while every `pts` was still null. Treating that as tab's answer locked
 * the reader out of picking and left every later round waiting forever. So the
 * ranks decide, not the flag — and it is per room, because ballots come in one
 * room at a time.
 */
function simResult(slug, k) {
  const r = simRounds(slug)[k], m = new Map();
  if (!r || !r.results_public) return m;
  for (const d of (BY_ROUND.get(r.seq) || [])) {
    if (!d.decided) continue;
    // A break round is decided by `win`; fall back to the BP ranking for a
    // category that somehow runs its elims on points.
    if (d.through.size) for (const x of d.teams) m.set(x.t, d.through.has(x.t));
    else d.ranks.forEach((rk, tid) => m.set(tid, rk <= advPerRoom(slug, k)));
  }
  return m;
}

/** True when this particular room's result is in — the reader cannot overrule it. */
function simRoomDecided(real, seats) {
  return !!seats && seats.every(s => real.has(s.t));
}

/** Everyone through round `k`, or null while any room in it is still open. */
function simAdvancers(slug, k) {
  const per = simRoomAdvancers(slug, k);
  if (!per || !per.length || per.some(x => !x)) return null;
  return per.flat();
}

/** True when EVERY room of the round has a real result — see simRanks on why. */
function simLocked(slug, k) {
  const rooms = simRoomsAt(slug, k);
  if (!rooms || !rooms.length) return false;
  const real = simResult(slug, k);
  return real.size > 0 && rooms.every(seats => simRoomDecided(real, seats));
}

function simToggle(slug, k, tid) {
  const r = simRounds(slug)[k];
  const want = advPerRoom(slug, k);
  const rooms = simRoomsAt(slug, k) || [];
  const room = rooms.find(seats => seats && seats.some(s => s.t === tid));
  if (!room) return;

  const cur = simState.adv[r.abbr] || [];
  const inRoom = room.map(s => s.t);
  let next = cur.filter(x => x !== tid);
  if (next.length === cur.length) {                 // was not picked — pick it
    const mine = next.filter(x => inRoom.includes(x));
    if (mine.length >= want) next = next.filter(x => x !== mine[0]);   // drop the oldest
    next.push(tid);
  }
  simState.adv[r.abbr] = next;
  simSave();
  renderSim();
}

/** Fill in chalk picks without touching the DOM — used by the tests and by simChalk. */
function simChalkQuiet(slug) {
  simState.adv = {};
  simRounds(slug).forEach((r, k) => {
    const rooms = simRoomsAt(slug, k);
    if (!rooms) return;
    const want = advPerRoom(slug, k), out = [];
    for (const seats of rooms) {
      if (!seats) continue;
      out.push(...[...seats].sort((a, b) => a.seed - b.seed).slice(0, want).map(s => s.t));
    }
    simState.adv[r.abbr] = out;
  });
}

/** Advance the best-seeded teams in every room, all the way down. */
function simChalk(slug) { simChalkQuiet(slug); simSave(); renderSim(); }

function simRandom(slug) {
  simState.adv = {};
  simRounds(slug).forEach((r, k) => {
    const rooms = simRoomsAt(slug, k);
    if (!rooms) return;
    const want = advPerRoom(slug, k), out = [];
    for (const seats of rooms) {
      if (!seats) continue;
      const pool = [...seats];
      for (let i = 0; i < want && pool.length; i++) {
        out.push(pool.splice(Math.floor(Math.random() * pool.length), 1)[0].t);
      }
    }
    simState.adv[r.abbr] = out;
  });
  simSave(); renderSim();
}

function simClear() {
  simState.adv = {};
  simSave();
  // Drop the shared code from the address bar too, or a reload brings the old
  // picks straight back and it looks like Clear did nothing.
  if (location.hash.startsWith("#sim=")) {
    history.replaceState(null, "", location.pathname + location.search);
  }
  renderSim();
}

/* --------------------------------------------------- saving and sharing ----- */

function simSave() {
  try { localStorage.setItem(SIM_KEY, JSON.stringify(simState)); } catch (e) { /* private window */ }
}

function simRestore() {
  try {
    const s = JSON.parse(localStorage.getItem(SIM_KEY) || "null");
    if (s && s.adv) { simState.adv = s.adv; if (s.slug) simState.slug = s.slug; }
  } catch (e) { /* nothing saved, or unreadable */ }
}

/**
 * Picks as seat numbers, round by round — short enough to live in a link.
 * Exactly `want` characters per settled room, `x` for a seat not picked yet, so a
 * half-finished round cannot shift everything after it by a digit.
 */
function simCode(slug) {
  let out = "";
  simRounds(slug).forEach((r, k) => {
    const rooms = simRoomsAt(slug, k);
    if (!rooms) return;
    const want = advPerRoom(slug, k);
    const picked = new Set(simState.adv[r.abbr] || []);
    for (const seats of rooms) {
      if (!seats) continue;
      const seatsPicked = [];
      seats.forEach((s, i) => { if (picked.has(s.t)) seatsPicked.push(String(i)); });
      while (seatsPicked.length < want) seatsPicked.push("x");
      out += seatsPicked.slice(0, want).join("");
    }
  });
  return slug + "." + out;
}

function simFromCode(code) {
  const [slug, digits] = String(code || "").split(".");
  if (!CAT.has(slug) || !digits) return false;
  simState.slug = slug;
  simState.adv = {};
  let p = 0;
  for (const [k, r] of simRounds(slug).entries()) {
    const rooms = simRoomsAt(slug, k);
    if (!rooms) break;
    const want = advPerRoom(slug, k), out = [];
    for (const seats of rooms) {
      if (!seats) continue;
      for (let i = 0; i < want; i++) {
        const ch = digits[p++];
        const seat = ch === "x" ? null : seats[+ch];
        if (seat) out.push(seat.t);
      }
    }
    simState.adv[r.abbr] = out;
  }
  simSave();
  return true;
}

function simShare(slug) {
  const url = location.origin + location.pathname + "#sim=" + simCode(slug);
  history.replaceState(null, "", "#sim=" + simCode(slug));
  if (navigator.clipboard) {
    navigator.clipboard.writeText(url)
      .then(() => toast("Link copied — it carries your picks"))
      .catch(() => toast("Your picks are in the address bar — copy the link"));
  } else {
    toast("Your picks are in the address bar — copy the link");
  }
}

/* ------------------------------------------------------------------ render -- */

function renderSim() {
  const root = clear(q("#v-sim"));
  const cats = DATA.categories.filter(c => c.rounds.length);
  if (!simState.slug || !CAT.has(simState.slug)) {
    simState.slug = (cats.find(c => c.is_general) || cats[0] || {}).slug;
  }
  const slug = simState.slug;

  root.append(el("div", { class: "head" },
    el("h2", { text: "Run your own break" }),
    el("p", { text: "Click the teams you think go through and the next round redraws itself. "
      + "This is yours alone — it is kept in your browser, it is never sent anywhere, and it has "
      + "nothing to do with what the adjudication core has drawn." })));

  if (!cats.length || !simRounds(slug).length) {
    root.append(el("p", { class: "empty", text: "This tournament has no break rounds to simulate." }));
    return;
  }
  if (!simRoomsAt(slug, 0)) {
    root.append(el("p", { class: "note warm", text:
      "The break for this category has not been announced yet, so there is nothing to start from. "
      + "Come back once it is out." }));
    return;
  }

  const seg = el("div", { class: "seg", role: "group" });
  for (const c of cats) {
    seg.append(el("button", { text: c.name, "aria-pressed": String(c.slug === slug),
      onclick: () => { simState.slug = c.slug; simSave(); renderSim(); } }));
  }
  root.append(el("div", { class: "bar" },
    el("span", { class: "lab", text: "Break" }), seg,
    el("span", { class: "spacer", style: "flex:1" }),
    el("button", { class: "ghost", text: "Chalk — best seed wins", onclick: () => simChalk(slug) }),
    el("button", { class: "ghost", text: "Surprise me", onclick: () => simRandom(slug) }),
    el("button", { class: "ghost", text: "Share", onclick: () => simShare(slug) }),
    el("button", { class: "ghost", text: "Clear", onclick: simClear })));

  const rounds = simRounds(slug);
  const counts = rounds.map((r, k) => (simRoomsAt(slug, k) || []).length || r.rooms || 1);
  const orders = bracketOrder(counts);
  const tw = el("div", { class: "treewrap" });
  const tree = el("div", { class: "tree" });
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("class", "links");
  svg.setAttribute("aria-hidden", "true");
  tw.append(svg, tree);

  const cols = [];
  rounds.forEach((r, k) => {
    const rooms = simRoomsAt(slug, k);
    const ranks = simResult(slug, k);
    const locked = simLocked(slug, k);
    const want = advPerRoom(slug, k);
    const settled = (simRoomAdvancers(slug, k) || []).filter(Boolean).flat();
    // Decided rooms show their result; the rest stay the reader's to pick, even in
    // a round tab has already flagged public but not yet filled in.
    const picked = new Set([...settled.filter(t => ranks.has(t)),
                            ...(simState.adv[r.abbr] || [])]);

    const col = el("div", { class: "col" });
    col.append(el("div", { class: "colhead" },
      el("span", { class: "n", text: r.name }),
      locked ? el("span", { class: "pill ok", text: "as it happened" })
             : ranks.size
               ? el("span", { class: "pill gold", text: "results coming in — pick the rest" })
               : el("span", { class: "pill plum", text: want === 1 ? "pick the winner" : "pick 2 per room" })));

    const body = el("div", { class: "colbody" });
    const nodes = [];
    if (!rooms) {
      body.append(waitingRoom(r.abbr, "finish " + rounds[k - 1].abbr + " first"));
    } else {
      // Drawn in bracket order so each room sits beside the one it meets.
      const order = (orders[k] || []).length === rooms.length
        ? orders[k] : rooms.map((_, i) => i + 1);
      const P = (simRoomsAt(slug, k - 1) || []).length;
      order.forEach((fi, slot) => {
        const seats = rooms[fi - 1];
        if (!seats) {
          // The bracket is fixed, so we can name exactly which two rooms decide
          // this one even before anybody has picked in them.
          body.append(waitingRoom(r.abbr + " room " + fi,
            P ? `waiting on ${rounds[k - 1].abbr} rooms ${fi} and ${P + 1 - fi}`
              : "waiting on the round before"));
          return;
        }
        const n = { slot, fi, seats };
        n.dom = simRoom(slug, k, fi, seats, picked, want, simRoomDecided(ranks, seats));
        nodes.push(n);
        body.append(n.dom);
      });
    }
    col.append(body);
    tree.append(col);
    cols.push({ round: r, nodes });
  });

  // Real advancement lines: a room's children are the previous rooms its teams came from.
  for (let i = 1; i < cols.length; i++) {
    for (const n of cols[i].nodes) {
      const ids = new Set(n.seats.map(s => s.t));
      n.kids = cols[i - 1].nodes.filter(p => p.seats.some(s => ids.has(s.t)));
    }
  }
  root.append(tw);
  const redraw = () => drawLinks(tw, svg, cols);
  addEventListener("resize", redraw, { passive: true });
  requestAnimationFrame(redraw);

  root.append(championCard(slug));
  const P0 = (simRoomsAt(slug, 0) || []).length;
  root.append(el("p", { class: "note", style: "margin-top:16px", text:
    "How the bracket works: it is fixed the moment the break is announced. The break folds once, "
    + "into " + rounds[0].abbr + " — " + seedRule(P0) + ". After that nobody is re-seeded: it is the "
    + "rooms that fold, so " + rounds[0].abbr + " room 1 meets room " + P0 + ", room 2 meets room "
    + (P0 - 1) + ", and so on down the draw, and the winners of those two rooms make up the next "
    + "round's room 1. A team's whole possible path is therefore knowable from the break. The rooms "
    + "are listed in bracket order — each one next to the room it meets — which is why the numbers "
    + "run 1, " + P0 + ", 4, 5 rather than 1, 2, 3, 4." }));
}

/** A room whose feeders have not been settled yet — named, because the tree is fixed. */
function waitingRoom(label, why) {
  return el("div", { class: "room locked" },
    el("div", { class: "rh" },
      el("span", { class: "rn", text: label }),
      el("span", { class: "spacer", style: "flex:1" }),
      el("span", { class: "pill mute lock", text: "waiting" })),
    el("div", { class: "lockbody" }, el("span", { text: why })));
}

function simRoom(slug, k, no, seats, picked, want, locked) {
  const r = simRounds(slug)[k];
  const done = seats.filter(s => picked.has(s.t)).length;
  const box = el("div", { class: "room sim" + (done === want ? " settled" : "") });
  box.append(el("div", { class: "rh" },
    el("span", { class: "rn", text: r.abbr + " room " + no }),
    el("span", { class: "spacer", style: "flex:1" }),
    el("span", { class: "pill " + (done === want ? "ok" : "mute"),
      text: locked ? "result" : `${done}/${want} through` })));

  const slots = el("div", { class: "slots" });
  for (const s of seats) {
    const t = team(s.t);
    const on = picked.has(s.t);
    slots.append(el("div", {
      class: "slot pick" + (on ? " through" : "") + (locked ? " fixed" : ""),
      role: locked ? null : "checkbox", "aria-checked": locked ? null : String(on),
      tabindex: locked ? null : "0",
      title: locked ? `Break seed ${s.seed}` : (on ? "Through — click to undo" : "Click to send them through"),
      onclick: locked ? () => openTeam(s.t) : () => simToggle(slug, k, s.t),
      onkeydown: locked ? null : e => {
        if (e.key === " " || e.key === "Enter") { e.preventDefault(); simToggle(slug, k, s.t); }
      },
    },
      el("span", { class: "sd", text: "#" + s.seed }),
      el("span", { class: "nm" }, flagMark(t.region), t.name),
      el("span", { class: "rkb", text: on ? "✓" : "" })));
  }
  box.append(slots);
  return box;
}

function championCard(slug) {
  const rounds = simRounds(slug);
  const last = rounds[rounds.length - 1];
  const champs = simAdvancers(slug, rounds.length - 1);
  const body = el("div", { class: "body" });
  if (!champs || !champs.length) {
    body.append(el("p", { class: "note", text:
      "Work your way down to " + last.name + " and pick a winner." }));
  } else {
    const t = team(champs[0]);
    body.append(el("div", { class: "champ" },
      el("div", { class: "cup", text: "🏆" }),
      el("div", {},
        el("div", { class: "who" }, flagMark(t.region), t.name),
        el("div", { class: "tiny dim", text: `${t.inst} · broke ${
          breakRank(slug, t.id) != null ? "#" + breakRank(slug, t.id) : "—"}` }),
        el("button", { class: "linkish", style: "margin-top:6px",
          text: "see their tournament →", onclick: () => openTeam(t.id) }))));
  }
  return el("div", { class: "card", style: "margin-top:20px" },
    el("h3", {}, "Your champion",
      el("span", { class: "pill mute", text: "kept in your browser only" })), body);
}
