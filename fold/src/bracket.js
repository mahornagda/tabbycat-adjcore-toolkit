/* ===========================================================================
   bracket.js — the break rounds as blocks and lines.

   Two things are true at once and the drawing has to hold both: the *shape* of
   the break rounds is known from the moment the break size is set, while *who
   is in which room* is not ours to show until tab releases that draw. So every
   block exists from the start; a locked block draws dashed and says so, and
   fills in the instant the draw goes public. Nothing drafted internally ever
   reaches this page — build.py cannot even see it.

   Connectors follow the real path where both draws are out (matched on the
   teams that actually advanced) and the structural path where they are not.
   ========================================================================= */

const brState = { slug: null };

function renderBracket() {
  const root = clear(q("#v-bracket"));
  const cats = DATA.categories.filter(c => c.rounds.length);
  if (!brState.slug) brState.slug = (cats.find(c => c.is_general) || cats[0] || {}).slug;

  root.append(el("div", { class: "head" },
    el("h2", { text: "Break rounds" }),
    el("p", { text: "The road to the final. Rooms and panels appear here as tab releases each draw — "
      + "a dashed block is a room that exists but has not been published yet." })));

  if (!cats.length) { root.append(el("p", { class: "empty", text: "This tournament has no break rounds configured." })); return; }

  const seg = el("div", { class: "seg", role: "group" });
  for (const c of cats) {
    seg.append(el("button", {
      text: c.name, "aria-pressed": String(c.slug === brState.slug),
      onclick: () => { brState.slug = c.slug; renderBracket(); },
    }));
  }
  const cat = CAT.get(brState.slug);
  const rounds = ELIMS.filter(r => r.cat === brState.slug);
  root.append(el("div", { class: "bar" },
    el("span", { class: "lab", text: "Category" }), seg,
    el("span", { class: "spacer", style: "flex:1" }),
    el("span", { class: "pill mute", text: plural(cat.break_size, "team") + " break" }),
    el("span", { class: "pill mute", text: plural(rounds.length, "round") + " to the final" })));

  root.append(simCTA("These rooms fill in as tab releases each draw. In the meantime, "
    + "play it out yourself — pick who goes through and every later round redraws itself."));

  const cols = buildTree(rounds);
  const tw = el("div", { class: "treewrap" });
  const tree = el("div", { class: "tree" });
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("class", "links");
  svg.setAttribute("aria-hidden", "true");
  tw.append(svg, tree);

  cols.forEach((col, ci) => {
    const r = col.round;
    const c = el("div", { class: "col" });
    c.append(el("div", { class: "colhead" },
      el("span", { class: "n", text: r.name }),
      el("span", { class: "pill " + (r.draw_public ? "ok" : "mute") + (r.draw_public ? "" : " lock"),
        text: r.draw_public ? "draw out" : r.draw_status.toLowerCase() }),
      r.silent && !r.results_public ? el("span", { class: "pill gold", text: "silent" }) : null));
    const body = el("div", { class: "colbody" });
    col.nodes.forEach((n, i) => {
      n.dom = roomBlock(n, r, i, col.nodes.length);
      n.dom.dataset.fi = String(n.fi || i + 1);      // bracket position, not the venue name
      body.append(n.dom);
    });
    if (col.projected) c.querySelector(".colhead").append(
      el("span", { class: "pill gold", text: "projected from the break" }));
    c.append(body);
    tree.append(c);
  });
  root.append(tw);

  drawLinks(tw, svg, cols);
  const redraw = () => drawLinks(tw, svg, cols);
  addEventListener("resize", redraw, { passive: true });
  requestAnimationFrame(redraw);

  root.append(breakListCard(cat));

  const first = cols[0];
  if (cols.length > 1 && cols.some(c => c.nodes.some(n => n.structural))) {
    const P = cols[0].nodes.length;
    const pairs = [];
    for (let i = 0; i < Math.min(3, Math.floor(P / 2)); i++) {
      pairs.push(`${i + 1} with ${P - i}`);
    }
    root.append(el("p", { class: "note", style: "margin-top:18px", text:
      `Which room meets which: the bracket is fixed the moment the break is announced, and the `
      + `rooms fold the same way the seeds inside them did. `
      + `Room ${pairs.join(", room ")}${P > 6 ? ", and so on" : ""} — the room holding the top `
      + `seed meets the room holding seed ${P}. Nobody is re-seeded between rounds, so this shape `
      + `does not change. Dashed lines are that shape; they turn solid once tab publishes a `
      + `draw and the real path can be read off it. The rooms are listed in bracket order rather `
      + `than 1 to ${P} for the same reason — each room sits next to the one it meets, so no line `
      + `has to cross another.` }));
  }
  if (first && first.projected) {
    root.append(el("p", { class: "note warm", style: "margin-top:18px", text:
      `${first.round.name} is filled in from the announced break, not from the tab: `
      + seedRule(first.nodes.length) + ". " + whichSideSentence()
      + ", and who judges, are tab's to assign — so those stay blank until the draw is "
      + "released, and the real draw replaces this the moment it is." }));
  }
  root.append(el("p", { class: "note", style: "margin-top:10px", html:
    rounds.some(r => !r.draw_public)
      ? "Rooms past the first break round stay empty on purpose. Which room feeds which is fixed and drawn "
        + "above; who is standing in it is not, until the round before has been debated. The adjudication core "
        + "drafts break-round panels well before "
        + "they are announced; this site is built from the public tab only, so those drafts are not in the page "
        + "even in a form you could dig out."
      : "Every break-round draw for this category is public." }));
}

