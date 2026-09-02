#!/usr/bin/env python3
"""
terms.py — the vocabulary that must never reach a published summary, built from
the tab itself rather than typed out by hand.

Two consumers, and the split matters:

  MASK  (bundle.py)  names replaced with a placeholder *before* the model sees
                     the comments, so the model cannot repeat what it never got.
  BAN   (gate.py)    checked *after* generation, so a leak that the mask missed
                     still stops the build.

Belt and braces on purpose: the mask is the cheap fix and the ban is the proof.
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "core"))
sys.path.insert(0, HERE)
import countries, formats, common_english
RAW = os.path.join(HERE, "data", "raw.json")

# A motion is the single most identifying thing in a round, so any distinctive
# word a motion supplied is banned from summaries. "Distinctive" is the whole
# trick: this list holds the words that EVERY motion is made of, and whatever is
# left over after removing them is the part that would name the round.
#
# Nothing tournament-specific belongs in here. If your motions keep tripping the
# gate on an ordinary word, add that word here — not the topic it came from.
STOP = set("""a an the this that these those there here it its their they them he she
his her him we us you your our my i me and or but nor so yet for as of in on to
with without by from at into onto over under above below between through against
among along around about across behind beyond during before after while when
where which who whom whose what why how if then than because unless until since
though although however therefore thus hence is are was were be been being am
do does did done have has had having can could may might must shall should will
would ought not no nor none any all both each every few many more most much less
least other another same such own very too also only just even still yet again
house houses opposes believes prefers regrets would-prefer motion motions this-house
government governments opposition proposition state states national international
policy policies policymakers regulation regulations regulate deregulate law laws
legal illegal legalise legalize ban bans banned mandate mandates mandatory
subsidy subsidies subsidise subsidize fund funds funded funding tax taxes taxation
public private sector market markets economy economies economic industry industries
industrial commercial corporate corporation corporations company companies business
businesses institution institutions organisation organisations organization
citizen citizens people person persons community communities society societies
social cultural culture political politics democracy democratic election elections
elect elected vote votes voting voter voters party parties coalition coalitions
representative representation parliament parliamentary congress president
presidential prime minister ministers ministry government-funded court courts
judicial judiciary constitution constitutional right rights freedom freedoms
liberty liberties justice injustice equality inequality equity discrimination
education educational school schools schooling university universities student
students teach teaching teacher teachers curriculum health healthcare hospital
hospitals medical medicine patient patients doctor doctors welfare benefit
benefits poverty poor wealth wealthy rich income wage wages labour labor worker
workers employer employers employment unemployment union unions strike strikes
technology technological digital internet online platform platforms data privacy
media journalism press news information misinformation environment environmental
climate energy renewable emission emissions pollution conservation sustainable
development developing developed growth growing decline declining reform reforms
policy-makers intervention interventions aid assistance humanitarian military
war wars peace conflict conflicts security defence defense police policing prison
prisons crime criminal punishment rehabilitation immigration immigrant immigrants
migration migrant migrants refugee refugees border borders citizenship
religion religious secular faith church tradition traditional modern modernity
family families parent parents child children youth young old elderly gender
woman women man men feminist feminism movement movements activist activists
activism protest protests campaign campaigns organisation-led framework
frameworks mechanism mechanisms narrative narratives comparative comparatively
principle principles practical practically intentionally left blank info slide
world global local regional urban rural city cities country countries
increase increases increasing decrease decreases reduce reduces reducing
require requires requiring allow allows allowing prevent prevents preventing
support supports supporting oppose opposing abolish abolishing abandon
abandoning pursue pursuing adopt adopting implement implementing prioritise
prioritize prioritised prioritized prioritising favour favor relax relaxation
inclusion inclusive exclusion exclusive strong strongly weak weakly better
worse best worst good bad important significant necessary sufficient""".split())


# macOS and most Linuxes ship /usr/share/dict/words. A surname that is also an
# ordinary English word ("Long", "Sharp", "Young", "Chan" in some lists) must NOT
# be masked or banned on its own, or the mask eats "long-winded" and the gate
# fails a summary for the word "sharp". Full names and adjacent pairs are always
# masked and always banned; it is only the lone token that needs this escape.
_DICT = None


def common_words():
    global _DICT
    if _DICT is None:
        try:
            with open("/usr/share/dict/words", encoding="utf-8", errors="ignore") as fh:
                _DICT = {w.strip().lower() for w in fh if w.strip().islower()}
        except OSError:
            _DICT = set()
        _DICT |= STOP
    return _DICT


def _load():
    with open(RAW, encoding="utf-8") as fh:
        return json.load(fh)


def _clean(s):
    """Drop Tabbycat's emoji suffixes and squeeze whitespace."""
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s&.'/()-]", " ", s or "")).strip()


