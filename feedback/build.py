#!/usr/bin/env python3
"""
build.py — emit dist/ : one static page plus one JSON file per judge.

The file name is sha256(url_key). That is the whole access model, and it is
deliberately the *only* one:

  · the published site never contains a url_key, so a copy of dist/ is not a
    set of credentials the way data/ is;
  · there is no index, no listing and no search endpoint, so holding the site
    tells you nothing about who is in it;
  · a judge's page is reachable only by someone who already has their private
    URL — which is exactly the property Tabbycat already relies on.

Names live inside the file, not in its path, so a directory of hashes leaks
nothing even if a host were to list it.
"""
import datetime, hashlib, json, os, re, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "core"))
import config
SRC = os.path.join(HERE, "src")
DIST = os.path.join(HERE, "dist")
BUNDLES = os.path.join(HERE, "data", "bundles.json")
RAW = os.path.join(HERE, "data", "raw.json")
SUMS = os.path.join(HERE, "summaries")

# Published to a judge. Anything else that happens to be in a summary file --
# the model name, the thin flag's provenance, a reviewer's note -- stays local.
PUBLISH = ("name", "overview", "strengths", "growth", "themes", "thin")

HEADERS = """/*
  X-Frame-Options: DENY
  X-Content-Type-Options: nosniff
  Referrer-Policy: no-referrer
  X-Robots-Tag: noindex, nofollow
  Content-Security-Policy: default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; img-src data:; connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'

/f/*
  Cache-Control: no-store
  Content-Type: application/json; charset=utf-8
  X-Robots-Tag: noindex, nofollow
"""


def main():
    bundles = json.load(open(BUNDLES, encoding="utf-8"))
    if os.path.exists(DIST):
        shutil.rmtree(DIST)
    os.makedirs(os.path.join(DIST, "f"))

    written, missing, keyless = 0, [], []
    for aid, rec in bundles.items():
        path = os.path.join(SUMS, f"{aid}.json")
        if not os.path.exists(path):
            if rec["comments"]:
                missing.append(rec["name"])
            continue
        if not rec.get("key"):
            keyless.append(rec["name"])
            continue
        s = json.load(open(path, encoding="utf-8"))
        out = {k: s[k] for k in PUBLISH if k in s}
        h = hashlib.sha256(rec["key"].encode()).hexdigest()
        with open(os.path.join(DIST, "f", f"{h}.json"), "w", encoding="utf-8") as fh:
            json.dump(out, fh, ensure_ascii=False, separators=(",", ":"))
        written += 1

    built = datetime.date.today().strftime("%-d %b %Y")

    # The tournament names itself. It comes from the tab on the pull, so nothing
    # anywhere in this repo says the name of a tournament that is not yours —
    # and there is nothing for a user to type in and get wrong.
    tour = ""
    if os.path.exists(RAW):
        tour = (json.load(open(RAW, encoding="utf-8")).get("tournament") or "")
    tour = config.name() or tour

    # The placeholder in the paste box shows the shape of a private URL on THIS
    # tab, which is the thing a judge is being asked to find.
    try:
        tab_url, tab_slug = config.tab()
        example = f"{tab_url}/{tab_slug}/privateurls/…"
    except Exception:
        example = "https://your-tab/your-tournament/privateurls/…"

    html = open(os.path.join(SRC, "index.html"), encoding="utf-8").read()
    css = open(os.path.join(SRC, "style.css"), encoding="utf-8").read()
    app = open(os.path.join(SRC, "app.js"), encoding="utf-8").read()
    html = html.replace("/*__STYLE__*/", css)
    html = html.replace("/*__DATA__*/",
                        f"const BUILT = {json.dumps(built)};\n"
                        f"const TOURNAMENT = {json.dumps(tour)};")
    html = html.replace("/*__APP__*/", app)
    html = html.replace("{{TOURNAMENT}}", tour)
    html = html.replace("{{PRIVATE_URL_EXAMPLE}}", example)
    open(os.path.join(DIST, "index.html"), "w", encoding="utf-8").write(html)
    open(os.path.join(DIST, "_headers"), "w", encoding="utf-8").write(HEADERS)

    # A judge who opens a stray path should get the front door, not a 404 that
    # looks like their feedback was lost.
    shutil.copyfile(os.path.join(DIST, "index.html"), os.path.join(DIST, "404.html"))

    kb = os.path.getsize(os.path.join(DIST, "index.html")) // 1024
    print(f"built dist/ — {written} judge pages, index {kb} KB")
    if missing:
        print(f"  {len(missing)} judges have comments but no summary yet "
              f"(run ./summarise.py): {', '.join(missing[:6])}"
              f"{' …' if len(missing) > 6 else ''}")
    if keyless:
        print(f"  {len(keyless)} judges have no private URL in the tab and cannot "
              f"be reached: {', '.join(keyless)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
