#!/usr/bin/env python3
"""
test_gate.py — the deploy gate. refresh refuses to publish if this fails.

Two halves. The first re-runs gate.check() over every summary that is about to
be published, because a summary can be hand-edited after generation and a
reviewer's improvement is exactly as capable of leaking a team name as the
model's first draft. The second checks properties of the built site itself.
"""
import hashlib, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import gate, terms as T

DIST = os.path.join(ROOT, "dist")
fails = []


def check(name, ok, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'} {name}{'' if ok else '  — ' + detail}")
    if not ok:
        fails.append(name)


def main():
    vocab = T.build()
    bundles = json.load(open(os.path.join(ROOT, "data", "bundles.json"), encoding="utf-8"))

    print("summaries")
    sdir = os.path.join(ROOT, "summaries")
    files = sorted(f for f in os.listdir(sdir) if f.endswith(".json"))
    check("there is something to publish", bool(files), "summaries/ is empty")
    bad_total = 0
    for f in files:
        rec = json.load(open(os.path.join(sdir, f), encoding="utf-8"))
        src = bundles.get(f[:-5], {}).get("comments", ())
        bad = gate.check(rec, src, vocab)
        if bad:
            bad_total += 1
            print(f"  FAIL {f} ({rec.get('name','?')})")
            for b in bad:
                print("        ·", b)
    check(f"all {len(files)} summaries pass every content rule", bad_total == 0,
          f"{bad_total} failed")

    print("\npublished files")
    fdir = os.path.join(DIST, "f")
    check("dist/f exists", os.path.isdir(fdir), "run ./build.py first")
    if not os.path.isdir(fdir):
        return 1
    pub = sorted(os.listdir(fdir))
    check("every published file is named by a sha-256 digest",
          all(re.fullmatch(r"[0-9a-f]{64}\.json", p) for p in pub),
          "a file is named something guessable")

    keys = {rec["key"] for rec in bundles.values() if rec.get("key")}
    hashes = {hashlib.sha256(k.encode()).hexdigest() for k in keys}
    check("no published file is unaccounted for",
          all(p[:-5] in hashes for p in pub), "a stray file is in dist/f")

    # The one that matters most: a url_key is a credential, so it must appear
    # nowhere in anything that gets uploaded.
    blob = ""
    for root, _, names in os.walk(DIST):
        for n in names:
            with open(os.path.join(root, n), encoding="utf-8", errors="ignore") as fh:
                blob += fh.read()
    leaked = [k for k in keys if k and re.search(r"\b" + re.escape(k) + r"\b", blob)]
    check("no private URL key appears anywhere in dist", not leaked,
          f"{len(leaked)} keys are in the build")

    print("\npublished payloads")
    allowed = set(("name", "overview", "strengths", "growth", "themes", "thin"))
    extra, digits = [], []
    for p in pub:
        d = json.load(open(os.path.join(fdir, p), encoding="utf-8"))
        if set(d) - allowed:
            extra.append(p)
        if re.search(r"\d", gate._text(d)):
            digits.append(p)
    check("published payloads carry no undeclared field", not extra, str(extra[:3]))
    check("published payloads contain no digit anywhere", not digits, str(digits[:3]))

    print("\nthe page")
    html = open(os.path.join(DIST, "index.html"), encoding="utf-8").read()
    check("the page is one file — no external script or stylesheet but fonts",
          not re.search(r'<script[^>]+src=', html) and
          html.count("<link rel=\"stylesheet\"") == 1)
    check("no judge's name is in the page itself",
          not any(re.search(r"\b" + re.escape(n) + r"\b", html)
                  for n in vocab["full_names"]),
          "a name is baked into the HTML")
    check("the page can only talk to its own origin",
          "connect-src 'self'" in html and "fetch(`f/" in html)
    check("the page is not indexable", 'name="robots"' in html and "noindex" in html)
    check("_headers ships with the build", os.path.exists(os.path.join(DIST, "_headers")))

    print()
    if fails:
        print(f"{len(fails)} GATE CHECK(S) FAILED — do not publish")
        return 1
    print("all gate checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
