#!/usr/bin/env python3
"""
build.py — assemble the documentation site into docs/dist/.

    python3 docs/build.py            build
    python3 docs/build.py --serve    build, then serve it on :8788 to look at

Pages are Python modules in docs/content/, one per page, each exporting a
`PAGE` dict. That is deliberately not a markdown pipeline: the pages carry
annotated figures, two reading levels and a fair amount of structure, and
expressing those in markdown plus HTML escapes ends up less readable than
writing the components directly.

TWO READING LEVELS, ONE PAGE
----------------------------
Every page can carry blocks marked technical. A switch in the header adds a
class to the document root and the technical blocks appear or disappear; the
choice is remembered in the reader's browser. It is one page either way, so
the two versions cannot drift out of step, nothing is written twice, and a link
to a heading works whichever level the reader is on.
"""
import argparse, html, importlib.util, os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DIST = os.path.join(HERE, "dist")
sys.path.insert(0, HERE)
from annotate import CSS as FIGURE_CSS

SITE = "Tabbycat Adjcore Toolkit"
AUTHOR = "Mahor Nagda"

# slug, title, nav label, which group it belongs to
PAGES = [
    ("index",           "Three tools for an adjudication core", "Start here",        "top"),
    ("start",           "Set it up",                            "Set it up",          "using"),
    ("access",          "Getting access to your tab",           "Tab access",         "using"),
    ("tester-tracking", "Tester tracking",                      "Tester tracking",    "tools"),
    ("fold",            "The fold, and the simulator",          "The fold",           "tools"),
    ("feedback",        "Consolidated judge feedback",           "Judge feedback",     "tools"),
    ("how-it-works",    "How it all works",                     "How it works",       "deep"),
    ("limits",          "What it will not do",                   "Limits",             "deep"),
]
GROUPS = [("top", ""), ("using", "Running it"), ("tools", "The three tools"),
          ("deep", "Underneath")]

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600;9..144,700&family=Inter+Tight:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

:root{
  --bg:#FBF7F0; --sunk:#F4EDE1; --panel:#FFFDF9; --panel-2:#FAF5EC;
  --panel-strong:#FFFDF9;
  --ink:#1C1917; --dim:#57534E; --faint:#8A827A;
  --line:#E4DACA; --line-2:#D3C6B1;
  --accent:#C2410C; --accent-sk:#FDEAE0;
  --teal:#0F766E; --teal-sk:#DDF0EC;
  --gold:#A16207; --gold-sk:#FBF0D7;
  --plum:#7E3A8C; --plum-sk:#F3E6F6;
  --mark:#C2410C;
  --serif:"Fraunces",Georgia,serif;
  --sans:"Inter Tight",-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
  --mono:"JetBrains Mono",ui-monospace,"SF Mono",Menlo,monospace;
  --shadow:0 1px 2px rgba(28,25,23,.05), 0 8px 24px -14px rgba(28,25,23,.22);
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --bg:#17151A; --sunk:#100E12; --panel:#211E25; --panel-2:#282430;
    --panel-strong:#17151A;
    --ink:#F4F0EA; --dim:#B8B1A8; --faint:#837C74;
    --line:#332E3A; --line-2:#453E4F;
    --accent:#FB8B4E; --accent-sk:#3A2018;
    --teal:#4FD1C5; --teal-sk:#10312E;
    --gold:#E0B341; --gold-sk:#33270C;
    --plum:#D8A0E4; --plum-sk:#2E1A33;
    --mark:#FB8B4E;
  }
}
:root[data-theme="dark"]{
  --bg:#17151A; --sunk:#100E12; --panel:#211E25; --panel-2:#282430;
  --panel-strong:#17151A;
  --ink:#F4F0EA; --dim:#B8B1A8; --faint:#837C74;
  --line:#332E3A; --line-2:#453E4F;
  --accent:#FB8B4E; --accent-sk:#3A2018;
  --teal:#4FD1C5; --teal-sk:#10312E;
  --gold:#E0B341; --gold-sk:#33270C;
  --plum:#D8A0E4; --plum-sk:#2E1A33;
  --mark:#FB8B4E;
}

