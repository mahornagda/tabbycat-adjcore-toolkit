/* ===========================================================================
   speaks.js — the speaker tab, when the tournament has released it.

   This view does not exist unless `DATA.speaker_scores` is present, and that is
   present only when Tabbycat's own `speaker_tab_released` switch is on. So the
   tab appears on the page exactly when the tournament's own public tab would
   show it, and disappears again if it is un-released.

   Three of Tabbycat's rules are obeyed rather than reimplemented, and each is
   surfaced in the interface rather than applied silently:

     · a speaker the tab marks anonymous keeps their scores and loses their
       name, so the ranks stay continuous and nothing is invented;
     · a tab limit truncates the list, and the page says how far it goes;
     · an iron-person speech is marked, and excluded from the average the way
       the tab excludes it — a count that looks short then has a visible reason.
   ========================================================================= */

function renderSpeaks() {
  const root = clear(q("#v-speaks"));
  const rows = DATA.speaker_scores || [];
  const cut = (DATA.gate || {}).speaker_tab_limit || 0;
  const teamName = id => (T.get(id) || {}).name || "—";

  root.append(el("div", { class: "head" },
    el("h2", { text: "The speaker tab" }),
    el("p", { text: "Released by the tournament. Every number here comes from the "
                  + "tab's own speaker tab — nothing is recomputed, and nothing "
                  + "is shown that the tournament has not published." })));

  if (!rows.length) {
    root.append(el("p", { class: "empty", text: "The tab is released but empty." }));
    return;
  }

  const anon = rows.filter(r => r.anon).length;
  const ghosts = rows.reduce((n, r) => n + Object.values(r.by_round || {})
    .reduce((m, sp) => m + sp.filter(s => s.ghost).length, 0), 0);

  // `kpi()` emits .kpi tiles, which the stylesheet lays out inside .kpis —
  // .cards is for the bordered panels, and using it gave four unstyled divs.
  root.append(el("div", { class: "kpis", style: "margin-bottom:16px" },
    kpi(rows.length, cut ? "speakers, to the published limit" : "speakers on the tab",
        cut ? "the tournament publishes the top " + cut : "the whole tab"),
    kpi(spkFmt(rows[0].avg), "best average", rows[0].name || "an anonymous speaker"),
    kpi(anon, "anonymous", anon ? "scores shown, names withheld by the tab" : "none"),
    kpi(ghosts, "iron-person speeches", ghosts ? "marked, and out of the averages" : "none")));

  if (anon) {
    root.append(el("p", { class: "note", style: "margin-bottom:16px", text:
      "Some speakers have asked the tournament not to publish their name. Their "
      + "scores are here and their names are not — the same as on the "
      + "tournament's own tab." }));
  }

  root.append(dataTable(rows, [
    { k: "rank", label: "#", num: true, get: r => r.rank,
      cell: r => el("span", {}, String(r.rank), r.tied ? el("span",
        { class: "pill mute", style: "margin-left:6px", text: "=" }) : null) },
    { k: "name", label: "Speaker", w: "26%",
      get: r => r.name || "anonymous",
      cell: r => r.name
        ? el("span", { class: "nm", text: r.name })
        : el("span", { class: "nm mute", text: "Anonymous", title:
            "This speaker is marked anonymous on the tab" }) },
    { k: "team", label: "Team", get: r => teamName(r.t),
      cell: r => {
        const t = T.get(r.t);
        return t ? teamChip(t) : el("span", { class: "mute", text: "—" });
      } },
    { k: "total", label: "Total", num: true, get: r => r.total },
    { k: "avg", label: "Average", num: true, get: r => r.avg },
    { k: "count", label: "Speeches", num: true, get: r => r.count },
    { k: "stdev", label: "Spread", num: true, get: r => r.stdev,
      cell: r => el("span", { class: "mute", text: spkFmt(r.stdev) }) },
    { k: "rounds", label: "Round by round", w: "28%",
      get: r => "",
      cell: r => speechStrip(r) },
  ], { title: "Speakers", unit: "speaker", sort: "total",
       placeholder: "Filter by speaker, team or school…" }));

  root.append(el("p", { class: "note", style: "margin-top:16px", text:
    "Reply speeches and the adjudicator tab have their own release switches on "
    + "Tabbycat, and neither is published here. Releasing the speaker tab does "
    + "not release them." }));
}

/** One speaker's scores across the rounds, in round order, ghosts marked. */
function speechStrip(r) {
  const wrap = el("span", { class: "chips" });
  const seqs = Object.keys(r.by_round || {}).map(Number).sort((a, b) => a - b);
  if (!seqs.length) return el("span", { class: "mute", text: "—" });
  for (const sq of seqs) {
    const round = (R.get(sq) || {}).abbr || String(sq);
    for (const sp of r.by_round[String(sq)]) {
      wrap.append(el("span", {
        class: "pill" + (sp.ghost ? " mute" : ""),
        title: sp.ghost
          ? round + " — an iron-person speech, not counted in the average"
          : round + (sp.pos ? ", speaking " + spkOrdinal(sp.pos) : ""),
        text: spkFmt(sp.score) + (sp.ghost ? "*" : ""),
      }));
    }
  }
  return wrap;
}

function spkOrdinal(n) {
  const s = ["th", "st", "nd", "rd"], v = n % 100;
  return n + (s[(v - 20) % 10] || s[v] || s[0]);
}

/** Speaks are halves as often as not, so trim a trailing .0 but keep a .5. */
function spkFmt(v) {
  if (v == null) return "—";
  const n = Number(v);
  return Number.isInteger(n) ? String(n) : String(Math.round(n * 100) / 100);
}
