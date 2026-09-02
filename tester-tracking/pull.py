"""
pull.py — read the tournament from Tabbycat and work out everything adjcore needs.
Read-only. Writes one file: data.json.

Nothing about the tournament shape is hardcoded. Round count, which rounds are
prelims vs outrounds, how many break categories there are and what they're
called, how many teams are in a debate — all of it comes from the live config.
"""
import json, os, re, datetime, collections, sys
from concurrent.futures import ThreadPoolExecutor

# The one read-only Tabbycat client lives in core/, so all three tools share
# exactly the same guarantee rather than each having their own copy.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, "core"))
from tabread import TabRead

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "adjcore_state.json")     # local only, never sent to tab
OUT = os.path.join(HERE, "data.json")

POSITION = {"chair": "Chair", "panellist": "Panellist", "trainee": "Trainee"}


class SkipAdminPage(Exception):
    """Not an error: this client authenticated with a token, and the two admin
    pages need a session. Raised so the skip and a genuine failure take
    different paths and read differently in the log."""


def load_state():
    if os.path.exists(STATE):
        return json.load(open(STATE))
    return {"extra_testers": [], "panel_size": {}, "notes": {}, "manual_tests": []}


def rid(url):
    """Last path segment of an API url -> int id."""
    return int(str(url).rstrip("/").rsplit("/", 1)[1]) if url else None