*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:16px/1.62 var(--sans);-webkit-font-smoothing:antialiased}
a{color:var(--accent);text-decoration:none;
  border-bottom:1px solid color-mix(in srgb, var(--accent) 34%, transparent)}
a:hover{border-bottom-color:var(--accent)}
code,kbd{font:.9em/1.5 var(--mono);background:var(--sunk);padding:1px 5px;
  border-radius:5px;border:1px solid var(--line)}
pre{background:var(--sunk);border:1px solid var(--line);border-radius:10px;
  padding:14px 16px;overflow-x:auto;font:13.5px/1.65 var(--mono);margin:18px 0}
pre code{background:none;border:0;padding:0;font-size:inherit}
h1,h2,h3,h4{font-family:var(--serif);font-weight:600;line-height:1.18;
  letter-spacing:-.01em;margin:0}
h1{font-size:clamp(1.9rem,4.2vw,2.7rem);margin-bottom:10px}
h2{font-size:1.52rem;margin:52px 0 12px;padding-top:8px}
h3{font-size:1.16rem;margin:32px 0 8px;font-family:var(--sans);font-weight:600}
p,ul,ol{margin:14px 0}
li{margin:6px 0}
hr{border:0;border-top:1px solid var(--line);margin:44px 0}

/* ---- shell --------------------------------------------------------------- */
.top{position:sticky;top:0;z-index:50;background:color-mix(in srgb,var(--bg) 92%,transparent);
  backdrop-filter:blur(10px);border-bottom:1px solid var(--line)}
.top .in{max-width:1180px;margin:0 auto;padding:12px 22px;display:flex;
  align-items:center;gap:18px;flex-wrap:wrap}
.brand{font-family:var(--serif);font-weight:700;font-size:1.06rem;
  color:var(--ink);border:0;display:flex;align-items:center;gap:9px}
.brand .sw{display:inline-flex;flex-direction:column;gap:2px}
.brand .sw i{display:block;width:19px;height:2.5px;border-radius:2px;background:var(--accent)}
.brand .sw i:nth-child(2){background:var(--teal);width:14px}
.brand .sw i:nth-child(3){background:var(--gold);width:17px}
.top nav{display:flex;gap:2px;margin-left:auto;flex-wrap:wrap}
.top nav a{border:0;padding:6px 11px;border-radius:7px;font-size:.92rem;
  color:var(--dim)}
.top nav a:hover{background:var(--sunk);color:var(--ink)}
.top nav a[aria-current]{background:var(--accent-sk);color:var(--accent);font-weight:500}

.levels{display:flex;gap:0;border:1px solid var(--line-2);border-radius:8px;
  overflow:hidden;background:var(--panel)}
.levels button{border:0;background:none;font:500 .85rem var(--sans);color:var(--dim);
  padding:6px 12px;cursor:pointer}
.levels button[aria-pressed="true"]{background:var(--accent);color:#FFFDF9}

.wrap{max-width:1180px;margin:0 auto;padding:0 22px;display:grid;
  grid-template-columns:214px minmax(0,1fr);gap:44px}
aside{padding:34px 0 60px;position:sticky;top:57px;align-self:start;
  max-height:calc(100vh - 57px);overflow-y:auto}
aside h4{font:600 .74rem var(--sans);letter-spacing:.09em;text-transform:uppercase;
  color:var(--faint);margin:22px 0 7px}
aside a{display:block;border:0;padding:5px 10px;border-radius:6px;font-size:.93rem;
  color:var(--dim)}
aside a:hover{background:var(--sunk);color:var(--ink)}
aside a[aria-current]{background:var(--accent-sk);color:var(--accent);font-weight:500}
main{padding:34px 0 90px;min-width:0}
.lede{font-size:1.14rem;color:var(--dim);margin:0 0 26px;max-width:64ch}

/* ---- components ---------------------------------------------------------- */
.cards{display:grid;gap:16px;grid-template-columns:repeat(auto-fit,minmax(258px,1fr));
  margin:26px 0}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;
  padding:19px 20px;box-shadow:var(--shadow)}
.card h3{margin:0 0 7px;font-family:var(--serif);font-size:1.1rem;font-weight:600}
.card p{margin:0 0 12px;font-size:.95rem;color:var(--dim)}
.card .go{font-size:.9rem;font-weight:500}

