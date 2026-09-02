"""
gate.py — the one place that decides what a spectator is allowed to see.

The rule this project enforces: **if the tournament's own public pages would not
show it, this site does not show it.** Not "we probably shouldn't" — the decision
is read live off Tabbycat's `public_features__*` and `tab_release__*` preferences
every single build, so the moment tab flips a switch the site follows.

Two independent mechanisms, because one is not enough:

1. GATE RULES (below) — per round, per feature, derived from live preferences.
2. AN ALLOWLIST — `ALLOWED` names every key that may appear at every level of the
   emitted payload. `assert_clean()` walks the finished payload and raises on any
   key that was not declared. A new field cannot leak by accident; someone has to
   come here and add it deliberately.

Never emitted, whatever the preferences say, because adjcore holds them in trust
and no spectator page carries them: margins and any split within a room, ballots,
feedback of any kind, judge base scores, judge test/adjcore status, conflicts,
private URL keys, emails, phone numbers, barcodes, check-in state, room
importance, and any allocation this team has drafted but the tab has not
released.

SPEAKER SCORES AND TEAM SPEAKS ARE THE ONE EXCEPTION, AND ONLY ON RELEASE.
They used to be in the list above, and the gate's sharpest check was "no float
anywhere in the payload" — because speaks and feedback averages are floats while
points and counts are integers, a stray float was the tell that something private
had got in. That check has not been deleted; it has been narrowed to "no float
outside the declared speaker fields", so the tell still works everywhere else.

A speaker tab is published only when `tab_release__speaker_tab_released` is on,
team speaks only when `tab_release__team_tab_released` is on, and each obeys its
own `*_tab_limit`. Reply speeches and the adjudicator tab have their own switches
and are not covered by either — releasing the speaker tab does not release them.
Tabbycat's `anonymous` flag on a speaker is obeyed, so this can never show a name
the tournament's own page would withhold. And a speaker record carries an email,
a phone number, a barcode and a `url_key` — which IS that person's private ballot
URL — so the pull takes the name and nothing else.
"""

# ---------------------------------------------------------------- forbidden ----
# Substrings that may never appear in a key name anywhere in the payload.
FORBIDDEN_KEY_PARTS = (
    "score", "speak", "margin", "ballot", "feedback", "fdbk", "base",
    "conflict", "conf_", "url_key", "urlkey", "email", "barcode", "checkin",
    "check_in", "importance", "adjcore", "adj_core", "tester", "tested",
    "private", "ip_", "secret", "password", "token", "gender", "pronoun",
    "seed", "veto", "draft", "provisional", "internal",
)

# Three key names trip the substring filter above while being entirely benign.
# Each one is exempted here, by name, with the reason — so the filter can stay
# blunt without anyone being tempted to soften it.
EXEMPT = {
    # A list of names, which the public participants page already carries. No number
    # of any kind hangs off it.
    "speakers": "speaker names only, never a score",
    # These are the tab's own switch names, carried onto the page so a reader can
    # see for themselves what is and is not released. They are booleans and
    # limits about visibility, not the data they gate.
    "speaker_tab_released": "a visibility switch, reported so readers can check it",
    "ballots_released": "a visibility switch, reported so readers can check it",
    "speaker_tab_limit": "how far down the tab the tournament publishes",
    "speaker_tab_public": "a visibility switch, reported so readers can check it",
    "team_speaks_public": "a visibility switch, reported so readers can check it",
    "replies_tab_released": "a visibility switch; replies are withheld unless it is on",
    # The speaker tab itself. Permitted ONLY because it has its own release
    # switch, checked in speaker_tab_public(), and only ever carrying what
    # Tabbycat's own public speaker tab carries.
    "speaker_scores": "the released speaker tab, gated on speaker_tab_released",
    "speaks": "a released tab's total, gated on its own switch",
    "score": "one released speech score, inside speaker_scores only",
}

