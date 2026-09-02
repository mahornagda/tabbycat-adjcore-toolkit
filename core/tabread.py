"""
tabread.py — the only way any tool in this toolkit talks to Tabbycat, and it can
only read.

THE GUARANTEE, AND WHY IT IS STRUCTURAL RATHER THAN A PROMISE
-------------------------------------------------------------
`_GetOnlySession` subclasses `requests.Session` and overrides the single method
every request in the library funnels through. Anything that is not GET, HEAD or
OPTIONS raises `ReadOnlyViolation` before a packet leaves the machine. There is
no write method on this class to call, and no flag that turns one on. If someone
added `session.post(...)` anywhere downstream, it would raise rather than write.

The one POST in the whole toolkit is the Django login form, and it is done on a
throwaway session that is closed immediately; only its cookies are carried into
the read-only client. You can verify all of this in about a minute:

    grep -rn "\\.post\\|\\.patch\\|\\.delete\\|\\.put" --include=*.py .

This matters because you will probably have to convince a tab director to give
you an account, and "it cannot write, here is the line that enforces it" is a
much better answer than "it does not write".

TWO WAYS TO AUTHENTICATE, AND WHICH TO PREFER
---------------------------------------------
1. A TOKEN, if you have one. Tabbycat generates one per user and shows it under
   *Change Password* on the tab's home page (and under *Tokens* in the Edit
   Database area, where that is available). Set `TABBY_TOKEN` and this client
   sends `Authorization: Token ...` and never sees your password at all. Prefer
   this: a token is revocable on its own, and a password is not.

2. THE LOGIN FORM, otherwise. Set `TABBY_USER` and `TABBY_PASS` and this client
   posts the ordinary sign-in form and keeps the session cookie. Needed for the
   admin pages the REST API does not cover — feedback progress and check-in
   status — because those are ordinary pages rather than API endpoints.

Give it both and it uses both: the token for the API, the session for the two
admin pages. Tester tracking wants those pages; the fold and the feedback tool
do not, so a token alone is enough for them.
"""
import json, os, re, sys, time
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config

SAFE = {"GET", "HEAD", "OPTIONS"}
UA = "tabbycat-adjcore-toolkit/1.0 (read-only)"


class ReadOnlyViolation(RuntimeError):
    """Raised instead of sending anything that could change the tab."""


class TabError(RuntimeError):
    """A problem talking to Tabbycat, phrased so you can act on it."""


class _GetOnlySession(requests.Session):
    def request(self, method, url, *a, **kw):
        if str(method).upper() not in SAFE:
            raise ReadOnlyViolation(
                f"blocked {str(method).upper()} {url}\n"
                "This toolkit is read-only by construction. If you are seeing this, "
                "some code tried to change the tab — that is a bug, not a setting."
            )
        return super().request(method, url, *a, **kw)