/**
 * One column per break round: rooms drawn in bracket order, so pairs sit adjacent.
 * Real where the draw is public, folded off the break for the first round, plain
 * placeholders after that.
 */
function buildTree(rounds) {
  const perRoom = DATA.tournament.teams_per_debate;
  const counts = rounds.map((r, i) => {
    const real = r.draw_public ? (BY_ROUND.get(r.seq) || []) : [];
    return real.length || r.rooms || 1;
  });
  const orders = bracketOrder(counts);

  // A plain loop, not .map — each column needs the one before it to know its own
  // room numbers, and the fixed tree is what supplies them.
  const cols = [];
  rounds.forEach((r, ri) => {
    const real = r.draw_public ? (BY_ROUND.get(r.seq) || []) : [];
    let nodes;
    if (real.length) {
      nodes = real.map(d => ({
        d, seats: d.teams.map(x => ({ t: x.t, seed: seedOf(r.cat, x.t), side: x.side })),
      }));
    } else {
      const seeded = ri === 0 ? seedRooms(r.cat, perRoom) : null;
      nodes = Array.from({ length: counts[ri] }, (_, i) =>
        ({ d: null, seats: seeded ? seeded[i] : null }));
    }
    // The first round is named by its seeds — that IS the fold. Every later round
    // is named by the two rooms feeding it, so a knocked-out top seed cannot
    // renumber the bracket.
    const prev = ri ? cols[ri - 1].nodes : null;
    if (!prev || !assignFoldIndexFromFeeders(nodes, prev)) assignFoldIndex(nodes);
    const byFi = new Map(nodes.map(n => [n.fi, n]));
    const ordered = (orders[ri] || []).map(fi => byFi.get(fi)).filter(Boolean);
    const out = ordered.length === nodes.length ? ordered : nodes;
    out.forEach((n, k) => { n.slot = k; });
    cols.push({ round: r, nodes: out, projected: out.some(n => n.seats && !n.d) });
  });

  // Who feeds whom: read it off the teams when both draws are known, and off the
  // fold when they are not. Both give the same answer; the fold is the fallback.
  for (let c = 1; c < cols.length; c++) {
    const prev = cols[c - 1], P = prev.nodes.length;
    for (const n of cols[c].nodes) {
      const ids = new Set((n.seats || []).map(s => s.t));
      let kids = ids.size ? prev.nodes.filter(p => (p.seats || []).some(s => ids.has(s.t))) : [];
      n.structural = kids.length === 0;
      if (n.structural) kids = prev.nodes.filter(p => p.fi === n.fi || p.fi === P + 1 - n.fi);
      n.kids = kids;
    }
  }
  return cols;
}

function roomBlock(n, r, i, total) {
  const d = n.d, no = n.fi || i + 1;
  if (!d) {
    const head = el("div", { class: "rh" },
      el("span", { class: "rn", text: r.abbr + " room " + no }),
      el("span", { class: "spacer", style: "flex:1" }),
      el("span", { class: "pill " + (n.seats ? "gold" : "mute lock"),
        text: n.seats ? "projected" : "not released" }));
    if (!n.seats) {
      return el("div", { class: "room locked" }, head,
        el("div", { class: "lockbody" },
          el("span", {}, el("b", { text: DATA.tournament.teams_per_debate + " teams" }), " to be drawn"),
          el("span", { text: "panel published with the draw" })));
    }
    // Projected off the announced break: seeds and names, deliberately no sides
    // (tab assigns those) and no panel.
    const slots = el("div", { class: "slots" });
    for (const s of n.seats) {
      const t = team(s.t);
      slots.append(el("div", { class: "slot proj", onclick: () => openTeam(s.t),
        title: `Break seed ${s.seed} · ${t.inst}`,
 },
        el("span", { class: "sd", text: "#" + s.seed }),
        el("span", { class: "nm" }, flagMark(t.region), t.name),
        el("span", { class: "rkb", text: t.code })));
    }
    return el("div", { class: "room locked seeded" }, head, slots,
      el("div", { class: "panelrow" },
        el("span", { class: "tiny dim", text: "sides and panel come with the draw" })));
  }
  const box = el("div", { class: "room" });
  box.append(el("div", { class: "rh" },
    el("span", { class: "rn", text: d.room || r.abbr + " room " + no }),
    el("span", { class: "spacer", style: "flex:1" }),
    d.decided ? el("span", { class: "pill ok", text: d.through.size ? "through" : "result out" })
              : el("span", { class: "pill mute", text: r.results_public ? "no result" : "in the room" })));
  const slots = el("div", { class: "slots" });
  for (const x of d.teams) {
    const t = team(x.t);
    const rank = d.ranks.get(x.t) || null;
    const br = breakRank(r.cat, x.t);
    // A break room has no 1st/2nd/3rd/4th — the ballot says through or out, and
    // the two that advanced are not ranked against each other.
    const through = d.through.size ? d.through.has(x.t) : null;
    const won = through != null ? through : (rank != null && rank <= 2);
    slots.append(el("div", {
      class: "slot " + (x.side || "") + (won ? " won" : "") + (through === false ? " gone" : ""),
      onclick: () => openTeam(x.t), title: SIDE_FULL[x.side] || "",
    },
      el("span", { class: "sd", text: SIDE_LABEL[x.side] || "?" }),
      el("span", { class: "nm" }, flagMark(t.region), t.name),
      el("span", { class: "rkb", text: through != null ? (through ? "through" : "out")
                                     : rank ? ORD[4 - rank] : (br ? "#" + br : "") })));
  }
  box.append(slots);
  box.append(el("div", { class: "panelrow" },
    d.panel.length ? d.panel.map(p => judgeChip(p)) : el("span", { class: "tiny dim", text: "panel not published" })));
  return box;
}

