/* ===========================================================================
   rounds.js — round by round: the motion, the rooms, the panels, the rankings.

   A round only appears in full if the tab says it may. Three separate switches
   land here, and each one can be off on its own: the draw (rooms + panel), the
   result (who came 1st to 4th), and the motion.
   ========================================================================= */

const rdState = { seq: null, find: "" };

function renderRounds() {
  const root = clear(q("#v-rounds"));
  const shown = DATA.rounds.filter(r => r.draw_public || r.results_public);
  if (rdState.seq == null) rdState.seq = shown.length ? shown[shown.length - 1].seq : null;

  root.append(el("div", { class: "head" },
    el("h2", { text: "Round by round" }),
    el("p", { text: "Every room, who was in it, who judged it and where each team finished." })));

  const chips = el("div", { class: "seg", role: "group", style: "flex-wrap:wrap" });
  for (const r of DATA.rounds) {
    const open = r.draw_public || r.results_public;
    chips.append(el("button", {
      text: r.abbr, disabled: !open, title: open ? r.name : r.name + " — not public yet",
      "aria-pressed": String(r.seq === rdState.seq),
      style: open ? "" : "opacity:.4;cursor:not-allowed",
      onclick: () => { rdState.seq = r.seq; renderRounds(); },
    }));
  }
  root.append(el("div", { class: "bar" },
    el("span", { class: "lab", text: "Round" }), chips,
    el("span", { class: "spacer", style: "flex:1" }),
    el("input", { type: "search", placeholder: "Filter by team, judge or school…", value: rdState.find,
      oninput: e => { rdState.find = e.target.value; paintRooms(); } })));

  if (rdState.seq == null) {
    root.append(el("p", { class: "note warm", text: "No round is public yet." }));
    return;
  }
  const r = R.get(rdState.seq);
  const rooms = BY_ROUND.get(r.seq) || [];

  const pills = el("div", { class: "chips", style: "margin-bottom:16px" },
    el("span", { class: "pill " + (r.draw_public ? "ok" : "mute"), text: r.draw_public ? "draw public" : "draw not public" }),
    el("span", { class: "pill " + (r.results_public ? "ok" : "gold"), text: r.results_public ? "rankings public" : (r.silent ? "silent round" : "no rankings yet") }),
    r.outround ? el("span", { class: "pill plum", text: r.cat_name + " break round" }) : null,
    el("span", { class: "pill mute", id: "roomcount", text: plural(rooms.length, "room") }));
  root.append(pills);

  if (r.motion) {
    root.append(el("div", { class: "card", style: "margin-bottom:18px" },
      el("h3", {}, "The motion", r.motion.reference ? el("span", { class: "pill mute", text: r.motion.reference }) : null),
      el("div", { class: "body" },
        el("p", { style: "margin:0;font:400 19px/1.4 var(--serif)", text: r.motion.text }),
        r.motion.info_slide ? el("p", { class: "note", style: "margin-top:12px",
          text: "Info slide — " + r.motion.info_slide }) : null)));
  } else {
    root.append(el("p", { class: "note", style: "margin-bottom:18px",
      text: "The motion for this round is not published." }));
  }

  if (!rooms.length) {
    root.append(el("p", { class: "empty", text: "Nothing to show for this round yet." }));
    return;
  }
  const grid = el("div", { id: "roomgrid",
    style: "display:grid;gap:14px;grid-template-columns:repeat(auto-fill,minmax(292px,1fr))" });
  for (const d of rooms) grid.append(roomCard(d, r));
  root.append(grid);
  paintRooms();
}

function roomCard(d, r) {
  const box = el("div", { class: "room" });
  box.dataset.hay = [
    d.room,
    ...d.teams.map(x => { const t = team(x.t); return `${t.name} ${t.inst} ${t.region || ""}`; }),
    ...d.panel.map(p => { const j = judge(p.j); return `${j.name} ${j.inst}`; }),
  ].join(" ").toLowerCase();

  box.append(el("div", { class: "rh" },
    el("span", { class: "rn", text: d.room || "room" }),
    el("span", { class: "spacer", style: "flex:1" }),
    d.decided ? el("span", { class: "pill ok", text: d.through.size ? "through" : "ranked" })
      : el("span", { class: "pill mute", text: r.results_public ? "no ballot" : "not out" })));

  const slots = el("div", { class: "slots" });
  // Sort by points where there are points; a break room keeps its side order,
  // because "through" carries no ordering between the two that advanced.
  const order = (d.decided && !d.through.size)
    ? [...d.teams].sort((a, b) => b.pts - a.pts) : d.teams;
  for (const x of order) {
    const t = team(x.t), rank = d.ranks.get(x.t) || null;
    const through = d.through.size ? d.through.has(x.t) : null;
    slots.append(el("div", {
      class: "slot " + (x.side || "") + (through === true || rank === 1 ? " won" : "")
             + (through === false ? " gone" : ""),
      title: SIDE_FULL[x.side] || "", onclick: () => openTeam(x.t),
    },
      el("span", { class: "sd", text: SIDE_LABEL[x.side] || "?" }),
      el("span", { class: "nm" }, flagMark(t.region), t.name),
      through != null ? el("span", { class: "rkb", text: through ? "through" : "out" })
        : rank ? rankBadge(rank) : el("span", { class: "rkb", text: t.code })));
  }
  box.append(slots);
  box.append(el("div", { class: "panelrow" },
    d.panel.length ? d.panel.map(p => judgeChip(p)) : el("span", { class: "tiny dim", text: "panel not published" })));
  return box;
}

function paintRooms() {
  const s = rdState.find.trim().toLowerCase();
  const g = q("#roomgrid");
  if (!g) return;
  let n = 0;
  g.querySelectorAll(".room").forEach(b => {
    const hit = !s || b.dataset.hay.includes(s);
    b.style.display = hit ? "" : "none";
    if (hit) n++;
  });
  const c = q("#roomcount");
  if (c) c.textContent = s ? plural(n, "room") + " matching" : plural(g.children.length, "room");
}