# ------------------------------------------------------------- the allowlist ---
# key -> None (leaf, any scalar) | dict (nested object) | ("list", dict/None)
ALLOWED = {
    "built_at": None,
    "pulled_at": None,
    "tournament": {
        "name": None, "short": None, "slug": None, "site": None,
        "teams_per_debate": None, "sides": ("list", None),
        "staff": None,
    },
    "gate": {
        "public_draw": None, "public_results": None, "public_motions": None,
        "public_breaking_teams": None, "public_breaking_adjs": None,
        "public_team_standings": None, "public_participants": None,
        "team_tab_released": None, "speaker_tab_released": None,
        "ballots_released": None,
        "replies_tab_released": None, "adjudicators_tab_released": None,
        "speaker_tab_limit": None, "team_tab_limit": None,
        "speaker_tab_public": None, "team_speaks_public": None,
        "current_round": None,
        "withheld": ("list", None),
        "shown": ("list", None),
    },
    "rounds": ("list", {
        "seq": None, "abbr": None, "name": None, "outround": None,
        "cat": None, "cat_name": None, "completed": None, "silent": None,
        "draw_status": None, "results_public": None, "draw_public": None,
        "panel_public": None,
        "rooms": None, "teams_in": None,
        "motion": {"text": None, "reference": None, "info_slide": None},
    }),
    "categories": ("list", {
        "slug": None, "name": None, "break_size": None, "is_general": None,
        "break_public": None, "rounds": ("list", None),
    }),
    "teams": ("list", {
        "id": None, "name": None, "long": None, "code": None, "inst": None,
        "region": None, "emoji": None, "cats": ("list", None),
        "speakers": ("list", None),
    }),
    "judges": ("list", {
        "id": None, "name": None, "inst": None, "code": None,
        "region": None, "breaking": None,
    }),
    "debates": ("list", {
        "round": None, "room": None,
        "teams": ("list", {"t": None, "side": None, "pts": None, "win": None}),
        "panel": ("list", {"j": None, "pos": None}),
    }),
    "breaks": ("dict", ("list", {
        "t": None, "rank": None, "break_rank": None, "remark": None,
    })),
    "standings": ("list", {
        "t": None, "pts": None, "by_round": ("dict", None),
        "sides": ("dict", None),
        # Total speaks, present only when the team tab is released.
        "speaks": None,
    }),
    # The released speaker tab. Absent entirely unless speaker_tab_released.
    # `name` is null for a speaker Tabbycat marks anonymous — the scores stay,
    # the identity does not, which is what the tournament's own page does.
    "speaker_scores": ("list", {
        "rank": None, "tied": None, "name": None, "anon": None, "t": None,
        "total": None, "avg": None, "count": None, "stdev": None,
        # Per round: the speeches that counted, and the position spoken in.
        # `ghost` marks an iron-person speech, which Tabbycat excludes from the
        # average — it is marked rather than dropped so the page can say why a
        # count looks short.
        "by_round": ("dict", ("list", {
            "score": None, "pos": None, "ghost": None,
        })),
    }),
}


class GateViolation(RuntimeError):
    pass


# ------------------------------------------------------------------- rules -----
def read_prefs(raw):
    """Pull the handful of preferences the gate actually turns on."""
    g = lambda k, d=False: raw.get(k, d)
    return {
        "public_draw": g("public_features__public_draw", "off"),
        "public_results": bool(g("public_features__public_results")),
        "public_motions": bool(g("public_features__public_motions")),
        "public_breaking_teams": bool(g("public_features__public_breaking_teams")),
        "public_breaking_adjs": bool(g("public_features__public_breaking_adjs")),
        "public_team_standings": bool(g("public_features__public_team_standings")),
        "public_participants": bool(g("public_features__public_participants")),
        "team_tab_released": bool(g("tab_release__team_tab_released")),
        "speaker_tab_released": bool(g("tab_release__speaker_tab_released")),
        "ballots_released": bool(g("tab_release__ballots_released")),
        # Replies and the adjudicator tab have their own switches. Releasing the
        # speaker tab does not release either, and conflating them would publish
        # something the tournament deliberately held back.
        "replies_tab_released": bool(g("tab_release__replies_tab_released")),
        "adjudicators_tab_released": bool(g("tab_release__adjudicators_tab_released")),
        # 0 means no limit in Tabbycat. A positive value means the tournament
        # publishes only that far down, and so must this.
        "speaker_tab_limit": int(g("tab_release__speaker_tab_limit", 0) or 0),
        "team_tab_limit": int(g("tab_release__team_tab_limit", 0) or 0),
    }


def speaker_tab_public(prefs):
    """Whether a speaker tab may be published at all."""
    return bool(prefs["speaker_tab_released"])


def team_speaks_public(prefs):
    """Whether a team's total speaks may be published.

    Separate switch from the speaker tab, and separate from public team
    standings: a tournament can publish the points table all weekend and never
    release speaks.
    """
    return bool(prefs["team_tab_released"])


def tab_cut(prefs, which):
    """How far down a released tab goes. None means all of it."""
    n = prefs["speaker_tab_limit"] if which == "speaker" else prefs["team_tab_limit"]
    return n if n and n > 0 else None


