/* ===========================================================================
   sheets.js — the click-through: one team's whole tournament, one judge's whole
   tournament. Everything in here is assembled from the same public rows the
   tables above use; opening a sheet fetches nothing, because there is nothing
   to fetch.
   ========================================================================= */

function openSheet(build, key) {
  const wrap = q("#sheetwrap"), sheet = clear(q("#sheet"));
  build(sheet);
  wrap.hidden = false;
  document.body.style.overflow = "hidden";
  sheet.focus();
  if (key) history.replaceState(null, "", key);
}

function closeSheet() {
  q("#sheetwrap").hidden = true;
  document.body.style.overflow = "";
  if (location.hash) history.replaceState(null, "", location.pathname + location.search);
}

function sheetHead(title, meta, pills) {
  return el("div", { class: "sh" },
    el("button", { class: "x", "aria-label": "Close", onclick: closeSheet, text: "✕" }),
    el("h2", { text: title }),
    meta ? el("p", { class: "meta", text: meta }) : null,
    pills && pills.length ? el("div", { class: "pills" }, pills) : null);
}

const stat = (n, k) => el("div", { class: "stat" },
  el("div", { class: "n", text: String(n) }), el("div", { class: "k", text: k }));

/* ------------------------------------------------------------------- team --- */

function openTeam(tid) {
  const t = team(tid), h = hist(tid), s = ST.get(tid) || { pts: 0, by_round: {} };
  const tl = tally(tid);

  openSheet(sheet => {
    const pills = [];
    for (const c of DATA.categories) {
      if (!t.cats.includes(c.slug)) continue;
      const br = breakRank(c.slug, tid);
      const rem = BREAK_REMARK.get(c.slug + ":" + tid);
      if (br != null) pills.push(el("span", { class: "pill ok", text: `Broke ${c.name} #${br}` }));
      else if (announced(c.slug)) pills.push(el("span", { class: "pill mute",
        text: rem ? `${c.name} — ${REMARK[rem] || rem}` : `Did not break ${c.name}` }));
      else pills.push(el("span", { class: "pill mute", text: c.name + " eligible" }));
    }
    pills.push(el("span", { class: "pill warm", text: s.pts + " points" }));
    const pos = foldPosition(tid);
    if (pos) pills.push(el("span", { class: "pill plum", text: pos }));

    sheet.append(sheetHead(t.name,
      [t.long !== t.name ? t.long : null, t.inst, t.region].filter(Boolean).join(" · "), pills));

    const body = el("div", { class: "sb" });

    if (t.speakers && t.speakers.length) {
      body.append(el("div", {}, el("h4", { text: "Speaking for them" }),
        el("p", { style: "margin:0", text: t.speakers.join(" · ") })));
    }

    body.append(el("div", {}, el("h4", { text: "How the points landed" }),
      el("div", { class: "grid2" },
        stat(s.pts, "points"), stat(tl.firsts, "firsts"), stat(tl.seconds, "seconds"),
        stat(tl.thirds, "thirds"), stat(tl.fourths, "fourths"),
        stat(tl.rounds, "ranked rounds"))));

    if (tl.rounds > 1) body.append(el("div", {}, el("h4", { text: "Their path" }), pathChart(tid)));

    body.append(el("div", {}, el("h4", { text: "Round by round" }), roundTable(h)));

    const faced = new Map();
    for (const x of h) for (const o of x.opponents) faced.set(o.t, (faced.get(o.t) || 0) + 1);
    if (faced.size) {
      body.append(el("div", {}, el("h4", { text: `Teams faced — ${faced.size} of them` }),
        el("div", { class: "oppgrid" },
          [...faced.entries()].sort((a, b) => b[1] - a[1] || team(a[0]).name.localeCompare(team(b[0]).name))
            .map(([id, n]) => teamChip(team(id), { right: n > 1 ? n + "×" : team(id).code })))));
    }

    const seen = new Map();
    for (const x of h) for (const p of x.panel) seen.set(p.j, (seen.get(p.j) || 0) + 1);
    if (seen.size) {
      body.append(el("div", {}, el("h4", { text: `Judged by — ${seen.size} judges` }),
        el("div", { class: "oppgrid" },
          [...seen.entries()].sort((a, b) => b[1] - a[1])
            .map(([id, n]) => judgeChip({ j: id }, n > 1 ? n + "×" : null)))));
    }
    sheet.append(body);
  }, "#team-" + tid);
}

