#!/usr/bin/env python3
"""
mocktab.py — a fake Tabbycat, good enough that the real tools cannot tell.

    python3 demo/mocktab.py                 serve every shape in shapes/ on :8799
    python3 demo/mocktab.py --port 9000     somewhere else
    python3 demo/mocktab.py --list          what slugs are available

Then point any tool at it. The tools are NOT modified and know nothing about
this file:

    export TABBY_BASE=http://127.0.0.1:8799 TABBY_SLUG=demo
    export TABBY_USER=demo TABBY_PASS=demo
    cd tester-tracking && ./pull.py

WHAT IT IMPLEMENTS
------------------
Only what the three tools actually ask for, in the shapes Tabbycat actually
returns — including the two details that bite people writing against the real
API for the first time:

  · `/api/v1` has NO trailing slash. With one, Tabbycat 404s. So does this.
  · lists are unpaginated by default; `?limit=` switches on paging and the next
    page arrives in an RFC 5988 `Link: <...>; rel="next"` header, not in the
    body. So does this.

It also serves the two admin pages the REST API does not cover — feedback
progress and check-in status — as HTML with a `window.vueData` global, because
that is how Tabbycat hydrates its own tables and how the toolkit reads them.

Both ways of authenticating work, because both are worth testing:

  · `Authorization: Token ...` on the API, the way Tabbycat's own docs describe;
  · the Django login form — GET returns a page with a csrfmiddlewaretoken, POST
    sets a `sessionid` cookie — which is what the two admin pages need, since
    they are ordinary pages rather than API endpoints.

Any token and any password are accepted. There is nothing here to protect. What
IS enforced is the distinction that matters in the field: the admin pages refuse
a token-only client, exactly as the real ones do, so a tool that needs a session
finds that out here rather than at somebody's tournament.
"""
import argparse, glob, json, os, re, sys, threading, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from generate import Tournament, load_shape

LOGIN_HTML = """<!doctype html><html><head><title>Log in — mocktab</title></head>
<body><h1>Log in</h1>
<form method="post" action="/accounts/login/">
<input type="hidden" name="csrfmiddlewaretoken" value="mocktab-csrf-token">
<input name="username"><input name="password" type="password">
<button>Log in</button></form></body></html>"""

VUE_PAGE = """<!doctype html><html><head><title>%(title)s</title></head><body>
<div id="vue-container"></div>
<script>window.vueData = %(data)s;</script>
</body></html>"""


class Bank:
    """Every shape in shapes/, indexed by slug, built once."""

    def __init__(self, base, only=None):
        self.base, self.by_slug = base, {}
        paths = sorted(glob.glob(os.path.join(HERE, "shapes", "*.json")))
        for p in paths:
            shape = load_shape(p)
            if only and shape["slug"] != only:
                continue
            self.by_slug[shape["slug"]] = Tournament(shape, base=base)
            self.by_slug[shape["slug"]]._shape_file = os.path.basename(p)
        if not self.by_slug:
            self.by_slug["demo"] = Tournament(load_shape(None), base=base)

    def get(self, slug):
        return self.by_slug.get(slug)


def _paged(handler, rows, query):
    """Tabbycat pages only when asked, and says where the next page is in a
    header rather than the body. Mirroring that exactly is the point: a client
    that ignores the Link header silently truncates against the real thing, and
    it should silently truncate here too rather than pass and fail in the field."""
    limit = query.get("limit", [None])[0]
    offset = int(query.get("offset", ["0"])[0] or 0)
    if not limit:
        return rows, None
    limit = int(limit)
    page = rows[offset:offset + limit]
    nxt = None
    if offset + limit < len(rows):
        q = dict(query)
        q["limit"], q["offset"] = [str(limit)], [str(offset + limit)]
        nxt = f"{handler.path.split('?')[0]}?" + urllib.parse.urlencode(q, doseq=True)
    return page, nxt


