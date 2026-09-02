#!/usr/bin/env python3
"""
make_samples.py — build the public sample sites from the fake tournament.

    python3 demo/make_samples.py                    all three, default shape
    python3 demo/make_samples.py --only fold
    python3 demo/make_samples.py --shape two-team
    python3 demo/make_samples.py --skip-summaries   reuse feedback summaries

Output lands in demo/samples/, one directory per tool plus a landing page,
ready to publish as a static site.

The samples are built by running the real tools against demo/mocktab.py. No
sample is hand-written, and no sample contains anything from a real tournament,
because the real tournament is never part of the process.

TWO OF THE THREE ARE ALREADY STATIC. The Fold and the feedback site publish a
directory of files, so their sample IS their output. Tester tracking is a local
app with a small API behind it, so its sample gets a shim that answers those
calls from data baked into the page, and the buttons that would write say so
instead of failing. The dashboard's own HTML is not modified — if it were, the
sample and the real thing could drift, and the sample would stop being evidence.
"""
import argparse, json, os, re, shutil, socket, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "samples")
sys.path.insert(0, HERE)
import mocktab

SAMPLE_BANNER_CSS = """
.samplebar{position:sticky;top:0;z-index:99;display:flex;gap:10px;align-items:center;
  flex-wrap:wrap;padding:9px 16px;background:#3d3527;color:#f6f1e7;
  font:13px/1.45 'Inter Tight',system-ui,sans-serif}
.samplebar b{font-weight:600}
.samplebar a{color:#f6f1e7;text-decoration:underline;text-underline-offset:2px}
.samplebar .dot{opacity:.5}
@media (prefers-color-scheme: dark){.samplebar{background:#2b251b}}
"""


def banner(tool, tour, docs_url, live=False):
    """The banner has to tell the truth about which kind of sample this is.

    Two of the three run on an invented tournament. The fold's runs on a real
    one, because the fold publishes nothing that is not already public on the
    tab it reads — so the honest demo is the real thing, and saying "invented"
    over real names would be a lie in the one place it matters most.
    """
    if live:
        what = ("<b>A real tournament.</b> Everything here was already public on "
                "its own Tabbycat — this page adds nothing to it.")
    else:
        what = ("<b>Sample.</b> Invented tournament, invented people. Nothing "
                "here is real data.")
    return f"""<div class="samplebar">
  <span>{what}</span>
  <span class="dot">·</span>
  <span>{tour}</span>
  <span class="dot">·</span>
  <a href="{docs_url}">How {tool} works, and how to run it &rarr;</a>
</div>"""


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close()
    return p


def run(cmd, cwd, env, label, timeout=1800):
    print(f"    {label} …", end="", flush=True)
    r = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        print(" FAILED")
        tail = "\n".join((r.stdout + r.stderr).splitlines()[-25:])
        raise SystemExit(f"\n{label} failed:\n{tail}")
    print(" ok")
    return r.stdout


# ------------------------------------------------------------ tester tracking --
SHIM = """<script>
/* ---------------------------------------------------------------------------
   Sample shim. The dashboard is a local app that reads a small API; this page
   has no server, so the API is answered from data baked in below.

   The dashboard's own code is untouched. Everything here sits either side of
   it, which is what keeps the sample honest evidence of the real thing rather
   than a lookalike built for a screenshot.
   ------------------------------------------------------------------------- */
window.__SAMPLE__ = true;
const __DATA__ = %(data)s;
const __realFetch = window.fetch.bind(window);
window.fetch = async (url, opts) => {
  const u = String(url);
  const json = (body, status) => new Response(JSON.stringify(body),
    { status: status || 200, headers: { "Content-Type": "application/json" } });
  if (u.includes("/api/status") || u.includes("/functions/status"))
    return json({ ok: true, running: false, log: [], error: null,
                  pulled_at: __DATA__.pulled_at });
  if (u.includes("/api/data") || u.includes("/functions/data"))
    return json(__DATA__);
  if (u.includes("/state") || u.includes("/refresh") || u.includes("/login"))
    return json({ ok: true, sample: true });
  return __realFetch(url, opts);
};
</script>
"""