.note{background:var(--panel-2);border:1px solid var(--line);
  border-left:3px solid var(--teal);border-radius:9px;padding:14px 17px;margin:22px 0}
.note.warn{border-left-color:var(--gold);background:var(--gold-sk)}
.note.stop{border-left-color:var(--accent);background:var(--accent-sk)}
.note p:first-child{margin-top:0}.note p:last-child{margin-bottom:0}
.note b{font-weight:600}

.steps{counter-reset:s;list-style:none;padding:0;margin:24px 0}
.steps>li{counter-increment:s;position:relative;padding:0 0 4px 44px;margin:0 0 22px}
.steps>li::before{content:counter(s);position:absolute;left:0;top:-1px;width:28px;
  height:28px;border-radius:50%;background:var(--accent);color:#FFFDF9;
  font:600 .88rem var(--sans);display:grid;place-items:center}
.steps>li>b:first-child{display:block;font-family:var(--serif);font-size:1.08rem;
  font-weight:600;margin-bottom:5px}

table{width:100%;border-collapse:collapse;margin:22px 0;font-size:.94rem;
  display:block;overflow-x:auto}
th,td{text-align:left;padding:9px 12px;border-bottom:1px solid var(--line);
  vertical-align:top}
th{font:600 .76rem var(--sans);letter-spacing:.07em;text-transform:uppercase;
  color:var(--faint);white-space:nowrap}
tbody tr:last-child td{border-bottom:0}

.pill{display:inline-block;font:500 .74rem var(--sans);letter-spacing:.05em;
  text-transform:uppercase;padding:3px 9px;border-radius:20px;
  background:var(--teal-sk);color:var(--teal);border:1px solid transparent}
.pill.a{background:var(--accent-sk);color:var(--accent)}
.pill.g{background:var(--gold-sk);color:var(--gold)}
.pill.p{background:var(--plum-sk);color:var(--plum)}

