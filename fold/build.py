"""
build.py — pull the tab, keep only what the public may see, ship one HTML file.

Runs on Mahor's machine only: it needs the Tabbycat login, and it is the only
piece of this project that talks to the tab. Everything it produces is a single
static page with the data baked in, so the site itself holds no credentials, makes
no requests and cannot be coaxed into revealing anything the build did not write.

Read-only in the strict sense of the rest of the project: it imports the
GET-only client in ../dashboard/tabread.py and never constructs any other session.

    python3 build.py              # pull, gate, build dist/index.html
    python3 build.py --offline    # rebuild the page from the last pull (no tab call)

What may appear on the page is decided entirely by gate.py. Read that first.
"""
import argparse
import datetime
import json
import time
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
# The one read-only Tabbycat client lives in core/, shared by all three tools.
sys.path.insert(0, os.path.join(HERE, os.pardir, "core"))

import gate  # noqa: E402
from tabread import TabRead  # noqa: E402

SRC = os.path.join(HERE, "src")
DIST = os.path.join(HERE, "dist")
RAW = os.path.join(HERE, "raw.json")          # last pull, gated already
OUT = os.path.join(DIST, "index.html")

# The scripts are concatenated in this order; each one only uses what came before.
SCRIPTS = ["flags.js", "core.js", "fold.js", "bracket.js", "rounds.js",
           "people.js", "sheets.js", "speaks.js", "sim.js", "app.js"]

# Tabbycat's internal side codes. Which set is in play depends on how many teams
# are in a debate, and that is a live preference — so this is a lookup, not a
# constant. A two-team tournament whose rooms were sorted by the BP codes would
# have every room fall back to "unknown" and sort alphabetically.
SIDE_CODES = {4: ["og", "oo", "cg", "co"], 2: ["aff", "neg"], 3: ["og", "oo", "cg"]}


def side_order(teams_per_debate):
    return SIDE_CODES.get(int(teams_per_debate or 4),
                          [f"s{i}" for i in range(int(teams_per_debate or 4))])
POS = {"chair": "C", "panellist": "P", "trainee": "T"}


def _try(t, path):
    """A read that is allowed to come back empty rather than kill the build.

    These endpoints exist on every Tabbycat but a given tournament may have
    nothing in them, and an older version may not have the route at all. An
    empty speaker tab is a real state; it must not be confused with a failure,
    which is why the break endpoint next door does exactly the opposite.
    """
    try:
        return t.api(path, paginate=True)
    except Exception as e:
        print(f"  ({path} unavailable: {str(e)[:70]})")
        return []


def _metric(row, name):
    for m in row.get("metrics") or []:
        if m.get("metric") == name:
            return m.get("value")
    return None