OVERRIDES = """<script>
/* The two actions that write. In the real dashboard, Refresh re-reads your tab
   and everything else is stored beside it; here there is nothing to write to,
   so they say so rather than appearing to work and silently reverting. */
(function () {
  const note = m => (window.toast ? toast(m, 5200) : alert(m));
  const readOnly = "This is a sample, so nothing saves. Running it on your own "
    + "tournament, this re-reads your tab and keeps your changes beside it.";
  if (typeof saveState === "function") { saveState = async () => note(readOnly); }
  if (typeof saveNotes === "function") { saveNotes = async () => note(readOnly); }
  const btn = document.querySelector("#btnRefresh");
  if (btn) btn.onclick = () => note("This is a sample of a tournament that does not "
    + "exist, so there is no tab to re-read. On your own tournament this button "
    + "pulls the current draw, panels and feedback.");
})();
</script>
"""


def build_tester_tracking(env, tour, docs_url):
    src = os.path.join(ROOT, "tester-tracking")
    run([sys.executable, "pull.py"], src, env, "reading the fake tab")
    with open(os.path.join(src, "data.json"), encoding="utf-8") as fh:
        data = json.load(fh)
    # The local state file is the tester list and the notes. Ship whatever the
    # pull produced, so the sample shows the tab-derived default: adjudication
    # core are testers unless somebody says otherwise.
    html = open(os.path.join(src, "index.html"), encoding="utf-8").read()
    shim = SHIM % {"data": json.dumps(data, ensure_ascii=False, separators=(",", ":"))}
    html = html.replace("<script>\n/* ============================ plumbing",
                        shim + "<script>\n/* ============================ plumbing", 1)
    html = html.replace("</style>", SAMPLE_BANNER_CSS + "</style>", 1)
    html = html.replace("</script>\n</body>", "</script>\n" + OVERRIDES + "</body>", 1)
    # the banner goes just inside <body>, above the dashboard's own header
    html = html.replace("<body>", "<body>\n" + banner("tester tracking", tour, docs_url), 1)
    dest = os.path.join(OUT, "tester-tracking")
    os.makedirs(dest, exist_ok=True)
    with open(os.path.join(dest, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(html)
    kb = os.path.getsize(os.path.join(dest, "index.html")) // 1024
    print(f"    wrote samples/tester-tracking/index.html ({kb} KB, "
          f"{len(data['judges'])} judges baked in)")
    return {"judges": len(data["judges"]),
            "testers": data["counts"]["testers"],
            "tested": sum(1 for j in data["judges"] if j["test_count"])}


# ------------------------------------------------------------------- the fold --
def build_fold(env, tour, docs_url, live=False):
    src = os.path.join(ROOT, "fold")
    run([sys.executable, "build.py"], src, env, "building the fold")
    run([sys.executable, "tests/test_gate.py"], src, env, "gate checks")
    dest = os.path.join(OUT, "fold")
    os.makedirs(dest, exist_ok=True)
    html = open(os.path.join(src, "dist", "index.html"), encoding="utf-8").read()
    html = html.replace("</style>", SAMPLE_BANNER_CSS + "</style>", 1)
    html = html.replace("<body>", "<body>\n"
                        + banner("the fold simulator", tour, docs_url, live), 1)
    with open(os.path.join(dest, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(html)
    for extra in ("_headers",):
        p = os.path.join(src, "dist", extra)
        if os.path.exists(p):
            shutil.copyfile(p, os.path.join(dest, extra))
    kb = os.path.getsize(os.path.join(dest, "index.html")) // 1024
    print(f"    wrote samples/fold/index.html ({kb} KB)")
    return {"kb": kb}


# --------------------------------------------------------------- the feedback --
TRY_KEYS_CSS = """
.trykeys{margin:26px auto 0;max-width:44rem;padding:16px 18px;border-radius:11px;
  border:1px solid var(--rule,#E4DACA);background:var(--card-2,#FAF5EC)}
.trykeys h3{margin:0 0 4px;font-size:1rem}
.trykeys p{margin:0 0 12px;font-size:.92rem;opacity:.8}
.trykeys ul{list-style:none;margin:0;padding:0;display:grid;gap:8px}
.trykeys li{display:flex;gap:10px;align-items:baseline;flex-wrap:wrap;font-size:.93rem}
.trykeys a{font-family:var(--mono,monospace);font-size:.9rem}
.trykeys span{opacity:.72}
"""


def try_keys_panel(rows):
    """The real site hands a judge their own private URL and nothing else — no
    index, no search, no way to reach anybody else's page. That is the access
    model, so a public sample has to hand out a few keys or there is nothing to
    look at. These three are chosen to show the range: a judge with plenty
    written about them, an average one, and one where almost nothing came in."""
    items = "".join(
        f'<li><a href="#{k}">{k}</a> <span>{why}</span></li>' for k, why in rows)
    return f"""<div class="trykeys">
  <h3>Try it</h3>
  <p>A judge is given a link to their own page and nothing else — there is no
     index, no search, and no way to reach anyone else's. So for this sample,
     here are three keys. They show the range deliberately.</p>
  <ul>{items}</ul>
</div>"""


def build_feedback(env, tour, docs_url, skip_summaries=False, jobs=4):
    src = os.path.join(ROOT, "feedback")
    run([sys.executable, "pull.py", "--stats"], src, env, "reading the fake tab")
    run([sys.executable, "bundle.py"], src, env, "masking names out of the comments")
    if not skip_summaries:
        print("    writing summaries with the claude CLI (this is the slow part)")
        run([sys.executable, "summarise.py", "-j", str(jobs)], src, env,
            "summarising", timeout=5400)
    # Build first, then check: the gate inspects what is actually about to be
    # published, not just the drafts. Same order as feedback/refresh.
    run([sys.executable, "build.py"], src, env, "building the site")
    run([sys.executable, "tests/test_gate.py"], src, env,
        "gate checks over the built site")
    dest = os.path.join(OUT, "feedback")
    if os.path.exists(dest):
        shutil.rmtree(dest)
    shutil.copytree(os.path.join(src, "dist"), dest)
    for page in ("index.html", "404.html"):
        p = os.path.join(dest, page)
        if not os.path.exists(p):
            continue
        html = open(p, encoding="utf-8").read()
        # The build puts the real tab's address in the paste box as an example.
        # For the sample that address is the local fake server, which reads as
        # broken, so it is swapped for the generic shape.
        html = re.sub(r'placeholder="http://127\.0\.0\.1:\d+/[^"]*"',
                      'placeholder="https://your-tab/your-tournament/privateurls/…"',
                      html)
        html = html.replace("</style>", SAMPLE_BANNER_CSS + "</style>", 1)
        html = html.replace("<body>", "<body>\n"
                            + banner("the feedback tool", tour, docs_url), 1)
        open(p, "w", encoding="utf-8").write(html)
    # Pick three keys off what was actually published, so the panel can never
    # advertise a page that is not there.
    import hashlib
    raw = json.load(open(os.path.join(src, "data", "raw.json"), encoding="utf-8"))
    bundles = json.load(open(os.path.join(src, "data", "bundles.json"), encoding="utf-8"))
    counts = {aid: len(r["comments"]) for aid, r in bundles.items()}
    live = []
    for a in raw["adjudicators"]:
        key = a.get("url_key")
        if not key:
            continue
        h = hashlib.sha256(key.encode()).hexdigest()
        if os.path.exists(os.path.join(dest, "f", f"{h}.json")):
            live.append((counts.get(str(a["id"]), 0), key))
    live.sort(reverse=True)
    rows = []
    if live:
        rows.append((live[0][1], f"plenty was written about this judge"))
        rows.append((live[len(live) // 2][1], "an average amount came in"))
        thin = [k for c, k in live if c < 3]
        if thin:
            rows.append((thin[-1], "almost nothing was written — the short version"))
    if rows:
        idx = os.path.join(dest, "index.html")
        h = open(idx, encoding="utf-8").read()
        h = h.replace("</style>", TRY_KEYS_CSS + "</style>", 1)
        # after the paste-your-URL form, which is where a visitor is looking
        h = h.replace("</main>", try_keys_panel(rows) + "\n</main>", 1)
        if "trykeys" not in h:                       # no <main> in this template
            h = h.replace("</body>", try_keys_panel(rows) + "\n</body>", 1)
        open(idx, "w", encoding="utf-8").write(h)
        print(f"    sample keys offered: {', '.join(k for k, _ in rows)}")

    pages = len([f for f in os.listdir(os.path.join(dest, "f"))]) if \
        os.path.exists(os.path.join(dest, "f")) else 0
    print(f"    wrote samples/feedback/ ({pages} judge pages)")
    return {"pages": pages}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shape", default="bp-large")
    ap.add_argument("--only", choices=["tester-tracking", "fold", "feedback"])
    ap.add_argument("--skip-summaries", action="store_true")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--docs-url", default="/")
    ap.add_argument("--fold-from-live", action="store_true",
                    help="build the fold sample from the tab in tournament.json "
                         "and .env, instead of the fake one. The fold publishes "
                         "only what a tab has already made public, so a real "
                         "tournament is the honest demo — and the one that shows "
                         "real scale.")
    a = ap.parse_args()

    port = free_port()
    mocktab.serve(port, block=False)
    time.sleep(0.6)
    bank = mocktab.Handler.bank
    slug = next((s for s, t in bank.by_slug.items()
                 if t._shape_file.replace(".json", "") == a.shape), None)
    if not slug:
        sys.exit(f"no shape {a.shape!r}; have "
                 f"{[t._shape_file for t in bank.by_slug.values()]}")
    tour = bank.by_slug[slug].sh["name"]
    env = dict(os.environ, TABBY_BASE=f"http://127.0.0.1:{port}", TABBY_SLUG=slug,
               TABBY_USER="demo", TABBY_PASS="demo")

    os.makedirs(OUT, exist_ok=True)
    print(f"building samples from {tour} (shape {a.shape}, slug {slug})\n")
    facts = {}
    if a.only in (None, "tester-tracking"):
        print("  tester tracking")
        facts["tester_tracking"] = build_tester_tracking(env, tour, a.docs_url + "tester-tracking/")
    if a.only in (None, "fold"):
        if a.fold_from_live:
            sys.path.insert(0, os.path.join(ROOT, "core"))
            import config
            live_url, live_slug = config.tab()
            live_env = dict(os.environ, TABBY_BASE=live_url, TABBY_SLUG=live_slug)
            if not (live_env.get("TABBY_TOKEN") or live_env.get("TABBY_USER")):
                sys.exit("no sign-in loaded — set .env first "
                         "(set -a; . .env; set +a)")
            print(f"  the fold — from the LIVE tab at {live_url}/{live_slug}")
            print("    only what that tab has already made public reaches the page;"
                  "\n    the gate decides that, not this script")
            import subprocess as _sp
            name = _sp.run([sys.executable, "-c",
                            "import sys,os;sys.path.insert(0,'core');import tabread;"
                            "print(tabread.TabRead().api('').get('name',''))"],
                           cwd=ROOT, env=live_env, capture_output=True,
                           text=True).stdout.strip().splitlines()
            live_tour = name[-1] if name else "a real tournament"
            facts["fold"] = build_fold(live_env, live_tour,
                                       a.docs_url + "fold/", live=True)
            facts["fold"]["live"] = True
            facts["fold"]["tournament"] = live_tour
        else:
            print("  the fold")
            facts["fold"] = build_fold(env, tour, a.docs_url + "fold/")
    if a.only in (None, "feedback"):
        print("  judge feedback")
        facts["feedback"] = build_feedback(env, tour, a.docs_url + "feedback/",
                                          a.skip_summaries, a.jobs)
    with open(os.path.join(OUT, "sample-facts.json"), "w") as fh:
        json.dump({"tournament": tour, "shape": a.shape, **facts}, fh, indent=2)
    print(f"\ndone — demo/samples/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