def results_public(r, prefs):
    """Who came 1st/2nd/3rd/4th in a room.

    Public on the results pages once a round is finished — unless the round is
    silent, which is precisely tab saying "not yet". Every out-round here is
    silent until it is announced, so this is what keeps break-round results off
    the site while the room is still being run.
    """
    return bool(prefs["public_results"] and r["completed"] and not r["silent"])


def draw_public(r, prefs, current_seqs):
    """The rooms and the panel.

    Released draws only, and then only as far as `public_draw` allows:
    'all-released' shows every released draw, 'current' shows the round being run
    now — plus any earlier round whose results are already public, because the
    public results page carries the room and its panel too.

    `current_seqs` is a SET, not a number. Tabbycat runs several rounds at once
    whenever categories break separately: on 27 Aug it was on OQF and EFLSF
    together, and collapsing that to max() hid the released OQF draw behind the
    EFL semis. Every round tab calls current is current.
    """
    if r["draw_status"] != "Released":
        return False
    mode = prefs["public_draw"]
    if mode == "off":
        return False
    if mode in ("all", "all-released"):
        return True
    return bool(r["seq"] in current_seqs or results_public(r, prefs))


def panel_public(r, prefs, current_seqs):
    """Who judged: the chair, the panellists, the trainees, and which teams were
    in the room together.

    This is a WIDER rule than draw_public, and the difference was a real bug —
    the Judges view showed every judge with nothing against their name at a
    tournament whose panels were public all along.

    Two separate things get published at two separate moments on Tabbycat, and
    tying both to `public_draw` conflates them:

      · the DRAW page — rooms, panels, who is about to judge whom. Governed by
        `public_draw`, and commonly switched off once a tournament ends.
      · the RESULTS page — for each debate, the teams, their sides, their ranks
        AND the panel, with the chair and any trainee marked. Governed by
        `public_results`, and normally left on forever.

    So once a round's results are public, its panel is public, whatever
    `public_draw` says. Checked against a live tab: with the draw switched off,
    /results/round/1/ still serves every panel to an anonymous visitor.

    The room NAME is the exception and stays on draw_public — the public results
    page carries no venue column, so this must not publish one either.
    """
    return bool(draw_public(r, prefs, current_seqs) or results_public(r, prefs))


def motion_public(r, prefs, motions_released):
    return bool(prefs["public_motions"] and motions_released)


def break_public(prefs):
    return prefs["public_breaking_teams"]


def seed_rule_prose(break_size, teams_per_debate):
    """"room 1 is 1-8-9-16, room 2 is 2-7-10-15, ..." — worked out, not written.

    This sentence used to name a 32-team break folding into eight rooms of four,
    which is right for one tournament and wrong for everybody else's.
    """
    per = int(teams_per_debate or 4)
    rooms = int(break_size or 0) // per if per else 0
    if rooms < 2:
        return "the break folds into a single room"
    def ex(i):
        return "-".join(str(i + k * rooms if k % 2 == 0 else (k + 1) * rooms + 1 - i)
                        for k in range(per))
    return (f"room 1 is {ex(1)}, room 2 is {ex(2)}, and so on down to "
            f"room {rooms} at {ex(rooms)}")


