#!/usr/bin/env python3
"""
pull.py — read-only pull of everything the feedback consolidator needs.

Writes data/raw.json. That file carries every adjudicator's `url_key`, and a
url_key *is* their private URL: whoever holds it can submit ballots and feedback
as them. So data/ is gitignored, never deployed, and treated as credential
material.

  ./pull.py            pull everything
  ./pull.py --stats    pull, then print what came back
"""
import json, os, sys, re, collections
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, "core"))
# TabRead is the read-only client. The feedback tool used to use a separate
# client that also had a write method; there is now only one, and it cannot.
from tabread import TabRead as Tabby

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "raw.json")

# Which question holds the written comment is NOT configured here. Tabbycat marks
# each feedback question with an `answer_type`, and the long-text / short-text ones
# ("tl", "ts") are the written ones whatever they happen to be called on your form.
# Everything else is a scale or a yes/no, and a yes/no is a score by another name,
# so it is never read.
WRITTEN_TYPES = ("tl", "ts")


def rid(url):
    return int(url.rstrip("/").split("/")[-1]) if url else None


def main():
    t = Tabby()
    print("logged in as", t.user["username"])

    questions = t.api("feedback-questions", paginate=True)
    written_ids = {q["id"] for q in questions
                   if q.get("answer_type") in WRITTEN_TYPES}
    if not written_ids:
        raise SystemExit("no long-text feedback question found — nothing to summarise")

    feedback = t.api("feedback", params={"limit": 500}, paginate=True)
    adjudicators = t.api("adjudicators", paginate=True)
    teams = t.api("teams", paginate=True)
    rounds = t.api("rounds", paginate=True)
    motions = t.api("motions", paginate=True)
    # The format is read, never assumed: how many teams are in a debate decides
    # what craft vocabulary a summary may use, and the break categories are round
    # names in disguise ("the EFL semis" places a debate as surely as "round 5").
    prefs = {x["identifier"]: x["value"] for x in t.api("preferences", paginate=True)}
    breakcats = t.api("break-categories", paginate=True)
    # `institution` on a team/adjudicator is a URL, not a name — resolve it once.
    institutions = t.api("institutions", tournament=False, paginate=True)

    # Strip the feedback down to the only two things that matter downstream: who
    # it is ABOUT, and what was written. The submitter, the debate, the round,
    # the score and the timestamp are all dropped here, at the pull, so nothing
    # further down the chain can leak what it never received.
    written = []
    for f in feedback:
        if f.get("ignored"):
            continue
        text = ""
        for a in f.get("answers") or []:
            if rid(a["question"]) in written_ids and isinstance(a.get("answer"), str):
                if a["answer"].strip():
                    text = a["answer"].strip()
        if not text:
            continue
        written.append({
            "adj": rid(f["adjudicator"]),
            "text": text,
            # kept only so the bundler can shuffle deterministically and so a
            # duplicate submission can be spotted; never reaches a summary.
            "fid": f["id"],
        })

    out = {
        "pulled_at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
        # The page titles itself from this, so nothing anywhere says the name of a
        # tournament that is not yours.
        "tournament": (t.api("", tournament=True) or {}).get("name") or "",
        "format": {
            "teams_in_debate": int(prefs.get("debate_rules__teams_in_debate", 4) or 4),
            "speakers_per_team": int(prefs.get("debate_rules__substantive_speakers", 2) or 2),
            "side_names": prefs.get("debate_rules__side_names") or "",
        },
        "categories": sorted({v for b in breakcats for v in
                              (b.get("name"), b.get("slug")) if v}),
        "written": written,
        "adjudicators": [{
            "id": a["id"], "name": a["name"], "url_key": a.get("url_key"),
            "institution": (a.get("institution") or ""),
        } for a in adjudicators],
        # Everything below exists for one reason: gate.py needs to know every
        # name, code and motion term that must NOT appear in a summary.
        "team_names": sorted({v for tm in teams for v in
                              (tm.get("long_name"), tm.get("short_name"),
                               tm.get("reference"), tm.get("code_name"))
                              if v}),
        "institutions": sorted({i.get("name") or "" for i in institutions} |
                               {i.get("code") or "" for i in institutions}),
        "round_names": sorted({r["abbreviation"] for r in rounds} |
                              {r["name"] for r in rounds}),
        "motions": [m.get("text", "") for m in motions],
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    os.chmod(OUT, 0o600)

    per = collections.Counter(w["adj"] for w in written)
    print(f"wrote {OUT}  ({len(written)} written comments about {len(per)} judges)")
    if "--stats" in sys.argv:
        counts = sorted(per.values())
        print("  comments per judge: min %d  median %d  max %d"
              % (counts[0], counts[len(counts) // 2], counts[-1]))
        thin = [a["name"] for a in out["adjudicators"] if per[a["id"]] < 3]
        print(f"  {len(thin)} judges with fewer than 3 written comments")


if __name__ == "__main__":
    main()
