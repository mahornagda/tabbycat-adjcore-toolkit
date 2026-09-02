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
and no spectator page carries them: speaker scores, team speaks, margins, ballots,
feedback of any kind, judge base scores, judge test/adjcore status, conflicts,
private URL keys, emails, barcodes, check-in state, room importance, and any
allocation this team has drafted but the tab has not released.
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
    # These two are the tab's own switch names, carried onto the page so a reader can
    # see for themselves that the tab is not released. They are booleans about
    # visibility, not the data they gate.
    "speaker_tab_released": "a visibility switch, reported so readers can check it",
    "ballots_released": "a visibility switch, reported so readers can check it",
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
        "current_round": None,
        "withheld": ("list", None),
        "shown": ("list", None),
    },
    "rounds": ("list", {
        "seq": None, "abbr": None, "name": None, "outround": None,
        "cat": None, "cat_name": None, "completed": None, "silent": None,
        "draw_status": None, "results_public": None, "draw_public": None,
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
    }


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


def motion_public(r, prefs, motions_released):
    return bool(prefs["public_motions"] and motions_released)


def break_public(prefs):
    return prefs["public_breaking_teams"]


def summary(prefs, rounds, current_seqs):
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
    else:
        withheld.append("Round rankings — tab has public results switched off")
    if prefs["public_breaking_teams"]:
        shown.append("Break positions, exactly as announced")
        shown.append("The first break round's rooms, folded out of those announced ranks "
                     "(room 1 is 1-16-17-32, room 2 is 2-15-18-31, and so on) — a projection "
                     "off public numbers, replaced by the real draw the moment tab releases it")
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
    withheld += [
        "Speaker scores and team speaks — the tab is not released",
        "Ballots, and any margin or split within a room",
        "Judge feedback, judge test scores and adjudication-core notes",
        "Anyone's private links, emails or check-in state",
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
