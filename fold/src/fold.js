/* ===========================================================================
   fold.js — the fold: every team stacked by points, and the line that cuts it.

   The one screen this site exists for. Drag the round scrubber and watch the
   brackets re-form round by round; the break line is solid once the break has
   been announced and dashed while it is still only a projection off position.
   ========================================================================= */

const foldState = { slug: null, upto: LAST_SCORED, find: "" };

function renderFold() {
  const root = clear(q("#v-fold"));
  const cats = DATA.categories.filter(c => DATA.teams.some(t => t.cats.includes(c.slug)));
  if (!foldState.slug) foldState.slug = (cats.find(c => c.is_general) || cats[0] || {}).slug;

  root.append(nowBand());
  root.append(el("div", { class: "head" },
    el("h2", { text: "The fold" }),
    el("p", {
      text: !SCORED.length
        ? "No round rankings are public yet, so there is no fold to draw. This page fills itself in the moment tab publishes the first round."
        : "Every team stacked by the points they have won, high to low, with the break line cut across it. "
          + "Points come from round rankings on the public tab — nothing here uses speaker scores."
    })));

  if (!SCORED.length) { root.append(el("p", { class: "note warm", text: "Waiting on the tab." })); return; }

  // ---- controls -----------------------------------------------------------
  const seg = el("div", { class: "seg", role: "group" });
  for (const c of cats) {
    seg.append(el("button", {
      text: c.name, "aria-pressed": String(c.slug === foldState.slug),
      onclick: () => { foldState.slug = c.slug; renderFold(); },
    }));
  }
  const slider = el("input", {
    type: "range", min: "1", max: String(LAST_SCORED), value: String(foldState.upto),
    "aria-label": "Show the fold at the end of this round",
    oninput: e => { foldState.upto = +e.target.value; renderFold(); },
  });
  const finder = el("input", {
    type: "search", placeholder: "Find a team in the fold…", value: foldState.find,
    oninput: e => { foldState.find = e.target.value; paintFind(); },
  });
  const stamp = el("span", { class: "pill mute", text: foldState.upto === LAST_SCORED
    ? "after all " + LAST_SCORED + " rounds" : "after R" + foldState.upto });

  root.append(el("div", { class: "bar" },
    el("span", { class: "lab", text: "Break" }), seg,
    el("span", { class: "lab", text: "As at" }), slider, stamp,
    el("span", { class: "spacer", style: "flex:1" }), finder));

  const f = fold(foldState.slug, foldState.upto);
  if (!f.rows.length) { root.append(el("p", { class: "empty", text: "No teams in this category." })); return; }

  // ---- the numbers --------------------------------------------------------
  const onCut = f.rows[f.cut - 1], firstOut = f.rows[f.cut];
  root.append(el("div", { class: "kpis" },
    kpi(f.rows.length, "in the field", f.cat.name + " eligible"),
    kpi(f.official ? f.breaking : (f.size || "—"), "break size",
      f.official ? "announced" : "as configured"),
    kpi(onCut ? onCut.pts : "—", "points on the line",
      onCut ? onCut.t.name + (f.official && onCut.br != null
        ? " breaks " + onCut.br + ", last in" : " sits " + f.cut) : ""),
    kpi(firstOut ? firstOut.pts : "—", "first points out", firstOut ? firstOut.t.name + " sits " + (f.cut + 1) : "everyone breaks"),
    kpi(f.brackets.length, "brackets", "distinct point totals")));

  // ---- the fold itself ----------------------------------------------------
  const wrap = el("div", { class: "foldwrap card", style: "padding:14px 16px" });
  let seen = 0;
  for (const b of f.brackets) {
    const before = seen, after = seen + b.rows.length;
    const splits = before < f.cut && after > f.cut;      // the line falls inside this bracket
    if (splits) {
      wrap.append(bracketRow(b, b.rows.slice(0, f.cut - before), f, before, "top"));
      wrap.append(theLine(f));
      wrap.append(bracketRow(b, b.rows.slice(f.cut - before), f, f.cut, "rest"));
    } else {
      wrap.append(bracketRow(b, b.rows, f, before, null));
      if (after === f.cut) wrap.append(theLine(f));
    }
    seen = after;
  }
  root.append(wrap);

  // ---- who moved ----------------------------------------------------------
  if (foldState.upto > 1) root.append(moversCard(f));

  if (f.official) {
    root.append(el("div", { style: "margin-top:20px" }, simCTA(
      `All ${f.breaking} of them are through to the break rounds. Who wins it? `
      + "Pick your way through every room and watch the next round redraw itself.")));
  }

  root.append(el("p", { class: "note", html:
    "Inside a bracket, teams sit in announced break order where the break is out, and alphabetically where it is not — "
    + "the tab orders tied teams on speaker scores, and those are not public, so this site does not guess at them."
    + (f.passedOver > 0
      ? " The stack is by points, so a team that is out of this break can sit above the line: the line is drawn "
        + "after the last team that actually broke, and every chip says for itself whether it did."
      : "") }));

  paintFind();
}