class Handler(BaseHTTPRequestHandler):
    server_version = "mocktab/1.0"
    bank = None
    verbose = False

    # ------------------------------------------------------------- plumbing --
    def log_message(self, fmt, *a):
        if Handler.verbose:
            sys.stderr.write("  mocktab  " + fmt % a + "\n")

    def _send(self, code, body, ctype="application/json", headers=()):
        raw = body if isinstance(body, bytes) else str(body).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        for k, v in headers:
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(raw)

    def _json(self, data, nxt=None):
        headers = [("Link", f'<{self.bank.base}{nxt}>; rel="next"')] if nxt else []
        self._send(200, json.dumps(data, ensure_ascii=False), headers=headers)

    def _404(self, why="not found"):
        self._send(404, json.dumps({"detail": why}))

    # ---------------------------------------------------------------- routes --
    def do_POST(self):
        if self.path.rstrip("/") == "/accounts/login":
            self.send_response(302)
            self.send_header("Location", "/")
            self.send_header("Set-Cookie", "sessionid=mocktab-session; Path=/")
            self.send_header("Set-Cookie", "csrftoken=mocktab-csrf-token; Path=/")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        self._send(405, json.dumps({"detail": "mocktab is read-only too"}))

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path.rstrip("/") == "/accounts/login":
            return self._send(200, LOGIN_HTML, "text/html; charset=utf-8")
        if path == "/":
            return self._send(200, self._index(), "text/html; charset=utf-8")

        # The real API 404s on a trailing slash after /api/v1. Do the same, or
        # this mock teaches a habit that breaks in the field.
        if path == "/api/v1/":
            return self._404("no trailing slash on /api/v1")

        m = re.match(r"^/api/v1/users/me/?$", path)
        if m:
            return self._json({"username": "demo", "email": "demo@example.invalid",
                               "is_superuser": True, "is_staff": False})

        m = re.match(r"^/api/v1/institutions/?$", path)
        if m:
            rows = []
            for t in self.bank.by_slug.values():
                for i in t.insts:
                    if not any(r["id"] == i["id"] for r in rows):
                        rows.append(i)
            page, nxt = _paged(self, rows, query)
            return self._json(page, nxt)

        m = re.match(r"^/api/v1/institutions/(\d+)/?$", path)
        if m:
            for t in self.bank.by_slug.values():
                for i in t.insts:
                    if i["id"] == int(m.group(1)):
                        return self._json(i)
            return self._404()

        m = re.match(r"^/api/v1/tournaments/([^/]+)(/.*)?$", path)
        if m:
            slug, rest = m.group(1), (m.group(2) or "").strip("/")
            t = self.bank.get(slug)
            if not t:
                return self._404(f"no tournament {slug!r}; try {sorted(self.bank.by_slug)}")
            return self._tournament(t, rest, query)

        # admin pages: the two views the REST API does not expose. These are
        # ordinary Django pages, so a token does not open them — only a session
        # does. Enforcing that is the point; a mock that let a token through
        # would hide a real failure until it happened live.
        if "/admin/" in path and "sessionid" not in (self.headers.get("Cookie") or ""):
            return self._send(403, json.dumps({
                "detail": "this is an ordinary admin page, not an API endpoint — "
                          "it needs a session (TABBY_USER / TABBY_PASS), not a token"}))

        m = re.match(r"^/([^/]+)/admin/feedback/progress/?$", path)
        if m and self.bank.get(m.group(1)):
            return self._send(200, VUE_PAGE % {
                "title": "Feedback progress",
                "data": json.dumps(self._progress(self.bank.get(m.group(1))))},
                "text/html; charset=utf-8")

        m = re.match(r"^/([^/]+)/admin/checkins/status/people/?$", path)
        if m and self.bank.get(m.group(1)):
            return self._send(200, VUE_PAGE % {
                "title": "Check-ins",
                "data": json.dumps(self._checkins(self.bank.get(m.group(1))))},
                "text/html; charset=utf-8")

        self._404()

    # ------------------------------------------------------ the API surface --
    def _tournament(self, t, rest, query):
        if rest == "":
            current = [r["url"] for r in t.rounds
                       if r["draw_status"] != "N" and not r["completed"]]
            if not current:
                done = [r for r in t.rounds if r["completed"]]
                current = [done[-1]["url"]] if done else []
            return self._json({
                "name": t.sh["name"], "short_name": t.sh["short"], "slug": t.slug,
                "seq": 1, "active": True, "url": t.t_url(),
                "current_rounds": current,
            })

        simple = {
            "preferences": lambda: [{"identifier": k, "value": v}
                                    for k, v in self._prefs(t).items()],
            "rounds": lambda: [{k: v for k, v in r.items() if not k.startswith("_")}
                               for r in t.rounds],
            "break-categories": lambda: [{k: v for k, v in b.items()
                                          if not k.startswith("_")} for b in t.bcats],
            "speaker-categories": lambda: t_speaker_cats(t),
            "adjudicators": lambda: t.adjs,
            # `_strength` is generator bookkeeping; Tabbycat has no such field, so
            # serving it would let a tool accidentally depend on something real
            # tabs never send.
            "teams": lambda: [{k: v for k, v in tm.items() if not k.startswith("_")}
                              for tm in t.teams],
            "venues": lambda: t.venues,
            "motions": lambda: self._motions(t),
            "feedback": lambda: t.feedback,
            "feedback-questions": lambda: t.fq,
            "teams/standings/rounds": lambda: self._standings(t),
        }
        if rest in simple:
            page, nxt = _paged(self, simple[rest](), query)
            return self._json(page, nxt)

        m = re.match(r"^break-categories/(\d+)/break$", rest)
        if m:
            bc = next((b for b in t.bcats if b["id"] == int(m.group(1))), None)
            if not bc:
                return self._404()
            page, nxt = _paged(self, t.breaks.get(bc["slug"], []), query)
            return self._json(page, nxt)

        m = re.match(r"^break-categories/(\d+)/eligibility$", rest)
        if m:
            bc = next((b for b in t.bcats if b["id"] == int(m.group(1))), None)
            return self._json({"team_set": bc["_eligible"]}) if bc else self._404()

        m = re.match(r"^speaker-categories/(\d+)/eligibility$", rest)
        if m:
            spk = [s["url"] for tm in t.teams for s in tm["speakers"]]
            half = spk[: len(spk) // 2] if m.group(1) == "2" else spk
            return self._json({"speaker_set": half})

        m = re.match(r"^rounds/(\d+)/pairings$", rest)
        if m:
            seq = int(m.group(1))
            r = t["round"](seq)
            if not r:
                return self._404()
            if r["draw_status"] == "N":
                return self._json([])
            page, nxt = _paged(self, t.pairings.get(seq, []), query)
            return self._json(page, nxt)

        m = re.match(r"^rounds/(\d+)/pairings/(\d+)/ballots$", rest)
        if m:
            rows = getattr(t, "ballots", {}).get(int(m.group(2)), [])
            page, nxt = _paged(self, rows, query)
            return self._json(page, nxt)

        m = re.match(r"^rounds/(\d+)$", rest)
        if m:
            r = t["round"](int(m.group(1)))
            return self._json({k: v for k, v in r.items()
                               if not k.startswith("_")}) if r else self._404()

        for coll, rows in (("adjudicators", t.adjs), ("teams", t.teams),
                           ("venues", t.venues), ("feedback", t.feedback)):
            m = re.match(rf"^{coll}/(\d+)$", rest)
            if m:
                row = next((x for x in rows if x["id"] == int(m.group(1))), None)
                return self._json(row) if row else self._404()

        self._404(f"mocktab does not implement /{rest} — add it if a tool needs it")

    # ------------------------------------------------------------ sub-payloads --
    def _prefs(self, t):
        p = dict(t.sh["public"])
        p.update({
            "debate_rules__teams_in_debate": t.tpd,
            "debate_rules__substantive_speakers": int(t.sh["speakers_per_team"]),
            "debate_rules__side_names": t.sh["side_names"],
            "feedback__adj_min_score": 1.0,
            "feedback__adj_max_score": 10.0,
            "feedback__feedback_paths": "with-p-in-'s-panel",
            "draw_rules__adj_min_voting_score": 2.5,
            "public_features__tournament_staff":
                "<p>Convenors and the adjudication core are listed on the "
                "tournament's own page.</p>",
        })
        return p

    def _motions(self, t):
        from generate import _corpus
        texts = _corpus("motions.txt")
        out = []
        for i, r in enumerate(t["prelim_rounds"]):
            if not r["motions_released"]:
                continue
            out.append({
                "id": i + 1, "url": t.t_url("motions", i + 1),
                "text": texts[i % len(texts)],
                "reference": f"M{r['seq']}", "info_slide": "",
                "rounds": [{"round": r["url"], "seq": 1}],
            })
        return out

    def _standings(self, t):
        """Per-team, per-round points and sides — prelims only, exactly like the
        real endpoint. Elimination results are not here; they live on ballots."""
        out = []
        for tm in t.teams:
            rows = []
            for r in t["prelim_rounds"]:
                pts = t.points.get((r["seq"], tm["id"]))
                if pts is None:
                    continue
                rows.append({"round": r["url"], "points": pts,
                             "side": t.sides_of.get((r["seq"], tm["id"])),
                             "score": round(150.0 + pts * 3.5, 1)})
            out.append({"team": tm["url"], "rounds": rows})
        return out

    def _progress(self, t):
        """The feedback-progress admin table, in Tabbycat's vueData shape."""
        import collections
        got = collections.Counter(f["source"] for f in t.feedback)
        jrows, trows = [], []
        for a in t.adjs:
            expected = sum(1 for f in t.feedback if f["source"] == a["url"]) + 2
            done = got.get(a["url"], 0)
            jrows.append([{"text": a["name"]}, {"text": str(max(0, expected - done))},
                          {"text": f"{min(100, int(100 * done / max(1, expected)))}%"}])
        for tm in t.teams:
            expected = len([r for r in t["prelim_rounds"] if r["completed"]])
            done = got.get(tm["url"], 0)
            trows.append([{"text": tm["short_name"]}, {"text": str(max(0, expected - done))},
                          {"text": f"{min(100, int(100 * done / max(1, expected)))}%"}])
        return {"tablesData": [
            {"title": "Adjudicators",
             "head": [{"key": "name", "title": "name"}, {"key": "owed", "title": "owed"},
                      {"key": "percent", "title": "percent"}],
             "data": jrows},
            {"title": "Teams",
             "head": [{"key": "team", "title": "team"}, {"key": "owed", "title": "owed"},
                      {"key": "percent", "title": "percent"}],
             "data": trows},
        ]}

    def _checkins(self, t):
        events = [{"identifier": f"id{a['id']}"} for a in t.adjs if a["id"] % 5 != 0]
        events += [{"identifier": f"sp{s['id']}"} for tm in t.teams
                   for s in tm["speakers"] if s["id"] % 4 != 0]
        return {
            "events": events,
            "adjudicators": [{"id": a["id"], "name": a["name"],
                              "identifier": [f"id{a['id']}"]} for a in t.adjs],
            "speakers": [{"id": s["id"], "name": s["name"],
                          "identifier": [f"sp{s['id']}"]}
                         for tm in t.teams for s in tm["speakers"]],
        }

    def _index(self):
        rows = "".join(
            f"<li><code>{s}</code> — {t.sh['name']} · {t.tpd} teams a debate · "
            f"{len(t['prelim_rounds'])} prelims · {len(t.teams)} teams · "
            f"{len(t.adjs)} judges <small>({t._shape_file})</small></li>"
            for s, t in sorted(self.bank.by_slug.items()))
        return f"""<!doctype html><meta charset=utf-8>
<title>mocktab</title>
<style>body{{font:15px/1.6 system-ui;margin:40px auto;max-width:44rem;padding:0 1rem}}
code{{background:#f4f1ec;padding:1px 5px;border-radius:4px}}</style>
<h1>mocktab</h1>
<p>A fake Tabbycat for the toolkit's demo and tests. Nothing here is a real
tournament, and no real tournament is reachable from here.</p>
<h2>Tournaments served</h2><ul>{rows}</ul>
<h2>Point a tool at it</h2>
<pre>export TABBY_BASE={self.bank.base}
export TABBY_SLUG=demo TABBY_USER=demo TABBY_PASS=demo</pre>"""


def t_speaker_cats(t):
    return [{"id": 1, "url": t.t_url("speaker-categories", 1),
             "name": "Open", "slug": "open", "seq": 1, "public": True},
            {"id": 2, "url": t.t_url("speaker-categories", 2),
             "name": "Novice", "slug": "novice-speakers", "seq": 2, "public": True}]


def serve(port=8799, only=None, verbose=False, block=True):
    base = f"http://127.0.0.1:{port}"
    Handler.bank = Bank(base, only=only)
    Handler.verbose = verbose
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    if block:
        print(f"mocktab on {base}  —  slugs: {', '.join(sorted(Handler.bank.by_slug))}")
        print("  stop with ctrl-c")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nstopped")
    else:
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, base


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8799)
    ap.add_argument("--only", help="serve just this slug")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()
    if a.list:
        b = Bank(f"http://127.0.0.1:{a.port}")
        for s, t in sorted(b.by_slug.items()):
            print(f"{s:8s} {t.sh['name']:34s} {t.tpd} teams/debate  "
                  f"{len(t['prelim_rounds'])} prelims  {len(t.teams)} teams")
        sys.exit(0)
    serve(a.port, a.only, a.verbose)
