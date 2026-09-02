import { login, makeClient } from "./_tabread.mjs";

const POSITION = { chair: "Chair", panellist: "Panellist", trainee: "Trainee" };
const rid = u => u ? parseInt(String(u).replace(/\/$/, "").split("/").pop(), 10) : null;

export async function buildData(state, log = () => {}) {
  const cookie = await login();
  const { api, vuedata } = makeClient(cookie);
  log("reading tournament");

  const [tour, prefsArr, roundsRaw, breakcats, spkcats, instArr, adjs, teams] = await Promise.all([
    api(""), api("preferences", { paginate: true }), api("rounds", { paginate: true }),
    api("break-categories", { paginate: true }), api("speaker-categories", { paginate: true }),
    api("institutions", { tournament: false, paginate: true }),
    api("adjudicators", { paginate: true }), api("teams", { paginate: true }),
  ]);
  const prefs = Object.fromEntries(prefsArr.map(p => [p.identifier, p.value]));
  const rounds = [...roundsRaw].sort((a, b) => a.seq - b.seq);
  const insts = Object.fromEntries(instArr.map(i => [i.url, i]));
  const teamsPer = parseInt(prefs["debate_rules__teams_in_debate"] ?? 4, 10);
  const bcByUrl = Object.fromEntries(breakcats.map(b => [b.url, b]));
  log(`${rounds.length} rounds · ${adjs.length} judges · ${teams.length} teams`);

  const R = rounds.map(r => ({
    seq: r.seq, name: r.name, abbr: r.abbreviation,
    outround: r.stage === "E",
    break_category: (bcByUrl[r.break_category] || {}).name || null,
    break_slug: (bcByUrl[r.break_category] || {}).slug || null,
    completed: r.completed, silent: r.silent,
    draw_released: r.draw_status === "R",
    draw_made: ["D", "C", "R"].includes(r.draw_status),
    draw_status: { N: "Not started", D: "Draft", C: "Confirmed", R: "Released" }[r.draw_status] || r.draw_status,
    motions_released: r.motions_released,
    feedback_weight: r.feedback_weight,
  }));

  // outround plan — derived, never hardcoded
  const plan = [...breakcats].sort((a, b) => a.seq - b.seq).map(bc => {
    const elims = R.filter(r => r.outround && r.break_slug === bc.slug);
    let rooms = bc.break_size / teamsPer;
    const steps = elims.map(r => {
      const s = { ...r, rooms: Math.max(1, Math.round(rooms)),
                  teams_in: Math.max(teamsPer, Math.round(rooms * teamsPer)) };
      rooms /= 2; return s;
    });
    let n = bc.break_size / teamsPer, expected = 0;
    while (n >= 1) { expected++; n /= 2; }
    return { name: bc.name, slug: bc.slug, break_size: bc.break_size, is_general: bc.is_general,
             rounds: steps, rounds_expected: expected, rounds_configured: elims.length,
             matches: expected === elims.length };
  });

  const elig = [];
  await Promise.all([
    ...breakcats.map(async bc => {
      try { const e = await api(`break-categories/${bc.id}/eligibility`);
        elig.push({ name: bc.name, slug: bc.slug, teams: (e.team_set || []).length, break_size: bc.break_size });
      } catch {}
    }),
    ...spkcats.map(async sc => {
      try { const e = await api(`speaker-categories/${sc.id}/eligibility`);
        elig.push({ name: sc.name + " (speakers)", slug: sc.slug, teams: (e.speaker_set || []).length, break_size: null });
      } catch {}
    }),
  ]);

  const A = {};
  for (const a of adjs) {
    const inst = insts[a.institution] || {};
    A[a.id] = {
      id: a.id, name: a.name, institution: inst.name || "—", inst_code: inst.code || "—",
      region: inst.region ?? null, base_score: a.base_score,
      adjcore: a.adj_core, independent: a.independent, trainee: a.trainee, breaking: a.breaking,
      conflicts_team: a.team_conflicts.length, conflicts_adj: a.adjudicator_conflicts.length,
      conflicts_inst: a.institution_conflicts.length, has_email: !!a.email,
      rounds: [], feedback: [], tested: [], tested_others: [],
    };
  }
  const teamName = Object.fromEntries(teams.map(t => [t.url, t.short_name]));

  log("reading draws");
  const drawn = R.filter(r => r.draw_made);
  const draws = await Promise.all(drawn.map(r =>
    api(`rounds/${r.seq}/pairings`, { paginate: true }).catch(() => [])));
  let debateCount = 0;
  drawn.forEach((r, i) => {
    for (const d of draws[i]) {
      debateCount++;
      const ad = d.adjudicators || {};
      const panel = [
        ...(ad.chair ? [[rid(ad.chair), "chair"]] : []),
        ...((ad.panellists || []).map(u => [rid(u), "panellist"])),
        ...((ad.trainees || []).map(u => [rid(u), "trainee"])),
      ];
      const sides = (d.teams || []).map(dt => ({ side: dt.side, team: teamName[dt.team] || "?" }));
      for (const [aid, pos] of panel) {
        if (!A[aid]) continue;
        A[aid].rounds.push({
          seq: r.seq, round: r.abbr, position: POSITION[pos], debate: d.id,
          bracket: d.bracket ?? null, importance: d.importance ?? null,
          teams: sides, panel_size: panel.length,
          with: panel.map(([x]) => x).filter(x => x !== aid),
        });
      }
    }
  });

  log("reading feedback");
  let fb = [], fq = [];
  try { [fb, fq] = await Promise.all([
    api("feedback", { paginate: true }),
    api("feedback-questions", { paginate: true }),
  ]); } catch {}
  const qmap = Object.fromEntries((fq || []).map(q => [q.url, q]));
  const teamByUrl = Object.fromEntries(teams.map(t => [t.url, t]));
  const TEXTY = new Set(["tl", "ts", "t"]);
  const roundOf = u => {
    const m = String(u || "").match(/\/rounds\/(\d+)\/pairings\//);
    return m ? parseInt(m[1], 10) : null;
  };
  for (const f of fb) {
    const aid = rid(f.adjudicator);
    if (!A[aid]) continue;
    const src = f.source || "";
    let from_type = "other", from_name = "—";
    if (src.includes("/teams/")) {
      from_type = "team"; from_name = (teamByUrl[src] || {}).short_name || "a team";
    } else if (src.includes("/adjudicators/")) {
      from_type = "judge";
      const sid = rid(src);
      from_name = A[sid] ? A[sid].name : "a judge";
    }
    const answers = [], comments = [];
    for (const ans of f.answers || []) {
      const q = qmap[ans.question] || {};
      const row = { q: q.text || q.name || "Question", a: ans.answer, type: q.answer_type };
      answers.push(row);
      const val = String(row.a ?? "").trim();
      if (TEXTY.has(row.type) && val.length > 1) comments.push({ q: row.q, a: val });
    }
    const seq = roundOf(f.debate);
    A[aid].feedback.push({
      score: f.score ?? null, confirmed: f.confirmed, ignored: f.ignored,
      debate: rid(f.debate), seq,
      round: (R.find(r => r.seq === seq) || {}).abbr || "—",
      timestamp: f.timestamp, from_type, from_name, answers, comments,
    });
  }

  // testers
  const defaults = new Set(adjs.filter(a => a.adj_core).map(a => a.id));
  const extra = new Set(state.extra_testers || []);
  const testers = new Set([...defaults, ...extra]);
  for (const id of Object.keys(A)) {
    const n = Number(id);
    A[n].is_tester = testers.has(n);
    A[n].tester_source = defaults.has(n) ? "Adj core" : extra.has(n) ? "Added by adjcore" : null;
  }

  // test events, derived from who sat with whom
  for (const a of Object.values(A)) {
    if (a.is_tester) continue;
    for (const sit of a.rounds) {
      const present = sit.with.filter(x => testers.has(x) && x !== a.id);
      if (!present.length) continue;
      a.tested.push({
        seq: sit.seq, round: sit.round, as: sit.position,
        by: present.map(x => ({ id: x, name: A[x].name,
          their_position: (A[x].rounds.find(s => s.debate === sit.debate) || {}).position || "?" })),
      });
      for (const x of present)
        A[x].tested_others.push({ seq: sit.seq, round: sit.round, id: a.id, name: a.name, as: sit.position });
    }
  }
  for (const m of state.manual_tests || []) {
    const a = A[m.judge_id];
    if (a) a.tested.push({ seq: m.seq, round: m.round || "—", as: m.as || "Panellist",
      by: [{ id: null, name: m.by || "adjcore", their_position: "logged by hand" }], manual: true });
  }

  // name every panel, tested or not — adjcore need to see who chaired them and
  // who sat with them in EVERY round, not only where a tester was present.
  const posIn = new Map();
  for (const a of Object.values(A))
    for (const sit of a.rounds) posIn.set(`${sit.debate}:${a.id}`, sit.position);
  const order = { Chair: 0, Panellist: 1, Trainee: 2 };
  for (const a of Object.values(A)) {
    for (const sit of a.rounds) {
      const people = sit.with.filter(x => A[x]).map(x => ({
        id: x, name: A[x].name,
        position: posIn.get(`${sit.debate}:${x}`) || "?",
        is_tester: A[x].is_tester,
      }));
      people.sort((p, q) => (order[p.position] ?? 9) - (order[q.position] ?? 9)
                            || p.name.localeCompare(q.name));
      sit.panel = people;
      sit.chair = people.find(p => p.position === "Chair") || null;
    }
  }

  for (const a of Object.values(A)) {
    const seen = new Set(a.tested.map(x => x.as));
    a.tested_as_chair = seen.has("Chair");
    a.tested_as_panellist = seen.has("Panellist");
    a.tested_as_trainee = seen.has("Trainee");
    a.best_seen = a.tested_as_chair ? "Chair" : a.tested_as_panellist ? "Panellist"
                : a.tested_as_trainee ? "Trainee" : null;
    a.test_count = a.tested.length;
    const live = a.feedback.filter(f => f.score != null && !f.ignored);
    const sc = live.map(f => f.score);
    const avg = arr => arr.length ? Math.round((arr.reduce((x, y) => x + y, 0) / arr.length) * 100) / 100 : null;
    a.feedback_n = sc.length;
    a.feedback_avg = avg(sc);
    for (const grp of ["team", "judge"]) {
      const g = live.filter(f => f.from_type === grp).map(f => f.score);
      a[`feedback_${grp}_n`] = g.length;
      a[`feedback_${grp}_avg`] = avg(g);
    }
    a.comment_count = a.feedback.reduce((n, f) => n + (f.comments || []).length, 0);
    a.feedback.sort((x, y) => (x.seq || 0) - (y.seq || 0) || String(x.from_type).localeCompare(String(y.from_type)));
    a.rounds_judged = a.rounds.length;
    a.chaired = a.rounds.filter(s => s.position === "Chair").length;
    a.panelled = a.rounds.filter(s => s.position === "Panellist").length;
  }

  log("reading feedback progress and check-ins");
  const cellText = c => {
    if (c && typeof c === "object") {
      for (const k of ["text", "sort"]) if (c[k] != null && c[k] !== "")
        return String(c[k]).replace(/<[^>]+>/g, "").trim();
      return "";
    }
    return String(c ?? "");
  };
  let owedJ = {}, owedT = [], checked = {}, speakersIn = 0, speakersAll = 0;
  const [progVd, chkVd] = await Promise.all([
    vuedata("admin/feedback/progress/").catch(() => ({})),
    vuedata("admin/checkins/status/people/").catch(() => ({})),
  ]);
  for (const tb of progVd.tablesData || []) {
    const head = (tb.head || []).map(h => h.title || h.key || "");
    if (!head.includes("owed")) continue;
    const io = head.indexOf("owed"), ip = head.indexOf("percent");
    const rows = (tb.data || []).map(r => r.map(cellText));
    if (head.includes("name")) { const i = head.indexOf("name");
      for (const r of rows) owedJ[r[i]] = { owed: r[io], percent: r[ip] }; }
    else if (head.includes("team")) { const i = head.indexOf("team");
      for (const r of rows) owedT.push({ team: r[i], owed: r[io], percent: r[ip] }); }
  }
  for (const a of Object.values(A)) {
    const o = owedJ[a.name];
    a.owes_feedback = o ? o.owed : null;
    a.feedback_done_pct = o ? o.percent : null;
  }
  {
    const done = new Set((chkVd.events || []).map(e => e.identifier));
    for (const p of chkVd.adjudicators || []) checked[p.id] = p.identifier.some(x => done.has(x));
    const sp = chkVd.speakers || [];
    speakersAll = sp.length;
    speakersIn = sp.filter(p => p.identifier.some(x => done.has(x))).length;
  }
  for (const a of Object.values(A)) a.checked_in = checked[a.id] ?? null;

  log(`done — ${Object.keys(A).length} judges, ${debateCount} debates, ${fb.length} feedback`);
  return {
    pulled_at: new Date().toISOString(),
    tournament: {
      name: tour.name, short: tour.short_name, slug: tour.slug,
      teams_per_debate: teamsPer,
      speakers_per_team: parseInt(prefs["debate_rules__substantive_speakers"] ?? 2, 10),
      feedback_min: prefs["feedback__adj_min_score"], feedback_max: prefs["feedback__adj_max_score"],
      min_voting_score: prefs["draw_rules__adj_min_voting_score"],
      feedback_paths: prefs["feedback__feedback_paths"], sides: prefs["debate_rules__side_names"],
    },
    rounds: R,
    break_categories: breakcats.map(b => ({ name: b.name, slug: b.slug, break_size: b.break_size, is_general: b.is_general })),
    speaker_categories: spkcats.map(s => ({ name: s.name, slug: s.slug })),
    outround_plan: plan, eligibility: elig,
    judges: Object.values(A).sort((a, b) => a.name.toLowerCase().localeCompare(b.name.toLowerCase())),
    counts: { judges: Object.keys(A).length, teams: teams.length, testers: testers.size,
              adjcore: defaults.size, speakers_in: speakersIn, speakers_all: speakersAll },
    teams_owing_feedback: owedT,
    state,
  };
}