function kpi(n, k, s) {
  return el("div", { class: "kpi" },
    el("div", { class: "n", text: String(n) }),
    el("div", { class: "k", text: k }),
    s ? el("div", { class: "s", text: s }) : null);
}

function bracketRow(b, rows, f, offset, part) {
  const chips = el("div", { class: "chips" });
  rows.forEach((r, i) => {
    const breaks = f.official && r.br != null;
    const remark = r.remark ? REMARK[r.remark] || r.remark : null;
    const c = teamChip(r.t, {
      rk: r.pos, breaks, out: f.official && r.br == null,
      right: remark || (r.rounds < foldState.upto ? `${r.rounds} rounds` : r.t.code),
      title: `${r.pts} points · ${f.official ? (r.br != null ? "breaks " + r.br : "did not break") : "position " + r.pos}`,
    });
    c.dataset.tid = r.t.id;
    chips.append(c);
  });
  return el("div", { class: "bracketrow" },
    el("div", { class: "bno" },
      el("div", { class: "p", text: String(b.pts) }),
      el("div", { class: "l", text: part === "rest" ? "same bracket" : "points" }),
      el("div", { class: "c", text: plural(rows.length, "team") })),
    chips);
}

function theLine(f) {
  const cls = "theline" + (f.official ? "" : " projected");
  // In a sub-category some teams above the line are not in its break — they broke
  // elsewhere, or were capped. Say so on the line rather than letting the count
  // and the green chips disagree.
  const label = !f.official
    ? `Cut line at ${f.cut} · projection, break not announced`
    : f.passedOver > 0
      ? `The break — ${plural(f.breaking, f.cat.name + " team")}, `
        + `with ${plural(f.passedOver, "team")} above the line out of this break`
      : `The break — top ${f.breaking} ${f.cat.name} teams`;
  return el("div", { class: cls }, el("span", { class: "lab", text: label }));
}

/** Position now vs position one round ago, off public points only. */
function moversCard(f) {
  const prev = fold(foldState.slug, foldState.upto - 1);
  const was = new Map(prev.rows.map(r => [r.t.id, r.pos]));
  const moved = f.rows
    .filter(r => was.has(r.t.id))
    .map(r => ({ r, d: was.get(r.t.id) - r.pos }))
    .filter(x => x.d !== 0);
  const up = [...moved].sort((a, b) => b.d - a.d).slice(0, 6);
  const dn = [...moved].sort((a, b) => a.d - b.d).slice(0, 6);
  const list = (rows, sign) => el("div", { class: "chips" },
    rows.map(x => teamChip(x.r.t, { rk: x.r.pos, right: (sign > 0 ? "▲" : "▼") + Math.abs(x.d) })));
  return el("div", { class: "card", style: "margin-top:16px" },
    el("h3", {}, `Movement over R${foldState.upto}`,
      el("span", { class: "pill mute", text: plural(moved.length, "team") + " changed position" })),
    el("div", { class: "body" },
      el("h4", { text: "Climbed" }), list(up, 1),
      el("h4", { text: "Slipped", style: "margin-top:14px" }), list(dn, -1)));
}

function paintFind() {
  const s = foldState.find.trim().toLowerCase();
  q("#v-fold").querySelectorAll(".tchip[data-tid]").forEach(c => {
    const t = team(+c.dataset.tid);
    const hit = s && (t.name.toLowerCase().includes(s) || (t.inst || "").toLowerCase().includes(s)
      || (t.region || "").toLowerCase().includes(s));
    c.classList.toggle("me", !!hit);
  });
}


/**
 * What is happening right now — the first thing anyone opening this page wants.
 * The "current round" is the tab's own answer, so this band is never ahead of it.
 */
function nowBand() {
  const cur = R.get(DATA.gate.current_round);
  const next = DATA.rounds.find(r => r.seq > (cur ? cur.seq : 0) && !r.completed);
  const band = el("div", { class: "nowband" });

  const bit = (k, v, cls) => el("div", { class: "nb" },
    el("div", { class: "k", text: k }),
    el("div", { class: "v " + (cls || ""), text: v }));

  if (cur) {
    band.append(bit("Round in play", cur.name));
    band.append(bit("Its draw", cur.draw_public ? "published" : cur.draw_status.toLowerCase(),
      cur.draw_public ? "ok" : "wait"));
    band.append(bit("Its rankings", cur.results_public ? "published"
      : (cur.silent ? "silent until announced" : "not in yet"),
      cur.results_public ? "ok" : "wait"));
  }
  if (next) {
    band.append(bit("Up next", next.name + (next.draw_public ? " — draw out" : " — draw not out yet"),
      next.draw_public ? "ok" : "wait"));
  }
  band.append(bit("This page", "keeps itself current", "ok"));
  const goto_ = cur && (cur.draw_public || cur.results_public)
    ? el("button", { class: "ghost", text: "See " + cur.abbr + " room by room →",
        onclick: () => { rdState.seq = cur.seq; invalidate("rounds"); show("rounds"); } })
    : null;
  if (goto_) band.append(el("div", { class: "nb grow" }, goto_));
  return band;
}
