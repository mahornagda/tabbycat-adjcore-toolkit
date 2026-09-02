"""
server.py — the adjcore dashboard.

Serves the dashboard on your laptop and on the venue wifi, so the rest of
adjcore can open it on their phones.

Reads from Tabbycat. Never writes to it. The only thing this app writes is a
local file (adjcore_state.json) holding your own tester picks and notes —
that file never leaves this machine and never touches the tab.
"""
import http.server, socketserver, json, os, socket, threading, traceback, webbrowser, sys

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "adjcore_state.json")
DATA = os.path.join(HERE, "data.json")
PORT = int(os.environ.get("ADJCORE_PORT", "8790"))

_lock = threading.Lock()
_status = {"running": False, "log": [], "error": None}


def lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80)); ip = s.getsockname()[0]; s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def do_refresh():
    import pull
    with _lock:
        _status.update(running=True, log=[], error=None)
        try:
            pull.run(log=lambda m: _status["log"].append(str(m)))
        except Exception as e:
            _status["error"] = f"{type(e).__name__}: {e}"
            _status["log"].append(traceback.format_exc()[-800:])
        finally:
            _status["running"] = False


class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=HERE, **kw)

    def log_message(self, *a):
        pass

    def end_headers(self):
        # The page itself must never be cached, or an edit to index.html
        # silently does not show up until someone hard-refreshes.
        if self.path in ("/", "/index.html"):
            self.send_header("Cache-Control", "no-store, must-revalidate")
        super().end_headers()

    def _json(self, obj, code=200):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path.startswith("/api/status"):
            return self._json(_status)
        if self.path.startswith("/api/data"):
            if not os.path.exists(DATA):
                return self._json({"error": "no data yet — press Refresh"}, 404)
            b = open(DATA, "rb").read()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(b)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            return self.wfile.write(b)
        if self.path in ("/", "/index.html"):
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(n) or b"{}")
        if self.path.startswith("/api/refresh"):
            if _status["running"]:
                return self._json({"ok": False, "msg": "already refreshing"})
            threading.Thread(target=do_refresh, daemon=True).start()
            return self._json({"ok": True})
        if self.path.startswith("/api/state"):
            # LOCAL ONLY. Never sent to Tabbycat.
            # ?quiet=1 -> just write the file. Used by cell comments, which
            # nothing derived depends on, so re-reading the tab would be waste.
            quiet = "quiet=1" in self.path
            tmp = STATE + ".tmp"
            with open(tmp, "w") as f:
                json.dump(body, f, indent=1)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, STATE)          # atomic; refresh always sees a complete file
            if not quiet:
                threading.Thread(target=do_refresh, daemon=True).start()
            return self._json({"ok": True})
        return self._json({"error": "unknown"}, 404)


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    if not os.path.exists(DATA):
        print("no data yet — doing a first read from Tabbycat…")
        do_refresh()
        if _status["error"]:
            print("FAILED:", _status["error"]); sys.exit(1)
    url = f"http://localhost:{PORT}/"
    print(f"\n  Adjcore dashboard is up.\n")
    print(f"    On this laptop      {url}")
    print(f"    On the venue wifi   http://{lan_ip()}:{PORT}/")
    print(f"\n  Read-only against Tabbycat. Ctrl-C to stop.\n")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    Server(("0.0.0.0", PORT), H).serve_forever()
