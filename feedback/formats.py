"""
formats.py — what the summariser is allowed to say about the shape of a debate,
worked out from the tournament rather than assumed.

Two lines of the prompt depend on the format:

  · the craft vocabulary a summary MAY use. "The opening half", "an extension"
    and "the bench" are British Parliamentary words; in a two-team debate they
    are meaningless, and a summary that used them would read as though it had
    been written about somebody else's tournament.
  · the side labels a summary may NOT use, because a side label plus anything
    else narrows a comment down to one room.

Both come off the live config: `debate_rules__teams_in_debate` and
`debate_rules__side_names`. Nothing here is switched on the name of a
tournament or a format the toolkit was written for.
"""

# Tabbycat's own side-name presets, plus the words people use for them.
SIDE_WORDS = {
    "aff-neg": ["affirmative", "negative", "aff", "neg"],
    "gov-opp": ["government", "opposition", "gov", "opp"],
    "prop-opp": ["proposition", "opposition", "prop", "opp"],
    "pro-con": ["pro", "con"],
    "appellant-respondent": ["appellant", "respondent"],
}

# Side labels a summary may not use. NOTE what is deliberately absent: "opening
# half" and "closing half". Those are craft vocabulary — the prompt explicitly
# invites them, because you cannot describe how somebody judged a four-team
# debate without them, and unlike "opening government" they name a region of the
# debate rather than a particular team. Banning them makes the tool useless at
# exactly the thing it is for.
BP_SIDES = ["OG", "OO", "CG", "CO",
            "opening government", "opening opposition",
            "closing government", "closing opposition"]

PROFILES = {
    4: {
        "format_line": "a British Parliamentary debating tournament",
        "craft_vocab": (
            "the opening half, the closing half, an extension, the comparative, "
            "the bench, the whip, a knife, deliberation"),
        # In BP the halves ARE the sides, so the positional words are banned as
        # labels while "the opening half" stays legal as craft vocabulary — the
        # gate distinguishes them, this list is only what may not be used to
        # place a team.
        "extra_side_labels": ["OG", "OO", "CG", "CO"],
    },
    3: {
        "format_line": "a three-team-per-debate tournament",
        "craft_vocab": "the case line, the clash, the comparative, the reply, deliberation",
        "extra_side_labels": [],
    },
    2: {
        "format_line": "a two-team debating tournament",
        "craft_vocab": (
            "the case line, the clash, the comparative, points of information, "
            "the reply speech, deliberation"),
        "extra_side_labels": [],
    },
}


def profile(teams_in_debate=4, side_names=None):
    """The three prompt fragments for this tournament's format."""
    n = int(teams_in_debate or 4)
    p = dict(PROFILES.get(n) or PROFILES[2])
    if n not in PROFILES:
        p["format_line"] = f"a debating tournament with {n} teams in a debate"

    labels = list(p["extra_side_labels"])
    key = str(side_names or "").strip().lower()
    labels += SIDE_WORDS.get(key, [])
    if n == 4:
        labels += [w for w in BP_SIDES if w not in labels]
    if not labels:                       # unknown preset: cover the common words
        labels = ["government", "opposition", "proposition", "affirmative", "negative"]

    seen, ordered = set(), []
    for w in labels:
        if w.lower() not in seen:
            seen.add(w.lower())
            ordered.append(w)
    return {
        "format_line": p["format_line"],
        "craft_vocab": p["craft_vocab"],
        "side_labels": ", ".join(ordered),
        "teams_in_debate": n,
    }


if __name__ == "__main__":
    for n, sn in ((4, "gov-opp"), (2, "aff-neg"), (2, None), (3, "prop-opp"), (6, None)):
        p = profile(n, sn)
        print(f"{n} teams / {sn}:")
        print(f"   {p['format_line']}")
        print(f"   may say : {p['craft_vocab']}")
        print(f"   may not : {p['side_labels'][:88]}…")
