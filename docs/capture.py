#!/usr/bin/env python3
"""
capture.py — take the documentation screenshots from the sample sites.

    python3 docs/capture.py

Every figure in the docs comes from demo/samples/, which is built from the fake
tournament — so no screenshot can contain a real person, and any of them can be
regenerated exactly. Run demo/make_samples.py first.

The arrows and captions are NOT in these images. They are SVG laid over them at
page-build time (see annotate.py), so retaking a screenshot does not mean
redrawing the marks.
"""
import functools, http.server, os, socket, sys, threading

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SAMPLES = os.path.join(ROOT, "demo", "samples")
OUT = os.path.join(HERE, "assets", "figures")
VIEW = {"width": 1400, "height": 900}


def serve(directory):
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()

    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    h = functools.partial(Quiet, directory=directory)
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{port}"


SHOTS = [
    # (sample, name, path, actions, clip-height or None for viewport)
    ("tester-tracking", "tt-testing", "/",
     [("click-text", "Testing")], None),
    ("tester-tracking", "tt-coverage", "/",
     [("click-text", "Testing"), ("scroll", 1500)], None),
    ("tester-tracking", "tt-judges", "/",
     [("click-text", "Judges")], None),
    ("tester-tracking", "tt-rightnow", "/",
     [("click-text", "Right now")], None),
    ("fold", "fold-stack", "/", [], None),
    ("fold", "fold-bracket", "/", [("click", "#tab-bracket")], None),
    ("fold", "fold-sim", "/", [("click", "#tab-sim")], None),
    ("fold", "fold-speaks", "/", [("click", "#tab-speaks")], None),
    ("fold", "fold-judges", "/", [("click", "#tab-judges")], None),
    ("fold", "fold-shown", "/", [("click", "#tab-shown")], None),
    ("feedback", "fb-landing", "/", [], None),
    ("feedback", "fb-summary", "/#a8f1cd03", [], None),
    ("feedback", "fb-thin", "/#1ac6680f", [], None),
]


def main():
    from playwright.sync_api import sync_playwright
    os.makedirs(OUT, exist_ok=True)
    servers = {}
    for name in ("tester-tracking", "fold", "feedback"):
        d = os.path.join(SAMPLES, name)
        if not os.path.isdir(d):
            sys.exit(f"no sample at {d} — run demo/make_samples.py first")
        servers[name] = serve(d)

    written = []
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        for sample, name, path, actions, clip in SHOTS:
            srv, base = servers[sample]
            pg = b.new_page(viewport=VIEW, device_scale_factor=2)
            pg.goto(base + path)
            pg.wait_for_timeout(1400)
            for kind, arg in actions:
                if kind == "click":
                    pg.locator(arg).first.click()
                elif kind == "click-text":
                    pg.get_by_text(arg, exact=True).first.click()
                elif kind == "scroll":
                    pg.evaluate(f"window.scrollTo(0,{arg})")
                pg.wait_for_timeout(900)
            out = os.path.join(OUT, name + ".png")
            pg.screenshot(path=out)
            written.append((name, os.path.getsize(out) // 1024))
            pg.close()
        b.close()
    for srv, _ in servers.values():
        srv.shutdown()

    print(f"wrote {len(written)} figures to docs/assets/figures/")
    for name, kb in written:
        print(f"  {name:16s} {kb} KB")


if __name__ == "__main__":
    main()