/** Elbow connectors, measured off the rendered boxes so they always line up. */
function drawLinks(wrap, svg, cols) {
  const base = wrap.getBoundingClientRect();
  const W = wrap.scrollWidth, H = wrap.scrollHeight;
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  svg.setAttribute("width", W); svg.setAttribute("height", H);
  svg.style.width = W + "px"; svg.style.height = H + "px";
  clear(svg);
  const box = n => {
    const b = n.dom.getBoundingClientRect();
    return { x1: b.left - base.left + wrap.scrollLeft, x2: b.right - base.left + wrap.scrollLeft,
             y: b.top - base.top + wrap.scrollTop + b.height / 2 };
  };
  for (let i = 1; i < cols.length; i++) {
    for (const n of cols[i].nodes) {
      const p = box(n);
      for (const k of (n.kids || [])) {
        const c = box(k);
        const mx = c.x2 + (p.x1 - c.x2) / 2;
        svg.append(document.createElementNS("http://www.w3.org/2000/svg", "path"));
        const path = svg.lastChild;
        path.setAttribute("d", `M${c.x2} ${c.y} H${mx} V${p.y} H${p.x1}`);
        path.setAttribute("fill", "none");
        path.setAttribute("stroke", n.structural ? "var(--rule-2)" : "var(--teal)");
        path.setAttribute("stroke-width", n.structural ? "1.5" : "2");
        path.setAttribute("stroke-linecap", "round");
        if (n.structural) path.setAttribute("stroke-dasharray", "4 5");
      }
    }
  }
}

/** The break itself — public, and the thing everyone wants to read. */
function breakListCard(cat) {
  const rows = (DATA.breaks || {})[cat.slug] || [];
  const inBreak = rows.filter(r => r.break_rank != null).sort((a, b) => a.break_rank - b.break_rank);
  const body = el("div", { class: "body" });
  if (!inBreak.length) {
    body.append(el("p", { class: "note warm", text: "The " + cat.name + " break has not been announced." }));
  } else {
    body.append(el("div", { class: "chips" },
      inBreak.map(r => teamChip(team(r.t), { rk: r.break_rank, breaks: true, right: team(r.t).region || team(r.t).code }))));
    const others = rows.filter(r => r.break_rank == null && r.remark);
    if (others.length) {
      body.append(el("h4", { text: "In the standings, out of this break", style: "margin-top:16px" }));
      body.append(el("div", { class: "chips" },
        others.map(r => teamChip(team(r.t), { rk: r.rank, out: true, right: REMARK[r.remark] || r.remark }))));
    }
  }
  return el("div", { class: "card", style: "margin-top:20px" },
    el("h3", {}, "Who broke — " + cat.name,
      el("span", { class: "pill " + (inBreak.length ? "ok" : "mute"),
        text: inBreak.length ? plural(inBreak.length, "team") : "not announced" })),
    body);
}

/**
 * Naming the four benches of a four-team format only reads correctly at a
 * four-team tournament. The side codes travel in the payload, so the sentence
 * is built from them and says the right thing at a two-team one too.
 */
function whichSideSentence() {
  const sides = ((DATA.tournament || {}).sides || []).map(s => String(s).toUpperCase());
  if (!sides.length) return "Which side each team takes";
  if (sides.length === 1) return "Which team sits where";
  return "Which team sits " + sides.slice(0, -1).join(", ") + " or " + sides[sides.length - 1];
}
