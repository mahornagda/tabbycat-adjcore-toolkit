#!/usr/bin/env python3
"""
bundle.py — turn the raw pull into one anonymised bundle per judge.

This is the mask half of the belt-and-braces in terms.py: names are replaced
*before* the model sees a comment, so the model cannot repeat what it never got.
gate.py is the braces, and it runs after.

What is removed here and never restored:
  · which round / debate a comment came from
  · who wrote it (team or co-panellist), and their name
  · the numeric feedback score and the yes/no "did you agree" answer
  · the timestamp, so the order carries no round information either

Writes data/bundles.json (gitignored — it is still every judge's raw feedback).
"""
import hashlib, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import terms as T

RAW = os.path.join(HERE, "data", "raw.json")
OUT = os.path.join(HERE, "data", "bundles.json")

# Enough written feedback to find a pattern in. Below this the summary says so
# plainly rather than inflating two lines into a paragraph.
THIN = 3


def masker(vocab):
    """Longest-first so 'Northgate Open University A' masks before 'Iqbal'."""
    by_len = lambda xs: sorted(xs, key=len, reverse=True)
    # Order matters: the longest string wins, so "Northgate Open University A"
    # is masked before "Iqbal", and a full name before either of its halves.
    pats = ([(re.compile(r"\b" + re.escape(x) + r"\b", re.I), "[a team]")
             for x in by_len(vocab["teams"] + vocab["institutions"])] +
            [(re.compile(r"\b" + re.escape(x) + r"\b"), "[a team]")
             for x in by_len(vocab["codes"])] +
            [(re.compile(r"\b" + re.escape(x) + r"\b", re.I), "[a person]")
             for x in by_len(vocab["full_names"] + vocab["people"])] +
            [(re.compile(r"\b" + re.escape(x) + r"\b", re.I), "[a round]")
             for x in by_len(vocab["rounds_ci"])] +
            # Upper-case only: "OF" is the grand final's abbreviation, and
            # matching it case-insensitively turns every "of" into "[a round]".
            [(re.compile(r"\b" + re.escape(x) + r"\b"), "[a round]")
             for x in by_len(vocab["rounds"])] +
            [(re.compile(r"\b(OG|OO|CG|CO)\b"), "[a team]")])

    def run(s):
        for p, r in pats:
            s = p.sub(r, s)
        return s
    return run


def main():
    raw = json.load(open(RAW, encoding="utf-8"))
    mask = masker(T.build())

    byadj = {}
    for w in raw["written"]:
        byadj.setdefault(w["adj"], []).append(w)

    out = {}
    for a in raw["adjudicators"]:
        items = byadj.get(a["id"], [])
        # Order by a hash of the comment id, not by time. Chronological order is
        # itself round information: the first comment in the list would be R1.
        items.sort(key=lambda w: hashlib.sha256(str(w["fid"]).encode()).hexdigest())
        seen, comments = set(), []
        for w in items:
            c = re.sub(r"\s+\n", "\n", mask(w["text"])).strip()
            if c.lower() in seen:
                continue
            seen.add(c.lower())
            comments.append(c)
        out[str(a["id"])] = {
            "name": a["name"],
            "key": a["url_key"],
            "comments": comments,
            "thin": len(comments) < THIN,
        }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    os.chmod(OUT, 0o600)

    n = sum(len(v["comments"]) for v in out.values())
    thin = [v["name"] for v in out.values() if v["thin"]]
    print(f"wrote {OUT}  ({len(out)} judges, {n} comments after masking)")
    print(f"  {len(thin)} judges below the {THIN}-comment line: {', '.join(thin) or 'none'}")
    if "--show" in sys.argv:
        k = sys.argv[sys.argv.index("--show") + 1]
        hit = next(v for v in out.values() if k.lower() in v["name"].lower())
        print(f"\n--- {hit['name']} ({len(hit['comments'])} comments)")
        for c in hit["comments"]:
            print("  ·", c.replace("\n", " ")[:300])


if __name__ == "__main__":
    main()
