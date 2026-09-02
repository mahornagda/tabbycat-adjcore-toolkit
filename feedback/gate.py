#!/usr/bin/env python3
"""
gate.py — the single decision point for what a judge is allowed to read.

Everything the CAP asked for on 1 Sep is a check in here, and a check that fails
stops the build rather than logging a warning:

  no scores          Sabri: "No scores". So: no digits anywhere, no score/rank/
                     average vocabulary, and no counted-people phrasing
                     ("three people said") which is a score with the numerals
                     spelled out.
  round-blind        Sabri: "so that the feedback doesnt give away what round
                     this was bc some args are mentioned in submissions etc".
                     So: no round names, no stage names, and no word that only
                     a motion could have supplied.
  nothing from teams Mahor: "dont reveal any info from teams". So: no team name,
                     no institution, no institution code, no side label, and no
                     attribution of a comment to a team or a co-panellist.
  no quoting         A distinctive phrase identifies its author inside a panel of
                     three. So: no 7-word run shared with any source comment.

Used twice. summarise.py runs it on a fresh draft and hands the violations back
to the model to fix, which is why the wording of each message is aimed at a
writer. tests/test_gate.py runs it again over the whole set, and refresh refuses
to publish if that fails.
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import terms as T

# The only keys a published summary file may contain. A new field cannot leak by
# accident: anything undeclared is a failure, the same allowlist idea the public
# site's gate uses.
ALLOWED = {"name", "overview", "strengths", "growth", "themes", "thin", "generated"}
PROSE_KEYS = ("overview", "strengths", "growth", "themes")

# Speaker-position abbreviations. These are format-specific but harmless to check
# everywhere: no format uses them as ordinary words, so a two-team tournament
# loses nothing by also rejecting "DPM".
SIDES = re.compile(r"\b(OG|OO|CG|CO|PM|LO|DPM|DLO|MG|MO|GW|OW)\b")

# Side names spelled out. Built from the tab's own side-name setting via
# formats.profile(), because "opening government" means nothing at a two-team
# tournament and "affirmative" means nothing at a BP one.
def _side_words(vocab):
    labels = [l for l in (vocab.get("side_labels") or []) if len(l) > 2]
    if not labels:
        return re.compile(r"\b(opening|closing)\s+(government|opposition)\b", re.I)
    alts = "|".join(re.escape(l) for l in sorted(labels, key=len, reverse=True))
    return re.compile(r"\b(" + alts + r")\b", re.I)

# Stage-of-tournament words. The generic part is fixed (every format has finals
# and prelims); the tournament's own break-category names are added from the tab,
# so a category called anything at all is caught without being typed in here.
_STAGE_GENERIC = (r"round\s*(one|two|three|four|five|six|seven|eight|nine|ten|\d)|"
                  r"octo\w*|quarter[- ]?finals?|semi[- ]?finals?|grand\s*final|"
                  r"the\s+final\b|break\s*round|out[- ]?round|prelim\w*|elim\w*|"
                  r"silent\s*round")


def _stage_words(vocab):
    extra = [s for s in (vocab.get("stages") or []) if len(s) > 2]
    alts = _STAGE_GENERIC
    if extra:
        alts += "|" + "|".join(re.escape(s) for s in sorted(extra, key=len, reverse=True))
    return re.compile(r"\b(" + alts + r")\b", re.I)
SCORE_WORDS = re.compile(
    r"\b(score[ds]?|scoring|rating[s]?|rated|rank(ed|ing|s)?|average[ds]?|"
    r"out\s+of\s+(ten|five|\w*\d)|percentile|points?\s+(given|awarded)|"
    r"feedback\s+(score|average|number))\b", re.I)
# "one person" is how you honestly report a single view, and the prompt asks for
# it — so the ban starts at two, where a count starts behaving like a score.
COUNTED = re.compile(
    r"\b(two|three|four|five|six|seven|eight|nine|ten)\s+"
    r"(of\s+\w+\s+)?(people|person|judges?|adjudicators?|panell?ists?|teams?|"
    r"respondents?|comments?|pieces?|rounds?|debates?|of\s+them)\b", re.I)
ATTRIB = re.compile(
    r"\b(a|the|one|another)\s+(team|panell?ist|chair|trainee|co-?panell?ist|"
    r"adjudicator|judge|speaker)\s+(said|wrote|felt|thought|noted|mentioned|"
    r"commented|observed|described|reported)\b", re.I)
DIGITS = re.compile(r"\d")


def _text(rec):
    """Every string a reader will actually see, joined."""
    out = []
    for k in PROSE_KEYS:
        v = rec.get(k)
        if isinstance(v, str):
            out.append(v)
        elif isinstance(v, list):
            out.extend(str(x) for x in v)
    return "\n".join(out)


def _shingles(s, n=7):
    w = re.findall(r"[a-z']+", s.lower())
    return {" ".join(w[i:i + n]) for i in range(max(0, len(w) - n + 1))}


def check(rec, sources=(), vocab=None):
    """Return a list of human-readable violations. Empty list means publishable."""
    v = vocab or T.build()
    bad = []

    extra = set(rec) - ALLOWED
    if extra:
        bad.append(f"undeclared field(s) {sorted(extra)} — only {sorted(ALLOWED)} may be published")
    for k in ("name", "overview"):
        if not isinstance(rec.get(k), str) or not rec[k].strip():
            bad.append(f"'{k}' is missing or empty")
    for k in ("strengths", "growth", "themes"):
        if not isinstance(rec.get(k), list):
            bad.append(f"'{k}' must be a list")

    body = _text(rec)
    low = body.lower()

    if DIGITS.search(body):
        bad.append("contains a digit — the summary must carry no numbers at all "
                   "(no scores, no counts, no round numbers)")
    for pat, msg in (
        (SIDES, "names a side or speaker position (OG/OO/CG/CO/PM/LO...) — "
                "say 'a team' instead"),
        (_side_words(v), "names a specific side — describe the judging, not who "
                         "was on which bench"),
        (_stage_words(v), "names a round or stage of the tournament — the summary "
                          "must not reveal which debate anything came from"),
        (SCORE_WORDS, "uses score/rank/average vocabulary — there are no scores "
                      "in this summary"),
        (COUNTED, "counts the people who wrote in — say 'several', 'a number of', "
                  "'one person' instead"),
        (ATTRIB, "attributes a comment to a team or a panellist — write 'people "
                 "who wrote about you' and never say who said what"),
    ):
        m = pat.search(body)
        if m:
            bad.append(f"{msg} [found: {m.group(0)!r}]")

    own = {p.lower() for p in re.findall(r"[A-Za-z][A-Za-z'-]{3,}", rec.get("name", ""))}
    for p in v["people"]:
        if p.lower() in own:
            continue
        if re.search(r"\b" + re.escape(p) + r"\b", body, re.I):
            bad.append(f"names a person ({p!r}) — no participant may be named")
            break
    for label, items, flags in (
        ("a team", v["teams"], re.I),
        ("an institution", v["institutions"], re.I),
        ("an institution code", v["codes"], 0),
        ("a round", v["rounds_ci"], re.I),
        ("a round abbreviation", v["rounds"], 0),
        ("a country or city", v["countries"], re.I),
    ):
        # A case-sensitive upper-case abbreviation is safe to check at two
        # characters; a case-insensitive word is not, or a team called "Alpha"
        # bans the word "alpha" from every summary.
        floor = 2 if flags == 0 else 4
        for it in items:
            if len(it) < floor:
                continue
            if re.search(r"\b" + re.escape(it) + r"\b", body, flags):
                bad.append(f"names {label} ({it!r}) — nothing that places a specific debate")
                break

    for w in v["motion_terms"]:
        if re.search(r"\b" + re.escape(w) + r"\b", low):
            bad.append(f"uses a word that only a motion could have supplied ({w!r}) — "
                       "describe the judging, never the debate's content")
            break

    if sources:
        src = set()
        for s in sources:
            src |= _shingles(s)
        for sh in _shingles(body):
            if sh in src:
                bad.append(f"quotes a comment nearly verbatim ({sh!r}) — always "
                           "paraphrase, or the author is identifiable")
                break

    return bad


def main():
    vocab = T.build()
    bundles = os.path.join(HERE, "data", "bundles.json")
    srcs = {}
    if os.path.exists(bundles):
        srcs = {str(k): v["comments"] for k, v in json.load(open(bundles)).items()}

    d = os.path.join(HERE, "summaries")
    files = sorted(f for f in os.listdir(d) if f.endswith(".json"))
    if not files:
        print("no summaries to check", file=sys.stderr)
        return 1
    fails = 0
    for f in files:
        rec = json.load(open(os.path.join(d, f), encoding="utf-8"))
        aid = f[:-5]
        bad = check(rec, srcs.get(aid, ()), vocab)
        if bad:
            fails += 1
            print(f"\nFAIL {f}  ({rec.get('name','?')})")
            for b in bad:
                print("   ·", b)
    print(f"\n{len(files) - fails}/{len(files)} summaries pass the gate")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