def build_speaker_tab(prefs, got, rounds):
    """The released speaker tab, or None if it is not released.

    Returning None rather than an empty list matters: the allowlist then has no
    `speaker_scores` key to check, so "not released" and "released but empty"
    cannot be confused on the page.

    Three rules are Tabbycat's, not ours, and all three are obeyed rather than
    reimplemented:
      · `anonymous` on a speaker — the scores stay, the name goes;
      · `speaker_tab_limit` — how far down the tournament publishes;
      · `ghost` on a speech — an iron-person speech, which Tabbycat leaves out
        of the average. It is marked rather than dropped, so a short count has a
        visible reason.
    """
    if not gate.speaker_tab_public(prefs):
        return None
    stand = got.get("spk_stand") or []
    if not stand:
        return []

    # A speaker record carries an email, a phone number, a barcode and a
    # url_key — which IS that person's private ballot URL. Take the name, the
    # team and the anonymous flag; leave the rest in the response object.
    who = {}
    for sp in got.get("speakers") or []:
        who[sp["url"]] = {
            "name": sp.get("name") or "",
            "anon": bool(sp.get("anonymous")),
            "team": rid(sp.get("team")),
        }

    seq_by_round = {r["url"] if isinstance(r, str) else r: None for r in ()}
    per_round = {}
    for row in got.get("spk_rounds") or []:
        rows = {}
        for entry in row.get("rounds") or []:
            sq = seq_of(entry.get("round"))
            if sq is None:
                continue
            speeches = []
            for sp in entry.get("speeches") or []:
                if sp.get("score") is None:
                    continue
                speeches.append({"score": round(float(sp["score"]), 2),
                                 "pos": sp.get("position"),
                                 "ghost": bool(sp.get("ghost"))})
            if speeches:
                rows[str(sq)] = speeches
        per_round[row.get("speaker")] = rows

    cut = gate.tab_cut(prefs, "speaker")
    out = []
    for row in sorted(stand, key=lambda r: (r.get("rank") or 10**6)):
        if cut and (row.get("rank") or 10**6) > cut:
            continue
        url = row.get("speaker")
        w = who.get(url, {"name": "", "anon": False, "team": None})
        stdev = _metric(row, "stdev")
        out.append({
            "rank": row.get("rank"),
            "tied": bool(row.get("tied")),
            # Anonymous means the tournament's own page shows no name here.
            "name": None if w["anon"] else (w["name"] or None),
            "anon": w["anon"],
            "t": w["team"],
            "total": _round(_metric(row, "total")),
            "avg": _round(_metric(row, "average")),
            "count": _int(_metric(row, "count")),
            "stdev": None if stdev is None else round(float(stdev), 2),
            "by_round": per_round.get(url, {}),
        })
    return out


def apply_team_speaks(prefs, got, standings):
    """Add each team's total speaks, but only if the team tab is released."""
    if not gate.team_speaks_public(prefs):
        return
    cut = gate.tab_cut(prefs, "team")
    by_team = {}
    for row in got.get("team_stand") or []:
        if cut and (row.get("rank") or 10**6) > cut:
            continue
        by_team[rid(row.get("team"))] = _round(_metric(row, "speaks_sum"))
    for row in standings:
        v = by_team.get(row["t"])
        if v is not None:
            row["speaks"] = v


def _round(v):
    """Speaks to two places. Tabbycat carries full float precision, and a
    standard deviation of 1.118033988749895 on a public page is noise."""
    return None if v is None else round(float(v), 2)


def _int(v):
    return None if v is None else int(v)


def rid(url):
    m = re.search(r"/(\d+)/?$", str(url or ""))
    return int(m.group(1)) if m else None


def seq_of(url):
    m = re.search(r"/rounds/(\d+)", str(url or ""))
    return int(m.group(1)) if m else None