.btnrow{display:flex;gap:11px;flex-wrap:wrap;margin:24px 0}
.btn{border:0;display:inline-flex;align-items:center;gap:7px;background:var(--accent);
  color:#FFFDF9;padding:10px 17px;border-radius:9px;font-weight:500;font-size:.95rem}
.btn:hover{border:0;filter:brightness(1.06)}
.btn.ghost{background:var(--panel);color:var(--ink);border:1px solid var(--line-2)}

/* the two reading levels */
.tech{display:none}
html.level-tech .tech{display:block}
html.level-tech li.tech,html.level-tech span.tech{display:list-item}
html.level-tech span.tech{display:inline}
.tech-only-note{display:none}
html.level-tech .tech-only-note{display:block}
.plain-only{display:block}
html.level-tech .plain-only{display:none}
.tech>h2:first-child,.tech>h3:first-child{margin-top:34px}
.techflag{font:500 .72rem var(--sans);letter-spacing:.06em;text-transform:uppercase;
  color:var(--plum);background:var(--plum-sk);padding:2px 8px;border-radius:20px;
  margin-left:8px;vertical-align:middle}

/* site map on the landing page */
.map{display:grid;gap:14px;grid-template-columns:repeat(auto-fit,minmax(226px,1fr));
  margin:22px 0}
.map section{background:var(--panel);border:1px solid var(--line);border-radius:11px;
  padding:16px 18px}
.map h4{font:600 .74rem var(--sans);letter-spacing:.09em;text-transform:uppercase;
  color:var(--faint);margin:0 0 9px}
.map ul{list-style:none;padding:0;margin:0}
.map li{margin:5px 0;font-size:.94rem}

footer{border-top:1px solid var(--line);padding:26px 22px 60px;color:var(--faint);
  font-size:.9rem}
footer .in{max-width:1180px;margin:0 auto;display:flex;gap:16px;flex-wrap:wrap}

@media (max-width:900px){
  .wrap{grid-template-columns:1fr;gap:0}
  aside{position:static;max-height:none;padding:18px 0 0;
    border-bottom:1px solid var(--line);margin-bottom:14px}
  aside h4{margin-top:12px}
  aside nav{display:flex;flex-wrap:wrap;gap:3px}
  aside a{padding:5px 9px}
}
""" + FIGURE_CSS

JS = """
(function () {
  var KEY = "adjcore-docs-level";
  var root = document.documentElement;
  function set(level, remember) {
    root.classList.toggle("level-tech", level === "tech");
    document.querySelectorAll(".levels button").forEach(function (b) {
      b.setAttribute("aria-pressed", String(b.dataset.level === level));
    });
    if (remember) { try { localStorage.setItem(KEY, level); } catch (e) {} }
  }
  var saved = "plain";
  try { saved = localStorage.getItem(KEY) || "plain"; } catch (e) {}
  set(saved, false);
  document.querySelectorAll(".levels button").forEach(function (b) {
    b.addEventListener("click", function () { set(b.dataset.level, true); });
  });
})();
"""


def nav(current):
    out = []
    for gid, label in GROUPS:
        items = [p for p in PAGES if p[3] == gid]
        if not items:
            continue
        if label:
            out.append(f"<h4>{label}</h4>")
        out.append("<nav>")
        for slug, title, navlabel, _ in items:
            href = "./" if slug == "index" else f"../{slug}/"
            if current == slug:
                href = "#"
            cur = ' aria-current="page"' if current == slug else ""
            out.append(f'<a href="{href}"{cur}>{html.escape(navlabel)}</a>')
        out.append("</nav>")
    return "".join(out)


def topnav(current):
    keys = ["start", "tester-tracking", "fold", "feedback", "how-it-works"]
    out = []
    for slug in keys:
        p = next(x for x in PAGES if x[0] == slug)
        href = "./" if slug == "index" else ("#" if current == slug
                                             else ("./" + slug + "/" if current == "index"
                                                   else "../" + slug + "/"))
        cur = ' aria-current="page"' if current == slug else ""
        out.append(f'<a href="{href}"{cur}>{html.escape(p[2])}</a>')
    return "".join(out)


def shell(slug, title, lede, body, depth):
    up = "" if depth == 0 else "../"
    home = "./" if depth == 0 else "../"
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)} — {SITE}</title>
<meta name="description" content="{html.escape(lede[:180])}">
<!-- The policy travels with the page as well as in _headers. A host matches
     header rules its own way — Cloudflare's `/` rule does not fire for the bare
     root, and `/*.html` never fires at all when pretty URLs are served from
     directory indexes — so the page carries its own copy. Everything except
     frame-ancestors works from a meta tag. -->
<meta http-equiv="Content-Security-Policy" content="{_CSP_DOCS}">
<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 32 32%22><text y=%2225%22 font-size=%2226%22>⚖️</text></svg>">
<style>{CSS}</style>
</head>
<body>
<header class="top"><div class="in">
  <a class="brand" href="{home}"><span class="sw"><i></i><i></i><i></i></span>{SITE}</a>
  <nav>{topnav(slug)}</nav>
  <div class="levels" role="group" aria-label="How much detail to show">
    <button data-level="plain" aria-pressed="true">Plain</button>
    <button data-level="tech" aria-pressed="false">Technical</button>
  </div>
</div></header>
<div class="wrap">
  <aside>{nav(slug)}</aside>
  <main>
    <h1>{html.escape(title)}</h1>
    <p class="lede">{lede}</p>
    {body}
  </main>
</div>
<footer><div class="in">
  <span>{SITE} — built by {AUTHOR}. MIT licensed.</span>
  <span>Tabbycat is a separate project; this is not affiliated with it.</span>
</div></footer>
<script>{JS}</script>
</body>
</html>"""


def load(slug):
    path = os.path.join(HERE, "content", slug.replace("-", "_") + ".py")
    spec = importlib.util.spec_from_file_location("page_" + slug, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.PAGE


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--serve", action="store_true")
    ap.add_argument("--port", type=int, default=8788)
    a = ap.parse_args()

    if os.path.exists(DIST):
        shutil.rmtree(DIST)
    os.makedirs(DIST)

    built = []
    for slug, title, navlabel, group in PAGES:
        page = load(slug)
        depth = 0 if slug == "index" else 1
        out_dir = DIST if slug == "index" else os.path.join(DIST, slug)
        os.makedirs(out_dir, exist_ok=True)
        html_text = shell(slug, page.get("title", title), page["lede"],
                          page["body"], depth)
        with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as fh:
            fh.write(html_text)
        built.append((slug, len(html_text) // 1024))

    # Figures live once at the site root and are referenced absolutely. Copying
    # them into each page directory instead multiplied a few megabytes of
    # screenshots by the page count.
    figs_src = os.path.join(HERE, "assets", "figures")
    if os.path.isdir(figs_src):
        shutil.copytree(figs_src, os.path.join(DIST, "assets", "figures"),
                        dirs_exist_ok=True)

    # the sample sites, if they have been built
    samples = os.path.join(ROOT, "demo", "samples")
    if os.path.isdir(samples):
        for name in os.listdir(samples):
            src = os.path.join(samples, name)
            if os.path.isdir(src):
                shutil.copytree(src, os.path.join(DIST, "samples", name),
                                dirs_exist_ok=True)
        print(f"  samples copied: {sorted(os.listdir(os.path.join(DIST, 'samples')))}")

    with open(os.path.join(DIST, "_headers"), "w") as fh:
        fh.write(_headers_text())

    # The zip mirror is part of the site, and this function empties dist/ on
    # every run — so building it here is the only way the download cannot end up
    # missing or stale relative to the pages that link to it.
    try:
        import make_downloads
        make_downloads.main()
    except SystemExit as e:
        if e.code:
            raise
    except Exception as e:
        print(f"  ! could not build the download: {e}")

    print(f"built docs/dist — {len(built)} pages")
    for slug, kb in built:
        print(f"  {slug:18s} {kb} KB")

    if a.serve:
        import http.server, functools
        os.chdir(DIST)
        h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=DIST)
        print(f"\nserving http://127.0.0.1:{a.port}  (ctrl-c to stop)")
        http.server.ThreadingHTTPServer(("127.0.0.1", a.port), h).serve_forever()
    return 0


# Cloudflare and Netlify both read ONE `_headers` file, at the root of what is
# published. Each tool ships its own policy for when it is published on its own,
# but under this site those files are never read — so the sample paths get their
# policies restated here. Without this the samples would be served weaker than
# the real thing, which makes them misleading evidence.
_CSP_STATIC = ("default-src 'none'; script-src 'unsafe-inline'; "
               "style-src 'unsafe-inline' https://fonts.googleapis.com; "
               "font-src https://fonts.gstatic.com; img-src data:; "
               "base-uri 'none'; form-action 'none'; frame-ancestors 'none'")

_CSP_DOCS = ("default-src 'none'; script-src 'unsafe-inline'; "
             "style-src 'unsafe-inline' https://fonts.googleapis.com; "
             "font-src https://fonts.gstatic.com; img-src 'self' data:; "
             "base-uri 'none'; form-action 'none'")


def _docs_csp_rules():
    """A rule per docs page, generated from PAGES.

    Not `/*`: a wildcard would match the sample paths too, and where two rules
    both set Content-Security-Policy the browser enforces the intersection — so
    the docs policy's missing `connect-src` would silently override the feedback
    sample's `connect-src 'self'` and stop a judge's page from loading.

    Not `/*.html` either, which was the first attempt: Cloudflare serves
    `/fold/` as a directory index, so that pattern matched nothing at all and the
    pages went out with no policy.
    """
    out = []
    for slug, *_ in PAGES:
        path = "/" if slug == "index" else f"/{slug}/*"
        out.append(f"\n{path}\n  Content-Security-Policy: {_CSP_DOCS}\n")
        if slug != "index":
            out.append(f"\n/{slug}\n  Content-Security-Policy: {_CSP_DOCS}\n")
    return "".join(out)


def _headers_text():
    return f"""/*
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=()
{_docs_csp_rules()}

/samples/fold/*
  Content-Security-Policy: {_CSP_STATIC}; connect-src 'none'

/samples/tester-tracking/*
  Content-Security-Policy: {_CSP_STATIC}; connect-src 'none'

/samples/feedback/*
  Content-Security-Policy: {_CSP_STATIC}; connect-src 'self'
  X-Robots-Tag: noindex, nofollow
  X-Frame-Options: DENY

/samples/feedback/f/*
  Cache-Control: no-store
  Content-Type: application/json; charset=utf-8
  X-Robots-Tag: noindex, nofollow
"""

if __name__ == "__main__":
    sys.exit(main())