class TabRead:
    """A read-only reader for one tournament.

    >>> t = TabRead()                  # url, slug and login from config + .env
    >>> t.api("rounds", paginate=True)
    """

    def __init__(self, base=None, slug=None, user=None, password=None,
                 token=None, quiet=True):
        if base is None or slug is None:
            cfg_base, cfg_slug = config.tab()
            base, slug = base or cfg_base, slug or cfg_slug
        self.base, self.slug = base.rstrip("/"), slug
        self.s = _GetOnlySession()
        self.s.headers["User-Agent"] = UA
        self.user = None
        self.auth = None

        token = token or os.environ.get("TABBY_TOKEN") or ""
        if user is None and password is None and not token:
            # Neither given explicitly: take whatever the environment has, and
            # say so clearly if it has nothing.
            token, user, password = config.auth()

        if token:
            self.s.headers["Authorization"] = f"Token {token.strip()}"
            self.auth = "token"
        if user and password:
            self._login(user, password)
            self.auth = "token+session" if token else "session"
        if not self.auth:
            raise TabError(
                "No way to sign in was given.\n"
                "  Either set a token (preferred):   export TABBY_TOKEN=...\n"
                "  or a username and password:       export TABBY_USER=... TABBY_PASS=...\n"
                "  Your token is on your tab's home page under 'Change Password'."
            )
        if self.user is None:
            try:
                self.user = self.api("users/me", tournament=False)
            except Exception:
                self.user = {}
        if not quiet:
            who = (self.user or {}).get("username", "?")
            print(f"reading {self.base}/{self.slug} as {who} ({self.auth})")

    def needs_admin_pages(self):
        """True if this client can read the two admin pages the REST API does
        not expose. A token authenticates the API but not an ordinary page, so
        feedback progress and check-in status need the session as well."""
        return self.auth in ("session", "token+session")

    # ------------------------------------------------------------------ auth --
    def _login(self, username, password):
        """The one POST in the toolkit. Runs on a separate, disposable session."""
        url = f"{self.base}/accounts/login/"
        boot = requests.Session()
        boot.headers["User-Agent"] = UA
        try:
            r = boot.get(url, timeout=30)
            r.raise_for_status()
        except requests.RequestException as e:
            raise TabError(
                f"could not reach {url}\n"
                "  Check the \"url\" in tournament.json. It should be everything before the\n"
                "  tournament name, with no trailing slash and no /admin on the end.\n"
                f"  ({e.__class__.__name__})"
            ) from e
        m = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', r.text)
        if not m:
            raise TabError(
                f"{url} did not look like a Tabbycat login page.\n"
                "  The most common cause is a url that points at something else — a site\n"
                "  front page, or a tournament path rather than the site root."
            )
        boot.post(url, timeout=30, headers={"Referer": url},
                  data={"csrfmiddlewaretoken": m.group(1), "username": username,
                        "password": password, "next": f"/{self.slug}/"})
        if "sessionid" not in boot.cookies:
            boot.close()
            raise TabError(
                "Tabbycat did not accept that login.\n"
                "  Check TABBY_USER and TABBY_PASS in .env — they are the username and\n"
                "  password you use to sign in to the tab in a browser, not a private URL\n"
                "  and not an email address."
            )
        self.s.cookies.update(boot.cookies)
        boot.close()
        try:
            self.user = self.api("users/me", tournament=False)
        except Exception:
            self.user = {}

    # ------------------------------------------------------------------- api --
    def api(self, path, paginate=False, tournament=True, params=None, tries=3):
        """GET the REST API.

        `paginate=True` follows the RFC 5988 `Link: rel="next"` header, which is
        how Tabbycat pages long lists. Note there is no trailing slash on
        `/api/v1` — with one, Tabbycat returns 404.
        """
        url, out = self._url(path, tournament), []
        while url:
            d = self._get_json(url, params=params, tries=tries)
            params = None                      # only the first page takes them
            if not paginate:
                return d
            out.extend(d if isinstance(d, list) else [d])
            url = self._next(self._last_link)
        return out

    def _url(self, path, tournament=True):
        if str(path).startswith("http"):
            return path
        p = str(path).strip("/")
        root = f"{self.base}/api/v1"
        base = f"{root}/tournaments/{self.slug}" if tournament else root
        return f"{base}/{p}" if p else base

    def _get_json(self, url, params=None, tries=3):
        last = None
        for attempt in range(tries):
            try:
                r = self.s.get(url, params=params, timeout=120)
                if r.status_code == 403:
                    raise TabError(
                        f"403 Forbidden on {url}\n"
                        "  The login worked but this account cannot see that. Feedback, panels\n"
                        "  and unreleased draws need a tab-side account (adjudication core or\n"
                        "  tabulation). A public or participant account will not do."
                    )
                if r.status_code == 404 and "/api/v1/" in url:
                    raise TabError(
                        f"404 on {url}\n"
                        "  Check the \"slug\" in tournament.json — it is the tournament's own bit\n"
                        "  of the web address, the part right after the host name."
                    )
                r.raise_for_status()
                self._last_link = r.headers.get("Link", "")
                return r.json()
            except TabError:
                raise
            except (requests.RequestException, ValueError) as e:
                last = e
                if attempt < tries - 1:
                    time.sleep(1.5 * (attempt + 1))
        raise TabError(f"gave up on {url} after {tries} tries — {last!r}") from last

    _last_link = ""

    @staticmethod
    def _next(link):
        for part in (link or "").split(","):
            m = re.match(r'\s*<([^>]+)>;\s*rel="next"', part)
            if m:
                return m.group(1)
        return None

    # ------------------------------------------- admin pages the API misses --
    def vuedata(self, page):
        """Every Tabbycat admin page hydrates its tables from a `window.vueData`
        global. Parsing it reaches views the REST API does not expose — feedback
        progress and check-in status, in particular. Still a GET of a page you
        are allowed to open in a browser."""
        url = f"{self.base}/{self.slug}/{str(page).lstrip('/')}"
        r = self.s.get(url, timeout=240)
        r.raise_for_status()
        m = re.search(r"window\.vueData\s*=\s*\{(.*)", r.text, re.S)
        if not m:
            return {}
        body, out, dec = m.group(1), {}, json.JSONDecoder()
        for km in re.finditer(r"['\"]?(\w+)['\"]?\s*:", body):
            s = body[km.end():].lstrip()
            if s[:1] in ("[", "{"):
                try:
                    out.setdefault(km.group(1), dec.raw_decode(s)[0])
                except Exception:
                    pass
        return out

    def tables(self, page):
        """Admin tables as [{title, head, rows}] with every cell flattened to text."""
        res = []
        for t in (self.vuedata(page).get("tablesData") or []):
            head = [h.get("title") or h.get("key", "") for h in (t.get("head") or [])]
            rows = [[self._cell(c) for c in row] for row in (t.get("data") or [])]
            res.append({"title": t.get("title"), "head": head, "rows": rows})
        return res

    @staticmethod
    def _cell(c):
        if isinstance(c, dict):
            for k in ("text", "sort", "html"):
                if c.get(k) not in (None, ""):
                    return re.sub(r"<[^>]+>", "", str(c[k])).strip()
            return ""
        return str(c)


# Kept so `from tabby import Tabby` in older scripts still resolves to the
# read-only client rather than silently finding something that can write.
Tabby = TabRead