# --------------------------------------------------------------------- pull ----
def pull(log=print):
    t = TabRead()
    log("reading the tab (read-only)…")
    with ThreadPoolExecutor(max_workers=8) as ex:
        f = {
            "tour": ex.submit(t.api, ""),
            "prefs": ex.submit(t.api, "preferences", True),
            "rounds": ex.submit(t.api, "rounds", True),
            "bcs": ex.submit(t.api, "break-categories", True),
            "insts": ex.submit(lambda: t.api("institutions", tournament=False, paginate=True)),
            "adjs": ex.submit(t.api, "adjudicators", True),
            "teams": ex.submit(t.api, "teams", True),
            "venues": ex.submit(t.api, "venues", True),
            "motions": ex.submit(t.api, "motions", True),
            "srounds": ex.submit(lambda: t.api("teams/standings/rounds", paginate=True)),
            # The speaker tab and the team tab. Fetched unconditionally because
            # the account is allowed to read them; whether a single number
            # reaches the page is decided below, by the release switches.
            "spk_stand": ex.submit(lambda: _try(t, "speakers/standings")),
            "spk_rounds": ex.submit(lambda: _try(t, "speakers/standings/rounds")),
            "team_stand": ex.submit(lambda: _try(t, "teams/standings")),
            "speakers": ex.submit(lambda: _try(t, "speakers")),
        }
    got = {k: v.result() for k, v in f.items()}

    prefs_raw = {p["identifier"]: p["value"] for p in got["prefs"]}
    prefs = gate.read_prefs(prefs_raw)
    rounds_raw = sorted(got["rounds"], key=lambda r: r["seq"])
    teams_per_debate = int(prefs_raw.get("debate_rules__teams_in_debate", 4))
    SIDE_ORDER = side_order(teams_per_debate)

    # Which round is "being run now" — the tab's own answer, with a fallback.
    # Tab can be running several rounds at once — on 27 Aug it was on OQF and the
    # EFL semis together, because the categories break separately. Keep the whole
    # set: collapsing it to one number hides the other round's released draw.
    cur = {seq_of(u) for u in (got["tour"].get("current_rounds") or [])}
    current_seqs = {s for s in cur if s}
    if not current_seqs:
        current_seqs = {max([r["seq"] for r in rounds_raw
                             if r["draw_status"] in ("D", "C", "R")] or [0])}
    current_seq = max(current_seqs)          # for the one field that wants a scalar

    bc_by_url = {b["url"]: b for b in got["bcs"]}
    motion_by_round = {}
    for m in got["motions"]:
        for link in m.get("rounds") or []:
            motion_by_round[seq_of(link.get("round"))] = m

    # ---- rounds, each one gated on its own ----
    rounds, drawable = [], []
    for r in rounds_raw:
        bc = bc_by_url.get(r.get("break_category")) or {}
        row = {
            "seq": r["seq"], "abbr": r["abbreviation"], "name": r["name"],
            "outround": r["stage"] == "E",
            "cat": bc.get("slug"), "cat_name": bc.get("name"),
            "completed": bool(r["completed"]), "silent": bool(r["silent"]),
            "draw_status": {"N": "Not started", "D": "Draft", "C": "Confirmed",
                            "T": "Teams released", "R": "Released"}.get(
                                r["draw_status"], r["draw_status"]),
        }
        row["results_public"] = gate.results_public(row, prefs)
        row["draw_public"] = gate.draw_public(row, prefs, current_seqs)
        m = motion_by_round.get(r["seq"])
        row["motion"] = None
        if m and gate.motion_public(row, prefs, r["motions_released"]):
            row["motion"] = {
                "text": m.get("text") or "",
                "reference": m.get("reference") or "",
                "info_slide": (m.get("info_slide_plain") or m.get("info_slide") or "").strip(),
            }
        rounds.append(row)
        if row["draw_public"] or row["results_public"]:
            drawable.append(row)

    # ---- the shape of the elimination rounds (derived, never hardcoded) ----
    cats = []
    for bc in sorted(got["bcs"], key=lambda b: b["seq"]):
        elims = [r for r in rounds if r["outround"] and r["cat"] == bc["slug"]]
        rooms = bc["break_size"] / teams_per_debate
        for r in elims:
            r["rooms"] = max(1, int(round(rooms)))
            r["teams_in"] = max(teams_per_debate, int(round(rooms * teams_per_debate)))
            rooms /= 2
        cats.append({
            "slug": bc["slug"], "name": bc["name"], "break_size": bc["break_size"],
            "is_general": bool(bc["is_general"]), "break_public": gate.break_public(prefs),
            "rounds": [r["abbr"] for r in elims],
        })

    # ---- people ----
    inst = {i["url"]: i for i in got["insts"]}
    teams = []
    for tm in got["teams"]:
        i = inst.get(tm["institution"]) or {}
        teams.append({
            "id": tm["id"], "name": tm["short_name"], "long": tm.get("long_name") or tm["short_name"],
            "code": i.get("code") or "—", "inst": i.get("name") or "—",
            "region": i.get("region"), "emoji": tm.get("emoji"),
            "cats": [(bc_by_url.get(u) or {}).get("slug") for u in (tm.get("break_categories") or [])],
            # Participant lists are public; nothing else about a speaker is.
            "speakers": ([s.get("name") for s in (tm.get("speakers") or []) if s.get("name")]
                         if prefs["public_participants"] else []),
        })
    teams.sort(key=lambda x: x["name"].lower())

    judges = sorted(({
        "id": a["id"], "name": a["name"],
        "inst": (inst.get(a["institution"]) or {}).get("name") or "—",
        "code": (inst.get(a["institution"]) or {}).get("code") or "—",
        "region": (inst.get(a["institution"]) or {}).get("region"),
        "breaking": bool(a.get("breaking")) if prefs["public_breaking_adjs"] else None,
    } for a in got["adjs"]), key=lambda j: j["name"].lower())

    # ---- draws: rooms and panels, only for rounds the gate opened ----
    venue = {v["url"]: (v.get("display_name") or v.get("name") or "") for v in got["venues"]}

    def _pair(r):
        try:
            return r["seq"], t.api(f"rounds/{r['seq']}/pairings", paginate=True)
        except Exception:
            return r["seq"], []
    with ThreadPoolExecutor(max_workers=6) as ex:
        draws = dict(ex.map(_pair, drawable))

    # ---- per-round points, from the standings the public page already shows ----
    pub_result_seqs = {r["seq"] for r in rounds if r["results_public"]}
    pts_by_team, sides_by_team = {}, {}
    if prefs["public_team_standings"] or prefs["public_results"]:
        for row in got["srounds"]:
            tid = rid(row["team"])
            for s in row.get("rounds") or []:
                sq = seq_of(s.get("round"))
                if sq in pub_result_seqs and s.get("points") is not None:
                    pts_by_team.setdefault(tid, {})[str(sq)] = int(s["points"])
                if sq and s.get("side"):
                    sides_by_team.setdefault(tid, {})[str(sq)] = s["side"]

    # ---- who advanced out of a break round ----
    #
    # An elimination result is not points. `/teams/standings/rounds` covers the
    # prelims only, and an elim ballot carries `win: true/false` with `points` and
    # `score` both null — two teams through, two out. Reading only points meant the
    # octofinal results were confirmed on tab and invisible here, which is not the
    # same thing as "no ballots are in", and I reported it as the latter.
    #
    # Only `win` is taken. `score` is a speaker total and must never leave this
    # function; the gate's no-float rule is the backstop if it ever tries.
    wins = {}                                   # (round seq, team id) -> bool
    for r in rounds:
        if not (r["outround"] and r["results_public"]):
            continue
        for d in draws.get(r["seq"], []):
            try:
                bs = t.api(f"rounds/{r['seq']}/pairings/{d['id']}/ballots", paginate=True)
            except Exception as e:
                raise RuntimeError(
                    f"could not read the {r['abbr']} ballot for pairing {d['id']}: {e!r}") from e
            sheets = [sh for b in bs for sh in ((b.get("result") or {}).get("sheets") or [])]
            for sh in sheets:
                for tm in sh.get("teams") or []:
                    if tm.get("win") is not None:
                        wins[(r["seq"], rid(tm.get("team")))] = bool(tm["win"])

    debates = []
    for r in drawable:
        show_panel = r["draw_public"]
        show_pts = r["results_public"]
        for d in draws.get(r["seq"], []):
            ts = []
            for dt in sorted((d.get("teams") or []),
                             key=lambda x: SIDE_ORDER.index(x["side"])
                             if x.get("side") in SIDE_ORDER else 9):
                tid = rid(dt.get("team"))
                ts.append({
                    "t": tid, "side": dt.get("side"),
                    "pts": (pts_by_team.get(tid, {}).get(str(r["seq"])) if show_pts else None),
                    "win": (wins.get((r["seq"], tid)) if show_pts else None),
                })
            panel = []
            if show_panel:
                adjd = d.get("adjudicators") or {}
                if adjd.get("chair"):
                    panel.append({"j": rid(adjd["chair"]), "pos": POS["chair"]})
                panel += [{"j": rid(u), "pos": POS["panellist"]} for u in (adjd.get("panellists") or [])]
                panel += [{"j": rid(u), "pos": POS["trainee"]} for u in (adjd.get("trainees") or [])]
            debates.append({
                "round": r["seq"],
                "room": (venue.get(d.get("venue")) or "") if show_panel else "",
                "teams": ts, "panel": panel,
            })

    # ---- the break, exactly as announced ----
    #
    # This used to `except Exception: return []`, and on 27 Aug a transient error
    # on one call published "the break has not been announced" over a break that
    # had been out for a day — no error, no log line, just a tournament site that
    # quietly forgot who broke. An empty break is a real state (before the break is
    # announced) which is exactly why it must never be *inferred* from a failure.
    # Retry, then raise and let refresh keep the last good build.
    breaks = {}
    if gate.break_public(prefs):
        def _brk(bc):
            last = None
            for attempt in range(3):
                try:
                    return bc["slug"], t.api(f"break-categories/{bc['id']}/break", paginate=True)
                except Exception as e:
                    last = e
                    time.sleep(1 + attempt)
            raise RuntimeError(
                f"could not read the {bc['slug']} break after 3 tries: {last!r}") from last
        with ThreadPoolExecutor(max_workers=4) as ex:
            for slug, rows in ex.map(_brk, got["bcs"]):
                breaks[slug] = [{"t": rid(e["team"]), "rank": e.get("rank"),
                                 "break_rank": e.get("break_rank"), "remark": e.get("remark")}
                                for e in rows]
        check_break_not_lost(breaks, got["tour"].get("slug"))

    standings = []
    for tm in teams:
        by = pts_by_team.get(tm["id"], {})
        standings.append({
            "t": tm["id"], "pts": sum(by.values()) if by else 0,
            "by_round": by, "sides": sides_by_team.get(tm["id"], {}),
        })

    # ---- the speaker tab and team speaks, each on its own switch ----
    speaker_scores = build_speaker_tab(prefs, got, rounds)
    apply_team_speaks(prefs, got, standings)

    g = {**prefs, "current_round": current_seq,
         "speaker_tab_public": gate.speaker_tab_public(prefs),
         "team_speaks_public": gate.team_speaks_public(prefs)}
    g.update(gate.summary(prefs, rounds, current_seqs, cats, teams_per_debate))

    payload = {
        "built_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "pulled_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "tournament": {
            "name": got["tour"].get("name") or "Tournament",
            "short": got["tour"].get("short_name") or "",
            "slug": got["tour"].get("slug") or "",
            "site": f"{t.base}/{t.slug}/",
            "teams_per_debate": teams_per_debate,
            "sides": SIDE_ORDER,
            "staff": _plain(prefs_raw.get("public_features__tournament_staff") or ""),
        },
        "gate": g, "rounds": rounds, "categories": cats, "teams": teams,
        "judges": judges, "debates": debates, "breaks": breaks, "standings": standings,
    }
    if speaker_scores is not None:
        payload["speaker_scores"] = speaker_scores
    gate.assert_clean(payload)
    return payload


