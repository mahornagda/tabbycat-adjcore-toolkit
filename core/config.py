"""
config.py — one place that knows which tournament this is.

Everything the three tools display, publish to, or connect to comes from
`tournament.json` at the top of the repo. Nothing about the tournament is
written into the code, so adopting the toolkit is editing one file.

Credentials are the exception: they live in `.env` and never in
`tournament.json`, so the config file is safe to commit, screenshot and paste
into a chat when you are asking someone for help.

Environment variables win over the file, which is what lets the demo point all
three tools at a local fake tournament without touching your real config:

    TABBY_BASE=http://127.0.0.1:8799 TABBY_SLUG=demo ./pull.py
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PATH = os.environ.get("TOOLKIT_CONFIG") or os.path.join(ROOT, "tournament.json")

DEFAULTS = {
    "tournament": {"name": "", "short": "", "timezone": "UTC"},
    "tab": {"url": "", "slug": ""},
    "publish": {"host": "cloudflare", "fold_project": "", "feedback_project": ""},
    "tester_tracking": {"port": 8790},
    "feedback": {"min_comments": 3, "model": "opus", "concurrency": 4},
}


class ConfigError(RuntimeError):
    pass


def _merge(base, over):
    out = dict(base)
    for k, v in (over or {}).items():
        out[k] = _merge(base[k], v) if isinstance(base.get(k), dict) and isinstance(v, dict) else v
    return out


def load():
    raw = {}
    if os.path.exists(PATH):
        try:
            with open(PATH, encoding="utf-8") as fh:
                raw = json.load(fh)
        except json.JSONDecodeError as e:
            raise ConfigError(
                f"{PATH} is not valid JSON — {e}.\n"
                "Most often this is a missing comma, or a smart quote pasted in from a document. "
                "Copy tournament.example.json over it and start again if you are stuck."
            ) from e
    cfg = _merge(DEFAULTS, raw)

    # Environment wins, so the demo and CI never need a config file at all.
    cfg["tab"]["url"] = (os.environ.get("TABBY_BASE") or cfg["tab"]["url"] or "").rstrip("/")
    cfg["tab"]["slug"] = os.environ.get("TABBY_SLUG") or cfg["tab"]["slug"] or ""
    if os.environ.get("TOURNAMENT_NAME"):
        cfg["tournament"]["name"] = os.environ["TOURNAMENT_NAME"]
    if not cfg["tournament"]["short"]:
        cfg["tournament"]["short"] = cfg["tournament"]["name"]
    return cfg


def tab():
    """(url, slug) — raises a sentence you can act on rather than a KeyError."""
    c = load()
    url, slug = c["tab"]["url"], c["tab"]["slug"]
    if not url or not slug:
        raise ConfigError(
            "I do not know which tab to read.\n"
            f"  Set \"tab\": {{\"url\": ..., \"slug\": ...}} in {PATH}\n"
            "  The url is everything before the tournament name: https://something.calicotab.com\n"
            "  The slug is the tournament's own bit of the address: .../<slug>/\n"
            "  Or, just for one run:  TABBY_BASE=... TABBY_SLUG=... <command>"
        )
    return url, slug


def auth():
    """(token, username, password) from the environment only — never from the
    config file, so tournament.json stays safe to share.

    A token is preferred: it is revocable on its own, where a password is not.
    A username and password are still needed for the two admin pages the REST
    API does not cover, which is what tester tracking reads for feedback
    progress and check-in status.
    """
    token = os.environ.get("TABBY_TOKEN") or ""
    u, p = os.environ.get("TABBY_USER") or "", os.environ.get("TABBY_PASS") or ""
    if not token and not (u and p):
        raise ConfigError(
            "No way to sign in to the tab was found.\n"
            "\n"
            "  Put one of these in .env at the top of the repo:\n"
            "\n"
            "    export TABBY_TOKEN=your-api-token            # preferred\n"
            "      Find it on your tab's home page, under 'Change Password'.\n"
            "\n"
            "    export TABBY_USER=your-tab-username          # or this\n"
            "    export TABBY_PASS=your-tab-password\n"
            "      The same sign-in you use in a browser. Needed as well as a\n"
            "      token if you want tester tracking's feedback-progress and\n"
            "      check-in columns, which come from admin pages rather than\n"
            "      the API.\n"
            "\n"
            "  then load it into your shell:  set -a; . .env; set +a\n"
            "  .env is gitignored. It must never be committed or pasted anywhere."
        )
    return token, u, p


def credentials():
    """Kept for anything that still wants just the pair."""
    token, u, p = auth()
    return u, p


def name():
    """What the pages call this tournament. Empty is fine — pages then say nothing."""
    return load()["tournament"]["name"]


def short():
    return load()["tournament"]["short"]