/** Where they sit in the fold now, in the category that fits them best. */
function foldPosition(tid) {
  const t = team(tid);
  for (const c of DATA.categories) {
    if (!t.cats.includes(c.slug)) continue;
    const f = fold(c.slug, LAST_SCORED);
    const row = f.rows.find(r => r.t.id === tid);
    if (row) return `${row.pos} of ${f.rows.length} in ${c.name}`;
  }
  return null;
}

function roundTable(h) {
  const table = el("table");
  table.append(el("thead", {}, el("tr", {},
    el("th", { text: "Rd" }), el("th", { text: "Room" }), el("th", { text: "Side" }),
    el("th", { class: "num", text: "Came" }), el("th", { class: "num", text: "Pts" }),
    el("th", { text: "In the room with" }), el("th", { text: "Panel" }))));
  const tb = el("tbody");
  let run = 0;
  for (const x of h) {
    if (x.pts != null) run += x.pts;
    tb.append(el("tr", {},
      el("td", {}, el("b", { text: x.abbr })),
      el("td", { class: "mono tiny", text: x.room || "—" }),
      el("td", {}, el("span", { class: "pill mute", text: SIDE_LABEL[x.side] || "—" })),
      el("td", { class: "num" }, x.through != null
        ? el("span", { class: "pill " + (x.through ? "ok" : "mute"),
                       text: x.through ? "through" : "out" })
        : x.rank ? rankBadge(x.rank)
        : el("span", { class: "tiny dim", text: x.silent ? "silent" : "—" })),
      el("td", { class: "num", text: x.pts == null ? "—" : `${x.pts} (${run})` }),
      el("td", {}, el("span", { class: "oppgrid" },
        x.opponents.map(o => teamChip(team(o.t), {
          right: SIDE_LABEL[o.side], out: x.rank && o.pts != null && o.pts < x.pts })))),
      el("td", {}, el("span", { class: "oppgrid" },
        x.panel.length ? x.panel.map(p => judgeChip(p)) : el("span", { class: "tiny dim", text: "—" })))));
  }
  table.append(tb);
  return el("div", { class: "tblwrap card" }, table);
}

/** Cumulative points against the field's average pace — public points only. */
function pathChart(tid) {
  const W = 640, H = 170, pad = { l: 34, r: 12, t: 12, b: 26 };
  const rounds = SCORED.map(r => r.seq);
  const by = (ST.get(tid) || {}).by_round || {};
  const maxPts = Math.max(3 * rounds.length, 1);
  const xs = i => pad.l + (rounds.length > 1 ? i * (W - pad.l - pad.r) / (rounds.length - 1) : 0);
  const ys = v => H - pad.b - (v / maxPts) * (H - pad.t - pad.b);

  let run = 0;
  const pts = rounds.map((sq, i) => { run += (by[String(sq)] || 0); return [xs(i), ys(run), run, sq]; });

  // the field's average pace, so a team's line has something to sit against
  const avg = rounds.map((sq, i) => {
    let tot = 0, n = 0;
    for (const s of DATA.standings) { const v = ptsTo(s.t, sq); if (v != null) { tot += v; n++; } }
    return [xs(i), ys(n ? tot / n : 0)];
  });

  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", "Cumulative points by round");
  const add = (tag, attrs, text) => {
    const n = document.createElementNS(ns, tag);
    for (const k in attrs) n.setAttribute(k, attrs[k]);
    if (text != null) n.textContent = text;
    svg.append(n);
    return n;
  };
  for (let v = 0; v <= maxPts; v += 3) {
    add("line", { x1: pad.l, x2: W - pad.r, y1: ys(v), y2: ys(v), stroke: "var(--rule)", "stroke-width": 1 });
    add("text", { x: pad.l - 7, y: ys(v) + 4, "text-anchor": "end", fill: "var(--ink-3)",
      "font-size": 10, "font-family": "var(--mono)" }, String(v));
  }
  add("path", { d: "M" + avg.map(p => p.join(" ")).join(" L "), fill: "none",
    stroke: "var(--rule-2)", "stroke-width": 2, "stroke-dasharray": "4 5" });
  add("path", { d: "M" + pts.map(p => p[0] + " " + p[1]).join(" L "), fill: "none",
    stroke: "var(--accent)", "stroke-width": 2.5, "stroke-linejoin": "round" });
  pts.forEach((p, i) => {
    add("circle", { cx: p[0], cy: p[1], r: 4, fill: "var(--accent)" });
    add("text", { x: p[0], y: H - 8, "text-anchor": "middle", fill: "var(--ink-3)",
      "font-size": 10, "font-family": "var(--mono)" }, "R" + p[3]);
    add("title", {}, `R${p[3]} — ${p[2]} points`);
  });
  return el("div", { class: "pathchart" }, svg,
    el("p", { class: "tiny dim", style: "margin:8px 0 0",
      text: "Solid line: their running points. Dashed: the field's average pace." }));
}