def _motion_terms(motions):
    """The words in the motions that would identify the round if repeated.

    The test is whether the word is DISTINCTIVE, not merely whether it appeared
    in a motion. Every motion is built almost entirely from ordinary English, so
    banning every motion word bans "work", "land", "large" and "individual" —
    and a summary about judging cannot be written without those. Filtering by
    how common the word is in the language is a property of English rather than
    of any tournament, which is the only version of this that travels.
    """
    out = set()
    for m in motions:
        for w in re.findall(r"[A-Za-z][A-Za-z'-]{3,}", m or ""):
            lw = w.lower().strip("'-")
            if len(lw) < 4 or lw in STOP:
                continue
            if common_english.is_ordinary(lw):
                continue
            out.add(lw)
    return out


def build():
    d = _load()

    words = common_words()
    people, full_names = set(), set()
    for a in d["adjudicators"]:
        parts = re.findall(r"[A-Za-z][A-Za-z'-]{3,}", _clean(a["name"]))
        for part in parts:
            if part.lower() not in words:
                people.add(part)
        if _clean(a["name"]):
            full_names.add(_clean(a["name"]))
        # Adjacent pairs are what catch a two-part name whose halves are each
        # unusable on their own: one half too short to match safely ("Wu", "Tay"),
        # or an ordinary English word that must stay legal by itself. Someone
        # surnamed Long is why "long-winded" must not become "[a person] winded".
        for i in range(len(parts) - 1):
            full_names.add(f"{parts[i]} {parts[i + 1]}")

    # Team names are only useful as ban terms when they are long enough to be
    # unambiguous. Tabbycat's `reference` for a team is often a single letter
    # ("A", "D", "GK"), and banning those would fail every summary on the word
    # "a". Long names and institution-prefixed short names carry the signal.
    def keep(n):
        """Drop a name that is one ordinary English word — a team called 'Alpha'
        must not ban the word 'alpha' from every summary."""
        n = _clean(n)
        return len(n) >= 4 and not (" " not in n and n.lower() in words)

    teams = {_clean(n) for n in d["team_names"] if keep(n)}
    institutions = {_clean(i) for i in d["institutions"] if keep(i)}

    # Institution codes are short and upper-case, sometimes with a space
    # ("NGU", "RVB C", "UPD"). Match them case-sensitively as whole words, or a
    # two-letter code like "UI" fires inside "building" and breaks every summary.
    codes = set()
    for n in d["team_names"]:
        m = re.match(r"^([A-Z][A-Z0-9]{2,})\b", _clean(n))
        if m:
            codes.add(m.group(1))

    # Round abbreviations are short and upper-case ("OF" is the grand final), so
    # they must match case-sensitively — matching "OF" case-insensitively turns
    # every "of" in a comment into "[a round]".
    rounds, rounds_ci = set(), set()
    for r in d["round_names"]:
        r = _clean(r)
        if not r:
            continue
        (rounds if r.isupper() and len(r) <= 6 else rounds_ci).add(r)

    # The format decides which words are craft vocabulary and which are side
    # labels, and the break categories are extra round names. Both come off the
    # tab, so a tournament with different categories or a different format gets
    # a ban list that fits it.
    fmt = formats.profile((d.get("format") or {}).get("teams_in_debate", 4),
                          (d.get("format") or {}).get("side_names"))
    # Break-category names are stage names ("the EFL semis" places a debate as
    # surely as "round five"). But a category called "Open" — and a great many
    # are — must not ban the word "open", or no summary can say "open to
    # persuasion" or "the opening". Same escape hatch as a judge surnamed Long:
    # a single token that is ordinary English is skipped; anything multi-word or
    # distinctive ("EFL", "Novice Cup", "ESL") is still caught.
    stages = set()
    for c in d.get("categories", []):
        name = _clean(c)
        if not name or len(name) < 3:
            continue
        # The test is the CURATED common-word list, not /usr/share/dict/words.
        # The system dictionary contains "novice", so using it would let a
        # category called Novice go unbanned — and "the novice semis" does place
        # a debate. The curated list holds only genuinely everyday words, so
        # "Open" and "Main" stay legal while "Novice", "ESL" and "EFL" do not.
        if " " not in name and common_english.is_ordinary(name):
            continue
        stages.add(name)

    return {
        "side_labels": sorted({w.strip() for w in fmt["side_labels"].split(",") if w.strip()}),
        "stages": sorted(stages),
        "format": fmt,
        "people": sorted(p for p in people if p),
        "full_names": sorted(full_names),
        "rounds_ci": sorted(rounds_ci),
        "teams": sorted(teams),
        "institutions": sorted(institutions),
        "codes": sorted(codes),
        "rounds": sorted(rounds),
        "motion_terms": sorted(_motion_terms(d["motions"])),
        "countries": sorted(COUNTRIES),
    }


# Naming a place is either quoting a motion or telling the reader which
# tournament this was, and both are out. The list is every country, demonym,
# capital and major city in the world — from core/countries.py, the same source
# the Fold's flags come from — so it does not quietly assume the toolkit is
# still running in the region it was written in.
COUNTRIES = countries.place_words()


if __name__ == "__main__":
    import sys
    t = build()
    for k, v in t.items():
        print(f"{k:14s} {len(v):4d}  {', '.join(v[:8])}")
    if "--all" in sys.argv:
        print(json.dumps(t, indent=1))