def _plain(html):
    """Tab writes the staff list as rich text; the site only wants the words."""
    s = re.sub(r"<br\s*/?>|</p>|</div>", "\n", html or "")
    s = re.sub(r"<[^>]+>", "", s)
    s = (s.replace("&nbsp;", " ").replace("&amp;", "&")
          .replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"'))
    return "\n".join(ln.strip() for ln in s.split("\n") if ln.strip())


def check_break_not_lost(breaks, tournament_slug=None):
    """Refuse to publish a break that has gone backwards since the last build.

    A 200 with an empty body looks identical to "not announced yet", so the retry
    above cannot catch every way this fails. The last good pull is the reference:
    a category that had ranked teams and now has none is a regression, never news.

    The comparison is only valid against the SAME tournament. Without that check
    the guard fires the first time you point the tool at a different tab — after
    the demo, or at next year's tournament — and refuses to publish a break that
    was never lost, only different. A guard that cries wolf gets switched off,
    which is worse than not having it.
    """
    if not os.path.exists(RAW):
        return
    try:
        with open(RAW) as fh:
            prev = json.load(fh)
    except Exception:
        return
    was_slug = ((prev.get("tournament") or {}).get("slug") or None)
    if tournament_slug and was_slug and was_slug != tournament_slug:
        return
    before = (prev.get("breaks") or {})
    for slug, was in before.items():
        had = sum(1 for e in was if e.get("break_rank") is not None)
        now = sum(1 for e in (breaks.get(slug) or []) if e.get("break_rank") is not None)
        if had and not now:
            raise RuntimeError(
                f"the {slug} break came back empty but had {had} teams in the last "
                f"build — refusing to publish a page that forgets who broke")


# -------------------------------------------------------------------- build ----
def render(payload):
    shell = open(os.path.join(SRC, "index.html")).read()
    css = open(os.path.join(SRC, "style.css")).read()
    js = "\n\n".join(open(os.path.join(SRC, f)).read() for f in SCRIPTS)
    blob = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    html = (shell.replace("/*__STYLE__*/", css)
                 .replace("/*__DATA__*/", "const DATA = " + blob + ";")
                 .replace("/*__APP__*/", js))
    os.makedirs(DIST, exist_ok=True)
    with open(OUT, "w") as fh:
        fh.write(html)
    write_headers()
    return html


# Cloudflare Pages and Netlify both read a `_headers` file out of the published
# directory, so the real response headers ship with the build rather than living
# in one host's config file. The page also carries the policy as a <meta> tag, so
# a host that ignores this file still gets everything but frame-ancestors.
HEADERS = """/*
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=()
  Content-Security-Policy: default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; img-src data:; connect-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'

/index.html
  Cache-Control: public, max-age=0, must-revalidate
"""


def write_headers():
    with open(os.path.join(DIST, "_headers"), "w") as fh:
        fh.write(HEADERS)


def report(payload, html):
    d, g = payload, payload["gate"]
    pub_r = [r["abbr"] for r in d["rounds"] if r["results_public"]]
    pub_d = [r["abbr"] for r in d["rounds"] if r["draw_public"]]
    locked = [r["abbr"] for r in d["rounds"] if r["outround"] and not r["draw_public"]]
    print(f"\nbuilt {os.path.relpath(OUT)}  ({len(html)/1024:.0f} KB, one file, no network calls)")
    print(f"  {len(d['teams'])} teams · {len(d['judges'])} judges · {len(d['debates'])} rooms shown")
    print(f"  results shown for : {', '.join(pub_r) or 'none'}")
    print(f"  panels shown for  : {', '.join(pub_d) or 'none'}")
    print(f"  locked out-rounds : {', '.join(locked) or 'none'}")
    for slug, rows in (d["breaks"] or {}).items():
        broke = sum(1 for r in rows if r.get("break_rank"))
        print(f"  {slug} break: {broke} teams announced")
    print(f"  gate: public_draw={g['public_draw']} results={g['public_results']} "
          f"breaks={g['public_breaking_teams']} team_tab={g['team_tab_released']}")
    print("  allowlist check: passed — no undeclared field in the payload\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true",
                    help="rebuild the page from the last pull, without touching the tab")
    a = ap.parse_args()

    if a.offline:
        if not os.path.exists(RAW):
            sys.exit("no saved pull yet — run without --offline once")
        payload = json.load(open(RAW))
        gate.assert_clean(payload)
        payload["built_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    else:
        payload = pull()
        with open(RAW, "w") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=1)

    report(payload, render(payload))


if __name__ == "__main__":
    main()
