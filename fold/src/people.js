/* ===========================================================================
   people.js — teams, judges and schools as sortable tables.

   Team columns are counts of finishing positions, which is all the public
   rankings support. There is no speaks column here and there cannot be one:
   the number never reaches the page.
   ========================================================================= */

/** A sortable, filterable table. cols: {k, label, num, get, cell, w} */
function dataTable(rows, cols, opts) {
  const o = opts || {};
  const st = { key: o.sort || cols[0].k, dir: o.dir || -1, find: "" };
  const wrap = el("div", { class: "card" });
  const count = el("span", { class: "pill mute" });
  const head = el("h3", {}, o.title || "", count);
  const bar = el("div", { class: "body", style: "padding:11px 14px;border-bottom:1px solid var(--rule)" },
    el("input", { type: "search", placeholder: o.placeholder || "Filter…", style: "width:min(340px,100%)",
      oninput: e => { st.find = e.target.value.toLowerCase().trim(); paint(); } }));
  const tw = el("div", { class: "tblwrap" });
  const table = el("table");
  const thead = el("thead"), tbody = el("tbody");
  table.append(thead, tbody); tw.append(table);
  wrap.append(head, bar, tw);

  const th = el("tr"), arrows = new Map();
  for (const c of cols) {
    const ar = el("span", { class: "ar" });
    arrows.set(c.k, ar);
    th.append(el("th", {
      class: (c.num ? "num " : "") + "sortable", style: c.w ? "width:" + c.w : null,
      onclick: () => { st.dir = st.key === c.k ? -st.dir : (c.num ? -1 : 1); st.key = c.k; paint(); },
    }, c.label, ar));
  }
  thead.append(th);

  function paint() {
    const col = cols.find(c => c.k === st.key) || cols[0];
    const hay = r => cols.map(c => String(c.get(r) ?? "")).join(" ").toLowerCase()
      + " " + (o.hay ? o.hay(r) : "");
    let list = st.find ? rows.filter(r => hay(r).includes(st.find)) : rows.slice();
    list.sort((a, b) => {
      const x = col.get(a), y = col.get(b);
      const n = typeof x === "number" && typeof y === "number"
        ? x - y : String(x ?? "").localeCompare(String(y ?? ""));
      return n * st.dir || String(cols[0].get(a)).localeCompare(String(cols[0].get(b)));
    });
    clear(tbody);
    for (const r of list) {
      const tr = el("tr", { class: o.onrow ? "clk" : null, onclick: o.onrow ? () => o.onrow(r) : null });
      for (const c of cols) tr.append(el("td", { class: c.num ? "num" : null }, c.cell ? c.cell(r) : String(c.get(r) ?? "—")));
      tbody.append(tr);
    }
    count.textContent = plural(list.length, o.unit || "row");
    for (const c of cols) arrows.get(c.k).textContent =
      c.k === st.key ? (st.dir > 0 ? "▲" : "▼") : "";
  }
  paint();
  return wrap;
}

/** Finishing-position tallies from the public rankings. */
function tally(tid) {
  const h = hist(tid).filter(x => x.rank);
  const c = [0, 0, 0, 0];
  for (const x of h) c[x.rank - 1]++;
  return { firsts: c[0], seconds: c[1], thirds: c[2], fourths: c[3], rounds: h.length };
}

function breakLabel(t) {
  const bits = [];
  for (const c of DATA.categories) {
    if (!t.cats.includes(c.slug)) continue;
    const br = breakRank(c.slug, t.id);
    if (br != null) bits.push({ cls: "ok", text: c.name + " #" + br });
  }
  return bits;
}

function renderTeams() {
  const root = clear(q("#v-teams"));
  root.append(el("div", { class: "head" },
    el("h2", { text: "Teams" }),
    el("p", { text: plural(DATA.teams.length, "team") + " in the field. Click any row for the full path through the tournament." })));

  const rows = DATA.teams.map(t => ({ t, ...tally(t.id), pts: (ST.get(t.id) || {}).pts || 0,
                                      speaks: (ST.get(t.id) || {}).speaks }));
  // Total speaks are on the payload only when the tournament has released its
  // team tab, so the column exists exactly when the tab's own does.
  const hasSpeaks = rows.some(r => r.speaks != null);
  root.append(dataTable(rows, [
    { k: "name", label: "Team", get: r => r.t.name, w: "23%",
      cell: r => el("span", { class: "nmwrap" },
        el("span", { class: "linkish", text: r.t.name }),
        breakLabel(r.t).map(b => el("span", { class: "pill " + b.cls, text: b.text }))) },
    { k: "inst", label: "School", get: r => r.t.inst, w: "24%" },
    { k: "region", label: "Region", get: r => r.t.region || "—" },
    { k: "pts", label: "Pts", num: true, get: r => r.pts },
    ...(hasSpeaks ? [{ k: "speaks", label: "Speaks", num: true,
                       get: r => r.speaks == null ? "" : r.speaks }] : []),
    { k: "firsts", label: "1sts", num: true, get: r => r.firsts },
    { k: "seconds", label: "2nds", num: true, get: r => r.seconds },
    { k: "thirds", label: "3rds", num: true, get: r => r.thirds },
    { k: "fourths", label: "4ths", num: true, get: r => r.fourths },
    { k: "rounds", label: "Rds", num: true, get: r => r.rounds },
  ], {
    title: "The field", unit: "team", sort: "pts", placeholder: "Filter by team, school or region…",
    hay: r => (r.t.speakers || []).join(" ").toLowerCase() + " " + r.t.cats.join(" "),
    onrow: r => openTeam(r.t.id),
  }));
}