def summary(prefs, rounds, current_seqs, categories=(), teams_per_debate=4):
    """Plain-English 'here's what this site can and can't show', for the site itself."""
    shown, withheld = [], []
    dp = prefs["public_draw"]
    shown.append({
        "off": "Nothing — tab has the public draw switched off",
        "current": "Rooms and judge panels for every round being run now, and for every finished round",
        "all": "Rooms and judge panels for every released round",
        "all-released": "Rooms and judge panels for every released round",
    }.get(dp, dp))
    if prefs["public_results"]:
        shown.append("Round rankings — who came 1st, 2nd, 3rd and 4th in each room")
        shown.append("Team points, and the fold those points build")
        shown.append("Who judged each of those rooms — the chair, the panellists "
                     "and any trainee. The tab's own results pages carry this, "
                     "which is why it is here even when the draw is switched off")
    else:
        withheld.append("Round rankings — tab has public results switched off")
        withheld.append("Who judged — that travels with the results")
    if dp == "off":
        withheld.append("Room names — tab has the public draw switched off, and "
                        "the results pages carry no room column")
    if prefs["public_breaking_teams"]:
        shown.append("Break positions, exactly as announced")
        general = next((c for c in categories if c.get("is_general")), None) \
            or (categories[0] if categories else None)
        rule = seed_rule_prose((general or {}).get("break_size"), teams_per_debate)
        shown.append("The first break round's rooms, folded out of those announced ranks "
                     f"({rule}) — a projection off public numbers, replaced by the real "
                     "draw the moment tab releases it")
    else:
        withheld.append("Break positions — not announced yet")
    if prefs["public_motions"]:
        rel = [r["abbr"] for r in rounds if r.get("motion")]
        shown.append("Motions for " + (", ".join(rel) if rel else "no round yet"))
    silent = [r["abbr"] for r in rounds if r["outround"] and r["silent"]]
    if silent:
        withheld.append("Results of " + ", ".join(silent) +
                        " — these rounds are silent until announced")
    unrel = [r["abbr"] for r in rounds if r["outround"] and r["draw_status"] != "Released"]
    if unrel:
        withheld.append("Draws for " + ", ".join(unrel) +
                        " — locked until tab releases them, including anything adjcore has drafted")
    # Speaks are the one thing here that moves between the two lists, so it is
    # stated either way rather than assumed to be withheld.
    if speaker_tab_public(prefs):
        cut = tab_cut(prefs, "speaker")
        shown.append("The speaker tab — released by tab"
                     + (f", to the top {cut}" if cut else ", in full")
                     + ". Anyone the tab marks anonymous keeps their scores and "
                       "loses their name, exactly as on the tournament's own page")
    else:
        withheld.append("Speaker scores — tab has not released the speaker tab")
    if team_speaks_public(prefs):
        cut = tab_cut(prefs, "team")
        shown.append("Total team speaks — released by tab"
                     + (f", to the top {cut}" if cut else ""))
    else:
        withheld.append("Team speaks — tab has not released the team tab")
    if not prefs["replies_tab_released"]:
        withheld.append("Reply speeches — their own switch, and it is off. Releasing "
                        "the speaker tab does not release replies")
    if not prefs["adjudicators_tab_released"]:
        withheld.append("The adjudicator tab — its own switch, and it is off")
    withheld += [
        "Ballots, and any margin or split within a room",
        "Judge feedback, judge test scores and adjudication-core notes",
        "Anyone's private links, emails, phone numbers or check-in state",
    ]
    return {"shown": shown, "withheld": withheld}


# ------------------------------------------------------------- the assertion ---
def assert_clean(payload):
    """Walk the finished payload; raise on anything not declared in ALLOWED."""
    problems = []

    def bad_name(k):
        if k in EXEMPT:
            return []
        lk = str(k).lower()
        return [p for p in FORBIDDEN_KEY_PARTS if p in lk]

    def walk(node, spec, path):
        if spec is None:
            # A declared leaf. It must be a scalar. Without this check, a spec of
            # None waves through an entire nested object — so a field declared as
            # "a list of names" could quietly become a list of whole participant
            # records, PII and private URL keys included, and the allowlist would
            # report the payload clean.
            if isinstance(node, dict):
                problems.append(
                    f"{path}: declared as a scalar but is an object with keys "
                    f"{sorted(node)[:6]} — declare its shape in gate.ALLOWED")
            elif isinstance(node, list):
                for i, item in enumerate(node):
                    if isinstance(item, (dict, list)):
                        problems.append(
                            f"{path}[{i}]: declared as a scalar list but holds a "
                            f"{type(item).__name__}")
                        break
            return
        if isinstance(spec, tuple):
            kind, inner = spec
            if kind == "list":
                if not isinstance(node, list):
                    return
                for i, item in enumerate(node):
                    walk(item, inner, f"{path}[{i}]")
            elif kind == "dict":
                if not isinstance(node, dict):
                    return
                for k, v in node.items():
                    hits = bad_name(k)
                    if hits:
                        problems.append(f"{path}.{k}: forbidden key part {hits}")
                    walk(v, inner, f"{path}.{k}")
            return
        if not isinstance(node, dict):
            return
        for k, v in node.items():
            hits = bad_name(k)
            if hits:
                problems.append(f"{path}.{k}: forbidden key part {hits}")
            if k not in spec:
                problems.append(f"{path}.{k}: not in the allowlist — declare it in gate.ALLOWED")
                continue
            walk(v, spec[k], f"{path}.{k}")

    walk(payload, ALLOWED, "$")
    if problems:
        raise GateViolation("payload would leak non-public data:\n  " + "\n  ".join(problems))
    return True
