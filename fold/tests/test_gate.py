"""
test_gate.py — prove the built page cannot be carrying anything private.

Run it after every build. It reads the payload that actually went into
dist/index.html (not raw.json, which could drift) and checks invariants that
would each be violated by a real leak:

  1. every key is declared in gate.ALLOWED
  2. no float appears anywhere EXCEPT the declared speaker fields — speaks and
     feedback averages are floats in Tabbycat while points and counts are not,
     so a float outside those fields is still the tell it always was
  3. per-round points only exist for rounds whose rankings are public
  4. rooms and panels only exist for rounds whose draw is public
  5. per-team points are inside the format's scale (3/2/1/0 in a four-team
     debate, 1/0 in a two-team one) — read off the tournament, not assumed
  6. the page's own script makes no network call

    python3 tests/test_gate.py
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, os.pardir)
sys.path.insert(0, ROOT)
import gate  # noqa: E402

PAGE = os.path.join(ROOT, "dist", "index.html")
fails = []


def check(ok, msg):
    print(("  ok   " if ok else "  FAIL ") + msg)
    if not ok:
        fails.append(msg)


def payload_from_page(path):
    html = open(path).read()
    m = re.search(r"const DATA = (\{.*?\});\n", html, re.S)
    if not m:
        sys.exit("could not find the data blob in " + path)
    return json.loads(m.group(1)), html


def floats(node, path="$"):
    if isinstance(node, float):
        return [f"{path} = {node}"]
    if isinstance(node, dict):
        return [x for k, v in node.items() for x in floats(v, f"{path}.{k}")]
    if isinstance(node, list):
        return [x for i, v in enumerate(node) for x in floats(v, f"{path}[{i}]")]
    return []


def main():
    if not os.path.exists(PAGE):
        sys.exit("no built page yet — run `python3 build.py` first")
    d, html = payload_from_page(PAGE)
    print(f"checking {os.path.relpath(PAGE)} ({len(html)/1024:.0f} KB)\n")

    # 1 — the allowlist
    try:
        gate.assert_clean(d)
        check(True, "every field in the payload is declared in gate.ALLOWED")
    except gate.GateViolation as e:
        check(False, str(e))

    # 2 — no float OUTSIDE the declared speaker fields.
    #
    # This was "no float anywhere", which was the single sharpest check here:
    # speaks and feedback averages are floats in Tabbycat while points and counts
    # are integers, so any float was evidence something score-shaped had got in,
    # whatever it was called. Publishing a released speaker tab means floats are
    # now legitimate — but only in four places, so the check is narrowed rather
    # than dropped and keeps working everywhere else.
    import re as _re
    ALLOWED_FLOAT = (
        _re.compile(r"^\$\.speaker_scores\[\d+\]\.(total|avg|stdev)$"),
        _re.compile(r"^\$\.speaker_scores\[\d+\]\.by_round\.\d+\[\d+\]\.score$"),
        _re.compile(r"^\$\.standings\[\d+\]\.speaks$"),
    )
    f = [x for x in floats(d)
         if not any(rx.match(x.split(" = ")[0]) for rx in ALLOWED_FLOAT)]
    check(not f, "no float outside the declared speaker fields"
          + ("" if not f else " — found " + "; ".join(f[:5])))

    # 2b — the released tabs, and everything that must travel with them
    g = d["gate"]
    spk = d.get("speaker_scores")
    if g.get("speaker_tab_released"):
        check(spk is not None and len(spk) > 0,
              f"the speaker tab is released, so it is published ({len(spk or [])} rows)")
        # Tabbycat's anonymous flag: the scores stay, the name goes.
        named_anon = [r for r in (spk or []) if r.get("anon") and r.get("name")]
        check(not named_anon,
              f"no anonymous speaker is named ({sum(1 for r in (spk or []) if r.get('anon'))} anonymous)"
              + ("" if not named_anon else f" — {[r['name'] for r in named_anon][:3]}"))
        # A tab limit means the tournament publishes only that far down.
        cut = g.get("speaker_tab_limit") or 0
        over = [r["rank"] for r in (spk or []) if cut and (r.get("rank") or 0) > cut]
        check(not over,
              (f"the tab stops at the published limit of {cut}" if cut
               else "no tab limit is set, so the whole tab is published")
              + ("" if not over else f" — ranks past it: {sorted(set(over))[:5]}"))
    else:
        check(spk is None,
              "the speaker tab is not released, so no speaker data is published"
              + ("" if spk is None else f" — {len(spk)} rows LEAKED"))

    speaks = [r for r in d["standings"] if "speaks" in r]
    if g.get("team_tab_released"):
        check(bool(speaks), f"the team tab is released, so team speaks are published "
                            f"({len(speaks)} teams)")
    else:
        check(not speaks, "the team tab is not released, so no team speaks are published"
              + ("" if not speaks else f" — {len(speaks)} teams LEAKED"))

    # Releasing the speaker tab does not release replies or the adjudicator tab.
    # Each has its own switch, and neither is ever published by this tool.
    body = html.lower()
    for word, why in (("replies_avg", "reply-speech averages"),
                      ("replies_count", "reply-speech counts"),
                      ("draw_strength", "draw strength")):
        check(word not in body, f"no {why} anywhere in the page")

    rounds = {r["seq"]: r for r in d["rounds"]}
    res_ok = {s for s, r in rounds.items() if r["results_public"]}
    draw_ok = {s for s, r in rounds.items() if r["draw_public"]}

    # 3 — points only for rounds whose rankings are public
    stray = [(s["t"], k) for s in d["standings"] for k in s["by_round"] if int(k) not in res_ok]
    check(not stray, f"per-round points exist only for {sorted(res_ok)}"
          + ("" if not stray else f" — {len(stray)} stray, e.g. {stray[:3]}"))

    # The points scale is the format's, not BP's: a four-team debate awards
    # 3/2/1/0, a two-team one 1/0. Reading it off teams_per_debate means this
    # check stays a real check instead of a range so wide it can never fail.
    max_points = int((d["tournament"] or {}).get("teams_per_debate") or 4) - 1
    bad_pts = [(s["t"], k, v) for s in d["standings"] for k, v in s["by_round"].items()
               if not isinstance(v, int) or not 0 <= v <= max_points]
    check(not bad_pts, f"every per-round value is inside this format's scale (0-{max_points})"
          + ("" if not bad_pts else f" — {bad_pts[:3]}"))

    # 4 — rooms and panels only where the draw is public
    bad_room = {x["round"] for x in d["debates"] if x["round"] not in draw_ok and x["room"]}
    bad_panel = {x["round"] for x in d["debates"] if x["round"] not in draw_ok and x["panel"]}
    check(not bad_room, f"no room name outside {sorted(draw_ok)}"
          + ("" if not bad_room else f" — leaked in {sorted(bad_room)}"))
    check(not bad_panel, f"no judge panel outside {sorted(draw_ok)}"
          + ("" if not bad_panel else f" — leaked in {sorted(bad_panel)}"))

    bad_dpts = [x["round"] for x in d["debates"]
                if x["round"] not in res_ok and any(t["pts"] is not None for t in x["teams"])]
    check(not bad_dpts, "no in-room result outside the public rounds"
          + ("" if not bad_dpts else f" — leaked in {sorted(set(bad_dpts))}"))

    # silent rounds are the whole reason for rule 4 — say so out loud
    silent = sorted(r["abbr"] for r in d["rounds"] if r["silent"] and not r["results_public"])
    check(all(s not in [rounds[x]["abbr"] for x in res_ok] for s in silent),
          f"silent rounds stay silent: {', '.join(silent) or 'none'}")

    # 5 — the page cannot phone home
    script = html.split("<script>")[-1]
    calls = [w for w in ("fetch(", "XMLHttpRequest", "WebSocket", "EventSource",
                         "import(", "navigator.sendBeacon") if w in script]
    check(not calls, "the page's script makes no network call"
          + ("" if not calls else " — found " + ", ".join(calls)))

    ext = re.findall(r'(?:src|href)="(https?://[^"]+)"', html)
    allowed = ("https://fonts.googleapis.com", "https://fonts.gstatic.com",
               d["tournament"].get("site") or "\0")
    bad_ext = [u for u in ext if not u.startswith(allowed)]
    check(not bad_ext, "the only outside references are the font host and the tab itself"
          + ("" if not bad_ext else " — " + ", ".join(bad_ext[:3])))

    print()
    if fails:
        print(f"{len(fails)} check(s) failed — do not deploy this build.")
        sys.exit(1)
    print("all checks passed — safe to deploy.")


if __name__ == "__main__":
    main()