function renderJudges() {
  const root = clear(q("#v-judges"));
  const anyPanel = DATA.rounds.some(r => r.draw_public);
  root.append(el("div", { class: "head" },
    el("h2", { text: "Judges" }),
    el("p", { text: anyPanel
      ? "Who judged where, from the published allocations. Feedback, test scores and adjudication-core notes are not public and are not in this page."
      : "No judge allocation is public yet." })));

  const rows = DATA.judges.map(j => {
    const h = jhist(j.id);
    return { j, rounds: h.length,
      C: h.filter(x => x.pos === "C").length,
      P: h.filter(x => x.pos === "P").length,
      T: h.filter(x => x.pos === "T").length };
  });
  root.append(dataTable(rows, [
    { k: "name", label: "Judge", get: r => r.j.name, w: "26%",
      cell: r => el("span", { class: "nmwrap" },
        el("span", { class: "linkish", text: r.j.name }),
        r.j.breaking ? el("span", { class: "pill ok", text: "breaking" }) : null) },
    { k: "inst", label: "School", get: r => r.j.inst, w: "28%" },
    { k: "region", label: "Region", get: r => r.j.region || "—" },
    { k: "rounds", label: "Rooms", num: true, get: r => r.rounds },
    { k: "C", label: "Chaired", num: true, get: r => r.C },
    { k: "P", label: "Panelled", num: true, get: r => r.P },
    { k: "T", label: "Trainee", num: true, get: r => r.T },
  ], { title: "The panel", unit: "judge", sort: "rounds",
       placeholder: "Filter by judge, school or region…", onrow: r => openJudge(r.j.id) }));
}

function renderSchools() {
  const root = clear(q("#v-schools"));
  const by = new Map();
  const add = (key, kind, item) => {
    if (!by.has(key)) by.set(key, { inst: key, region: item.region, teams: [], judges: [] });
    by.get(key)[kind].push(item);
  };
  for (const t of DATA.teams) add(t.inst, "teams", t);
  for (const j of DATA.judges) add(j.inst, "judges", j);

  const rows = [...by.values()].map(s => ({
    ...s,
    pts: s.teams.reduce((n, t) => n + ((ST.get(t.id) || {}).pts || 0), 0),
    broke: s.teams.filter(t => breakLabel(t).length).length,
  }));
  const regions = new Map();
  for (const r of rows) {
    const k = r.region || "—";
    const g = regions.get(k) || { region: k, schools: 0, teams: 0, broke: 0 };
    g.schools++; g.teams += r.teams.length; g.broke += r.broke;
    regions.set(k, g);
  }

  root.append(el("div", { class: "head" },
    el("h2", { text: "Schools and regions" }),
    el("p", { text: plural(rows.length, "institution") + " across " + plural(regions.size, "region") + "." })));

  root.append(el("div", { class: "cards" },
    dataTable(rows, [
      { k: "inst", label: "School", get: r => r.inst, w: "34%" },
      { k: "region", label: "Region", get: r => r.region || "—" },
      { k: "nt", label: "Teams", num: true, get: r => r.teams.length },
      { k: "nj", label: "Judges", num: true, get: r => r.judges.length },
      { k: "pts", label: "Pts", num: true, get: r => r.pts },
      { k: "broke", label: "Broke", num: true, get: r => r.broke },
      { k: "who", label: "Its teams", get: r => r.teams.map(t => t.name).join(" "), w: "26%",
        cell: r => el("span", { class: "chips" }, r.teams.map(t => teamChip(t, { right: String((ST.get(t.id) || {}).pts ?? "") }))) },
    ], { title: "Schools", unit: "school", sort: "pts", placeholder: "Filter schools…" }),
    dataTable([...regions.values()], [
      { k: "region", label: "Region", get: r => r.region, w: "40%" },
      { k: "schools", label: "Schools", num: true, get: r => r.schools },
      { k: "teams", label: "Teams", num: true, get: r => r.teams },
      { k: "broke", label: "Broke", num: true, get: r => r.broke },
    ], { title: "Regions", unit: "region", sort: "teams", placeholder: "Filter regions…" })));
}