def run(log=print):
    t = TabRead()
    st = load_state()
    log("reading tournament…")

    with ThreadPoolExecutor(max_workers=8) as ex:
        f_tour = ex.submit(t.api, "")
        f_prefs = ex.submit(t.api, "preferences", True)
        f_rounds = ex.submit(t.api, "rounds", True)
        f_bc = ex.submit(t.api, "break-categories", True)
        f_sc = ex.submit(t.api, "speaker-categories", True)
        f_inst = ex.submit(lambda: t.api("institutions", tournament=False, paginate=True))
        f_adj = ex.submit(t.api, "adjudicators", True)
        f_team = ex.submit(t.api, "teams", True)
    tour = f_tour.result()
    prefs = {p["identifier"]: p["value"] for p in f_prefs.result()}
    rounds = sorted(f_rounds.result(), key=lambda r: r["seq"])
    breakcats = f_bc.result()
    spkcats = f_sc.result()
    insts = {i["url"]: i for i in f_inst.result()}
    adjs = f_adj.result()
    teams = f_team.result()
    log(f"  {len(rounds)} rounds · {len(adjs)} judges · {len(teams)} teams")

    teams_per_debate = int(prefs.get("debate_rules__teams_in_debate", 4))
    bc_by_url = {b["url"]: b for b in breakcats}

    # ---------- rounds, classified from live config ----------
    R = []
    for r in rounds:
        R.append({
            "seq": r["seq"], "name": r["name"], "abbr": r["abbreviation"],
            "outround": r["stage"] == "E",
            "break_category": (bc_by_url.get(r.get("break_category")) or {}).get("name"),
            "break_slug": (bc_by_url.get(r.get("break_category")) or {}).get("slug"),
            "completed": r["completed"], "silent": r["silent"],
            "draw_released": r["draw_status"] in ("R",),
            "draw_made": r["draw_status"] in ("D", "C", "R"),
            "draw_status": {"N": "Not started", "D": "Draft", "C": "Confirmed",
                            "R": "Released"}.get(r["draw_status"], r["draw_status"]),
            "motions_released": r["motions_released"],
            "feedback_weight": r["feedback_weight"],
        })

    # ---------- outround plan, derived not hardcoded ----------
    plan = []
    for bc in sorted(breakcats, key=lambda b: b["seq"]):
        elims = [r for r in R if r["outround"] and r["break_slug"] == bc["slug"]]
        rooms, steps = bc["break_size"] / teams_per_debate, []
        for r in elims:
            steps.append({**r, "rooms": max(1, int(round(rooms))),
                          "teams_in": max(teams_per_debate, int(round(rooms * teams_per_debate)))})
            rooms = rooms / 2
        expected = []
        n = bc["break_size"] / teams_per_debate
        while n >= 1:
            expected.append(int(round(n))); n /= 2
        plan.append({
            "name": bc["name"], "slug": bc["slug"], "break_size": bc["break_size"],
            "is_general": bc["is_general"], "rounds": steps,
            "rounds_expected": len(expected), "rounds_configured": len(elims),
            "matches": len(expected) == len(elims),
        })

    # ---------- eligibility (the empty-EFL check) ----------
    def _bc_elig(bc):
        try:
            e = t.api(f"break-categories/{bc['id']}/eligibility")
            return {"name": bc["name"], "slug": bc["slug"],
                    "teams": len(e.get("team_set", [])), "break_size": bc["break_size"]}
        except Exception:
            return None

    def _sc_elig(sc):
        try:
            e = t.api(f"speaker-categories/{sc['id']}/eligibility")
            return {"name": sc["name"] + " (speakers)", "slug": sc["slug"],
                    "teams": len(e.get("speaker_set", [])), "break_size": None}
        except Exception:
            return None
    with ThreadPoolExecutor(max_workers=6) as ex:
        elig = [x for x in list(ex.map(_bc_elig, breakcats)) + list(ex.map(_sc_elig, spkcats)) if x]

    # ---------- judges ----------
    A = {}
    for a in adjs:
        A[a["id"]] = {
            "id": a["id"], "name": a["name"],
            "institution": (insts.get(a["institution"]) or {}).get("name", "—"),
            "inst_code": (insts.get(a["institution"]) or {}).get("code", "—"),
            "region": (insts.get(a["institution"]) or {}).get("region"),
            "base_score": a["base_score"],
            "gender": a.get("gender"), "pronoun": a.get("pronoun"),
            "adjcore": a["adj_core"], "independent": a["independent"],
            "trainee": a["trainee"], "breaking": a["breaking"],
            "conflicts_team": len(a["team_conflicts"]),
            "conflicts_adj": len(a["adjudicator_conflicts"]),
            "conflicts_inst": len(a["institution_conflicts"]),
            "inst_id": rid(a["institution"]),
            "conf_team_ids": [rid(u) for u in a["team_conflicts"]],
            "conf_adj_ids": [rid(u) for u in a["adjudicator_conflicts"]],
            "conf_inst_ids": [rid(u) for u in a["institution_conflicts"]],
            "has_email": bool(a["email"]),
            "rounds": [], "feedback": [], "tested": [], "tested_others": [],
        }

    team_name = {tm["url"]: tm["short_name"] for tm in teams}

    # ---------- draws, per round ----------
    log("reading draws…")
    drawn = [r for r in R if r["draw_made"]]          # skip rounds with no draw

    def _pairings(r):
        try:
            return r["seq"], t.api(f"rounds/{r['seq']}/pairings", paginate=True)
        except Exception:
            return r["seq"], []
    with ThreadPoolExecutor(max_workers=6) as ex:
        draws = dict(ex.map(_pairings, drawn))
    for r in drawn:
        ps = draws.get(r["seq"], [])
        for d in ps:
            adjd = d.get("adjudicators") or {}
            panel = ([(rid(adjd.get("chair")), "chair")] if adjd.get("chair") else []) \
                + [(rid(u), "panellist") for u in (adjd.get("panellists") or [])] \
                + [(rid(u), "trainee") for u in (adjd.get("trainees") or [])]
            room = (d.get("venue") or "")
            sides = [{"side": dt.get("side"), "team": team_name.get(dt.get("team"), "?")}
                     for dt in (d.get("teams") or [])]
            for aid, pos in panel:
                if aid in A:
                    A[aid]["rounds"].append({
                        "seq": r["seq"], "round": r["abbr"], "position": POSITION[pos],
                        "debate": d["id"], "bracket": d.get("bracket"),
                        "importance": d.get("importance"), "teams": sides,
                        "panel_size": len(panel),
                        "with": [x for x, _ in panel if x != aid],
                    })

    # ---------- feedback ----------
    log("reading feedback…")
    try:
        fb = t.api("feedback", paginate=True)
    except Exception:
        fb = []
    try:
        fq = t.api("feedback-questions", paginate=True)
    except Exception:
        fq = []
    qmap = {q["url"]: q for q in fq}
    team_by_url = {tm["url"]: tm for tm in teams}
    adj_by_url = {f"{t.base}/api/v1/tournaments/{t.slug}/adjudicators/{a['id']}": a for a in adjs}
    TEXTY = {"tl", "ts", "t"}          # long text / short text answer types

    def _round_of(debate_url):
        """debate urls look like .../rounds/<seq>/pairings/<id>"""
        m = re.search(r"/rounds/(\d+)/pairings/", str(debate_url or ""))
        return int(m.group(1)) if m else None

    for f in fb:
        aid = rid(f.get("adjudicator"))
        if aid not in A:
            continue
        src = f.get("source") or ""
        if "/teams/" in src:
            from_type, from_name = "team", (team_by_url.get(src) or {}).get("short_name", "a team")
        elif "/adjudicators/" in src:
            from_type = "judge"
            sid = rid(src)
            from_name = A[sid]["name"] if sid in A else (adj_by_url.get(src) or {}).get("name", "a judge")
        else:
            from_type, from_name = "other", "—"
        answers, comments = [], []
        for ans in f.get("answers", []) or []:
            q = qmap.get(ans.get("question"), {})
            row = {"q": q.get("text") or q.get("name") or "Question",
                   "a": ans.get("answer"), "type": q.get("answer_type")}
            answers.append(row)
            val = str(row["a"] or "").strip()
            if row["type"] in TEXTY and len(val) > 1:
                comments.append({"q": row["q"], "a": val})
        seq = _round_of(f.get("debate"))
        A[aid]["feedback"].append({
            "score": f.get("score"), "confirmed": f.get("confirmed"),
            "ignored": f.get("ignored"), "debate": rid(f.get("debate")),
            "seq": seq, "round": next((r["abbr"] for r in R if r["seq"] == seq), "—"),
            "timestamp": f.get("timestamp"),
            "from_type": from_type, "from_name": from_name,
            "answers": answers, "comments": comments,
        })

    # ---------- testers ----------
    default_testers = {a["id"] for a in adjs if a["adj_core"]}
    extra = set(st.get("extra_testers", []))
    testers = default_testers | extra
    for aid in A:
        A[aid]["is_tester"] = aid in testers
        A[aid]["tester_source"] = ("Adj core" if aid in default_testers
                                   else "Added by adjcore" if aid in extra else None)

    # ---------- test events, derived from who sat with whom ----------
    for aid, a in A.items():
        for sit in a["rounds"]:
            present = [x for x in sit["with"] if x in testers and x != aid]
            if not present:
                continue
            if aid in testers:
                continue          # testers testing each other doesn't count as being tested
            a["tested"].append({
                "seq": sit["seq"], "round": sit["round"],
                "as": sit["position"],
                "by": [{"id": x, "name": A[x]["name"],
                        "their_position": next((s["position"] for s in A[x]["rounds"]
                                                if s["debate"] == sit["debate"]), "?")}
                       for x in present],
            })
            for x in present:
                A[x]["tested_others"].append({"seq": sit["seq"], "round": sit["round"],
                                              "id": aid, "name": a["name"], "as": sit["position"]})

    for m in st.get("manual_tests", []):
        a = A.get(m.get("judge_id"))
        if a:
            a["tested"].append({"seq": m.get("seq"), "round": m.get("round", "—"),
                                "as": m.get("as", "Panellist"),
                                "by": [{"id": None, "name": m.get("by", "adjcore"),
                                        "their_position": "logged by hand"}],
                                "manual": True})

    # ---------- name every panel, tested or not ----------
    # adjcore need to see who chaired them and who sat with them in EVERY round,
    # not only the rounds where a tester happened to be present.
    pos_in = {}
    for aid, a in A.items():
        for sit in a["rounds"]:
            pos_in[(sit["debate"], aid)] = sit["position"]
    order = {"Chair": 0, "Panellist": 1, "Trainee": 2}
    for aid, a in A.items():
        for sit in a["rounds"]:
            people = []
            for x in sit["with"]:
                if x not in A:
                    continue
                people.append({
                    "id": x, "name": A[x]["name"],
                    "position": pos_in.get((sit["debate"], x), "?"),
                    "is_tester": A[x]["is_tester"],
                })
            people.sort(key=lambda p: (order.get(p["position"], 9), p["name"]))
            sit["panel"] = people
            sit["chair"] = next((p for p in people if p["position"] == "Chair"), None)

    # ---------- per-judge rollup ----------
    for a in A.values():
        seen = {x["as"] for x in a["tested"]}
        a["tested_as_chair"] = "Chair" in seen
        a["tested_as_panellist"] = "Panellist" in seen
        a["tested_as_trainee"] = "Trainee" in seen
        # best position a tester has actually watched them in
        a["best_seen"] = ("Chair" if a["tested_as_chair"]
                          else "Panellist" if a["tested_as_panellist"]
                          else "Trainee" if a["tested_as_trainee"]
                          else None)
        a["test_count"] = len(a["tested"])
        live = [f for f in a["feedback"] if f.get("score") is not None and not f.get("ignored")]
        scores = [f["score"] for f in live]
        a["feedback_n"] = len(scores)
        a["feedback_avg"] = round(sum(scores) / len(scores), 2) if scores else None
        for grp in ("team", "judge"):
            g = [f["score"] for f in live if f["from_type"] == grp]
            a[f"feedback_{grp}_n"] = len(g)
            a[f"feedback_{grp}_avg"] = round(sum(g) / len(g), 2) if g else None
        a["comment_count"] = sum(len(f.get("comments", [])) for f in a["feedback"])
        a["feedback"].sort(key=lambda f: (f.get("seq") or 0, f.get("from_type") or ""))
        a["rounds_judged"] = len(a["rounds"])
        a["chaired"] = sum(1 for s in a["rounds"] if s["position"] == "Chair")
        a["panelled"] = sum(1 for s in a["rounds"] if s["position"] == "Panellist")

    # ---------- feedback owed (who still has to submit) ----------
    # Feedback progress and check-in status are ordinary admin pages, not API
    # endpoints, so they need a session. With a token alone the rest of the
    # dashboard is fine and these two columns are simply blank — worth saying
    # out loud rather than leaving somebody to wonder why a column is empty.
    log("reading feedback progress…")
    owed_j, owed_t = {}, []
    admin_pages = t.needs_admin_pages()
    if not admin_pages:
        log("  skipped — feedback progress needs a username and password as well "
            "as a token (it is an admin page, not an API endpoint)")
    try:
        if not admin_pages:
            raise SkipAdminPage
        vd = t.vuedata("admin/feedback/progress/")
        tabs = vd.get("tablesData") or []
        def cell(c):
            import re as _re
            if isinstance(c, dict):
                for k in ("text", "sort"):
                    if c.get(k) not in (None, ""):
                        return _re.sub(r"<[^>]+>", "", str(c[k])).strip()
                return ""
            return str(c)
        for tb in tabs:
            head = [h.get("title") or h.get("key", "") for h in tb.get("head", [])]
            rows = [[cell(c) for c in r] for r in tb.get("data", [])]
            if "owed" not in head:
                continue
            io, ip_, isub = head.index("owed"), head.index("percent"), 0
            if "name" in head:      # judges
                inm = head.index("name")
                for r in rows:
                    owed_j[r[inm]] = {"owed": r[io], "percent": r[ip_]}
            elif "team" in head:    # teams
                itm = head.index("team")
                for r in rows:
                    owed_t.append({"team": r[itm], "owed": r[io], "percent": r[ip_]})
    except SkipAdminPage:
        pass
    except Exception as e:
        log(f"  feedback progress unavailable: {e}")
    for a in A.values():
        o = owed_j.get(a["name"])
        a["owes_feedback"] = o["owed"] if o else None
        a["feedback_done_pct"] = o["percent"] if o else None

    # ---------- outround draws, room by room (empty until adjcore make the draw) ----------
    outround_draws = {}
    for r in R:
        if not r["outround"]:
            continue
        rows = []
        for d in draws.get(r["seq"], []):
            adjd = d.get("adjudicators") or {}
            rows.append({
                "debate": d["id"], "room": (d.get("venue") or ""),
                "teams": [{"side": dt.get("side"),
                           "team": team_name.get(dt.get("team"), "?"),
                           "team_id": rid(dt.get("team"))}
                          for dt in (d.get("teams") or [])],
                "chair": rid(adjd.get("chair")),
                "panellists": [rid(u) for u in (adjd.get("panellists") or [])],
                "trainees": [rid(u) for u in (adjd.get("trainees") or [])],
            })
        outround_draws[r["abbr"]] = rows

    # ---------- the break itself, per category (empty until adjcore confirm it) ----------
    log("reading breaks\u2026")
    breaks = {}
    for bc in breakcats:
        try:
            rows = t.api(f"break-categories/{bc['id']}/break", paginate=True)
        except Exception as e:
            log(f"  break for {bc['name']} unavailable: {e}")
            rows = []
        breaks[bc["slug"]] = [
            {"team": rid(r.get("team")), "rank": r.get("rank"),
             "break_rank": r.get("break_rank"), "remark": r.get("remark")}
            for r in rows]
        # break_rank is set only on the teams that actually broke; the endpoint
        # also returns everyone else in the category with a remark, so counting
        # rows would report the whole eligible field as having broken.
        log(f"  {bc['name']}: {sum(1 for r in rows if r.get('break_rank'))} of "
            f"{len(rows)} eligible broke")

    # ---------- check-ins ----------
    log("reading check-ins…")
    checked = {}
    speakers_in = speakers_all = 0        # set up front, so any skip or failure
                                          # below leaves a defined value
    if not admin_pages:
        log("  skipped — check-in status needs a username and password as well "
            "as a token")
    try:
        if not admin_pages:
            raise SkipAdminPage
        vd = t.vuedata("admin/checkins/status/people/")
        done = {e["identifier"] for e in vd.get("events", [])}
        for p in vd.get("adjudicators", []) or []:
            checked[p["id"]] = bool(set(p["identifier"]) & done)
        speakers_in = sum(1 for p in (vd.get("speakers") or [])
                          if set(p["identifier"]) & done)
        speakers_all = len(vd.get("speakers") or [])
    except SkipAdminPage:
        pass
    except Exception as e:
        log(f"  check-ins unavailable: {e}")
    for aid, a in A.items():
        a["checked_in"] = checked.get(aid)

    data = {
        "pulled_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "tournament": {"name": tour["name"], "short": tour["short_name"],
                       "slug": tour["slug"],
                       "teams_per_debate": teams_per_debate,
                       "speakers_per_team": int(prefs.get("debate_rules__substantive_speakers", 2)),
                       "feedback_min": prefs.get("feedback__adj_min_score"),
                       "feedback_max": prefs.get("feedback__adj_max_score"),
                       "min_voting_score": prefs.get("draw_rules__adj_min_voting_score"),
                       "feedback_paths": prefs.get("feedback__feedback_paths"),
                       "sides": prefs.get("debate_rules__side_names")},
        "rounds": R,
        "break_categories": [{"name": b["name"], "slug": b["slug"],
                              "break_size": b["break_size"], "is_general": b["is_general"]}
                             for b in breakcats],
        "speaker_categories": [{"name": s["name"], "slug": s["slug"]} for s in spkcats],
        "outround_plan": plan,
        "eligibility": elig,
        "judges": sorted(A.values(), key=lambda x: x["name"].lower()),
        "counts": {"judges": len(A), "teams": len(teams),
                   "testers": len(testers), "adjcore": len(default_testers),
                   "speakers_in": speakers_in, "speakers_all": speakers_all},
        "teams_owing_feedback": owed_t,
        "teams_index": [
            {"id": tm["id"], "short_name": tm["short_name"],
             "inst_id": rid(tm.get("institution")),
             "inst_code": (insts.get(tm.get("institution")) or {}).get("code", "\u2014"),
             "region": (insts.get(tm.get("institution")) or {}).get("region"),
             "conf_inst_ids": [rid(u) for u in (tm.get("institution_conflicts") or [])],
             "break_slugs": [(bc_by_url.get(u) or {}).get("slug")
                             for u in (tm.get("break_categories") or [])],
             } for tm in teams],
        "breaks": breaks,
        "outround_draws": outround_draws,
        "state": st,
    }
    json.dump(data, open(OUT, "w"), ensure_ascii=False)
    log(f"done — {len(A)} judges, {sum(len(v) for v in draws.values())} debates, "
        f"{len(fb)} feedback")
    return data


if __name__ == "__main__":
    run()