/* ------------------------------------------------------------------ judge --- */

function openJudge(jid) {
  const j = judge(jid), h = jhist(jid);
  openSheet(sheet => {
    const pills = [
      el("span", { class: "pill mute", text: plural(h.length, "room") }),
      h.some(x => x.pos === "C") ? el("span", { class: "pill ok",
        text: plural(h.filter(x => x.pos === "C").length, "chair") }) : null,
    ];
    if (j.breaking) pills.push(el("span", { class: "pill warm", text: "Breaking judge" }));
    sheet.append(sheetHead(j.name, [j.inst, j.region].filter(Boolean).join(" · "), pills.filter(Boolean)));

    const body = el("div", { class: "sb" });
    body.append(el("div", {}, el("h4", { text: "Where they sat" }),
      el("div", { class: "grid2" },
        stat(h.length, "rooms"),
        stat(h.filter(x => x.pos === "C").length, "as chair"),
        stat(h.filter(x => x.pos === "P").length, "as panellist"),
        stat(h.filter(x => x.pos === "T").length, "as trainee"))));

    if (!h.length) {
      body.append(el("p", { class: "note", text: "No published allocation lists this judge yet." }));
      sheet.append(body); return;
    }

    const table = el("table");
    table.append(el("thead", {}, el("tr", {},
      el("th", { text: "Rd" }), el("th", { text: "Room" }), el("th", { text: "As" }),
      el("th", { text: "The room" }), el("th", { text: "Alongside" }))));
    const tb = el("tbody");
    for (const x of h) {
      const d = x.debate;
      tb.append(el("tr", {},
        el("td", {}, el("b", { text: x.abbr })),
        el("td", { class: "mono tiny", text: d.room || "—" }),
        el("td", {}, el("span", { class: "pill " + (x.pos === "C" ? "ok" : "mute"), text: POS_FULL[x.pos] })),
        el("td", {}, el("span", { class: "oppgrid" }, [...d.teams]
          .sort((a, b) => (d.ranks.get(b.t) ? -1 : 0) - (d.ranks.get(a.t) ? -1 : 0))
          .map(y => teamChip(team(y.t), {
            rk: d.ranks.get(y.t) ? d.ranks.get(y.t) : null,
            right: d.through.size ? (d.through.has(y.t) ? "through" : "out") : SIDE_LABEL[y.side],
            breaks: d.through.size ? d.through.has(y.t) : d.ranks.get(y.t) === 1 })))),
        el("td", {}, el("span", { class: "oppgrid" },
          d.panel.filter(p => p.j !== jid).map(p => judgeChip(p))))));
    }
    table.append(tb);
    body.append(el("div", {}, el("h4", { text: "Room by room" }), el("div", { class: "tblwrap card" }, table)));

    const with_ = new Map();
    for (const x of h) for (const p of x.debate.panel) if (p.j !== jid) with_.set(p.j, (with_.get(p.j) || 0) + 1);
    if (with_.size) {
      body.append(el("div", {}, el("h4", { text: `Sat with ${with_.size} other judges` }),
        el("div", { class: "oppgrid" }, [...with_.entries()].sort((a, b) => b[1] - a[1])
          .map(([id, n]) => judgeChip({ j: id }, n > 1 ? n + "×" : null)))));
    }
    sheet.append(body);
  }, "#judge-" + jid);
}
