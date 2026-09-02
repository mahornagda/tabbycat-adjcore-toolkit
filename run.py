#!/usr/bin/env python3
"""
run.py — the one command. Works the same on Windows, macOS and Linux.

    python3 run.py                  what can I do?
    python3 run.py check            have I got what I need?
    python3 run.py demo             try all three tools on a fake tournament
    python3 run.py setup            point it at your tournament (asks 3 things)
    python3 run.py testers          tester tracking
    python3 run.py fold             build the public page and open it
    python3 run.py fold --publish   put it online
    python3 run.py feedback         consolidated judge feedback, step by step

Everything else in this repository can be run directly if you prefer, and the
docs say how. This file exists because the direct way means changing directory,
knowing which script comes next, and running shell scripts that do not exist on
Windows — and none of that is the interesting part of the job.

It is plain Python with no dependencies beyond `requests`, calls the same
modules the scripts do, and never shells out to a shell.
"""
import argparse, importlib.util, os, platform, shutil, subprocess, sys, webbrowser

ROOT = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable or "python3"
WIN = platform.system() == "Windows"

C = {"b": "\033[1m", "d": "\033[2m", "g": "\033[32m", "r": "\033[31m",
     "y": "\033[33m", "x": "\033[0m"}
if WIN and not os.environ.get("WT_SESSION"):
    C = {k: "" for k in C}          # old Windows consoles show the codes literally


def say(msg=""):
    # Flushed, because everything below runs the repo's scripts as subprocesses
    # and unflushed parent output arrives after the child's — so the headings
    # ended up printed underneath the thing they were introducing.
    print(msg, flush=True)


def head(msg):
    say(f"\n{C['b']}{msg}{C['x']}")


def ok(msg):
    say(f"  {C['g']}ok{C['x']}   {msg}")


def bad(msg):
    say(f"  {C['r']}no{C['x']}   {msg}")


def hint(msg):
    say(f"       {C['d']}{msg}{C['x']}")


def load(rel, name):
    """Import a module by path, so nothing depends on how you invoked this."""
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, rel))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def run_module(rel, args=(), cwd=None, quiet=False):
    """Run one of the repo's scripts as a subprocess, so a failure in it cannot
    take this process down and its output arrives as it happens."""
    cmd = [PY, os.path.join(ROOT, rel), *args]
    r = subprocess.run(cmd, cwd=cwd or ROOT,
                       stdout=subprocess.DEVNULL if quiet else None)
    return r.returncode == 0


# --------------------------------------------------------------------- check --
def cmd_check(a):
    head("What you need")
    good = True

    v = sys.version_info
    if v >= (3, 9):
        ok(f"Python {v.major}.{v.minor}")
    else:
        bad(f"Python {v.major}.{v.minor} — 3.9 or newer is needed")
        good = False

    try:
        import requests  # noqa: F401
        ok("the requests package")
    except ImportError:
        bad("the requests package is missing")
        hint(f"{os.path.basename(PY)} -m pip install requests")
        good = False

    head("Only needed for particular things")
    if shutil.which("claude"):
        ok("the claude command — judge feedback can write its summaries")
    else:
        say(f"  {C['y']}--{C['x']}   no claude command. Everything works except "
            f"judge feedback,")
        hint("which uses it to write the summaries: https://claude.com/claude-code")
    if shutil.which("npx"):
        ok("npx — the fold and feedback pages can be published online")
    else:
        say(f"  {C['y']}--{C['x']}   no npx. You can still build the pages and open "
            f"them locally;")
        hint("publishing them needs Node: https://nodejs.org")

    head("Your tournament")
    cfg = os.path.join(ROOT, "tournament.json")
    if os.path.exists(cfg):
        sys.path.insert(0, os.path.join(ROOT, "core"))
        import config
        try:
            url, slug = config.tab()
            ok(f"tournament.json points at {url}/{slug}")
        except Exception as e:
            bad("tournament.json is there but incomplete")
            hint(str(e).splitlines()[0])
            good = False
    else:
        say(f"  {C['y']}--{C['x']}   no tournament.json yet — run "
            f"{C['b']}{os.path.basename(PY)} run.py setup{C['x']}")
    if os.environ.get("TABBY_TOKEN") or os.environ.get("TABBY_USER"):
        ok("a sign-in is loaded in this window")
    elif os.path.exists(os.path.join(ROOT, ".env")):
        say(f"  {C['y']}--{C['x']}   .env exists but is not loaded in this window")
        hint(env_hint())
    else:
        say(f"  {C['y']}--{C['x']}   no .env yet — run "
            f"{C['b']}{os.path.basename(PY)} run.py setup{C['x']}")

    say()
    if good:
        say(f"{C['g']}Ready.{C['x']} Try:  {os.path.basename(PY)} run.py demo")
    return 0 if good else 1


def env_hint():
    if WIN:
        return ('in PowerShell:  Get-Content .env | ForEach-Object '
                '{ if ($_ -match \'^export (\\w+)=(.*)$\') '
                '{ [Environment]::SetEnvironmentVariable($Matches[1],$Matches[2]) } }')
    return "set -a; . .env; set +a"


# ---------------------------------------------------------------------- demo --
def cmd_demo(a):
    head("Trying all three tools on a tournament that does not exist")
    say("  No tournament, no sign-in, nothing sent anywhere. If this works, your")
    say("  install is fine and any later problem is about your tab, not your laptop.\n")
    args = [] if a.full else ["--quick"]
    return 0 if run_module("demo/verify.py", args) else 1


# --------------------------------------------------------------------- setup --
def cmd_setup(a):
    head("Pointing this at your tournament")
    say("  Three questions. Nothing is sent anywhere until you answer them.\n")

    say(f"{C['b']}1. Your tab's web address{C['x']}")
    hint("Everything before the tournament name. No slash on the end.")
    hint("e.g. https://yourtournament.calicotab.com")
    url = input("   > ").strip().rstrip("/")

    say(f"\n{C['b']}2. The tournament's bit of the address{C['x']}")
    hint("If your tab is at https://x.calicotab.com/openx26/  this is  openx26")
    slug = input("   > ").strip().strip("/")

    say(f"\n{C['b']}3. Your API token{C['x']}")
    hint("Sign in to your tab in a browser, then open 'Change Password' on the")
    hint("home page. Your token is on that page. Safer than a password, because")
    hint("you can revoke just the token from there.")
    hint("Press enter with nothing to use a username and password instead.")
    token = input("   > ").strip()
    user = pw = ""
    if not token:
        say("\n   Username (the one you sign in to the tab with):")
        user = input("   > ").strip()
        say("   Password:")
        try:
            import getpass
            pw = getpass.getpass("   > ")
        except Exception:
            pw = input("   > ")

    if not url or not slug or not (token or (user and pw)):
        say(f"\n{C['r']}Nothing written — one of those was empty.{C['x']}")
        return 1

    import json
    cfg_path = os.path.join(ROOT, "tournament.json")
    example = os.path.join(ROOT, "tournament.example.json")
    cfg = json.load(open(example, encoding="utf-8")) if os.path.exists(example) else {}
    cfg.setdefault("tournament", {})
    cfg["tab"] = {"url": url, "slug": slug}
    cfg.setdefault("publish", {})
    cfg["publish"].setdefault("host", "cloudflare")
    if not cfg["publish"].get("fold_project") or "yourtournament" in str(
            cfg["publish"].get("fold_project")):
        cfg["publish"]["fold_project"] = f"{slug}-fold"
        cfg["publish"]["feedback_project"] = f"{slug}-feedback"
    cfg.pop("_comment", None)
    for k in list(cfg):
        if isinstance(cfg[k], dict):
            cfg[k].pop("_comment", None)
    with open(cfg_path, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=2)
        fh.write("\n")
    ok(f"wrote tournament.json")

    env_path = os.path.join(ROOT, ".env")
    lines = ["# Written by run.py setup. Never commit this file.\n"]
    if token:
        lines.append(f"export TABBY_TOKEN={token}\n")
    if user:
        lines += [f"export TABBY_USER={user}\n", f"export TABBY_PASS={pw}\n"]
    with open(env_path, "w", encoding="utf-8") as fh:
        fh.writelines(lines)
    try:
        os.chmod(env_path, 0o600)
    except OSError:
        pass
    ok(".env written, readable only by you")

    # Try it immediately, in this process, so the answer arrives now.
    head("Checking it can read your tab")
    os.environ.setdefault("TABBY_TOKEN", token or "")
    if user:
        os.environ["TABBY_USER"], os.environ["TABBY_PASS"] = user, pw
    sys.path.insert(0, os.path.join(ROOT, "core"))
    try:
        import tabread
        t = tabread.TabRead(base=url, slug=slug,
                            token=token or None,
                            user=user or None, password=pw or None)
        tour = t.api("")
        rounds = t.api("rounds", paginate=True)
        cats = t.api("break-categories", paginate=True)
        teams = t.api("teams", paginate=True)
        adjs = t.api("adjudicators", paginate=True)
        prelim = [r for r in rounds if r.get("stage") == "P"]
        elim = [r for r in rounds if r.get("stage") == "E"]
        ok(f"{tour.get('name')}")
        say(f"       {len(prelim)} preliminary rounds, {len(elim)} break rounds")
        say(f"       {len(teams)} teams, {len(adjs)} judges")
        say(f"       break categories: "
            + (", ".join(f"{c['name']} ({c['break_size']})" for c in cats) or "none"))
        say(f"\n  {C['b']}Do those numbers look like your tournament?{C['x']}")
        say(f"  {C['d']}If not, it is almost always the slug.{C['x']}")
    except Exception as e:
        bad("could not read your tab")
        for line in str(e).splitlines()[:6]:
            hint(line)
        return 1

    head("What now")
    p = os.path.basename(PY)
    say(f"  {p} run.py testers     who has been watched, and who still needs to be")
    say(f"  {p} run.py fold        the public page, built and opened locally")
    say(f"  {p} run.py feedback    consolidated judge feedback")
    say(f"\n  In a new terminal window you will need to load .env first:")
    hint(env_hint())
    return 0


# ------------------------------------------------------------------- testers --
def cmd_testers(a):
    head("Tester tracking")
    if not run_module("tester-tracking/pull.py", cwd=os.path.join(ROOT, "tester-tracking")):
        return 1
    say("\n  Starting the dashboard. Go to the Testing tab — that is the one that")
    say("  matters. Stop it with ctrl-c when you are done.\n")
    return 0 if run_module("tester-tracking/server.py",
                           cwd=os.path.join(ROOT, "tester-tracking")) else 1


# ---------------------------------------------------------------------- fold --
def cmd_fold(a):
    head("The fold" + (" — publishing" if a.publish else " — building only"))
    fold = os.path.join(ROOT, "fold")
    args = ["--offline"] if a.offline else []
    if not run_module("fold/build.py", args, cwd=fold):
        return 1
    if not run_module("fold/tests/test_gate.py", cwd=fold):
        say(f"\n{C['r']}The checks failed, so nothing will be published.{C['x']}")
        return 1
    page = os.path.join(fold, "dist", "index.html")
    if not a.publish:
        say(f"\n  Built. Opening it so you can see exactly what a spectator would.")
        say(f"  {C['d']}{page}{C['x']}")
        say(f"\n  Happy with it?  {os.path.basename(PY)} run.py fold --publish")
        try:
            webbrowser.open("file://" + page)
        except Exception:
            pass
        return 0
    return 0 if publish(os.path.join(fold, "dist"), "fold_project") else 1


# ------------------------------------------------------------------ feedback --
def cmd_feedback(a):
    fb = os.path.join(ROOT, "feedback")
    steps = [
        ("pull", "reading the written feedback", "feedback/pull.py", ["--stats"]),
        ("mask", "replacing every name with a placeholder", "feedback/bundle.py", []),
        ("write", "writing the summaries (the slow step)", "feedback/summarise.py", []),
        ("build", "building the pages", "feedback/build.py", []),
        ("check", "re-running every content check", "feedback/tests/test_gate.py", []),
    ]
    if a.step:
        steps = [s for s in steps if s[0] == a.step]
        if not steps:
            say("steps: pull, mask, write, build, check")
            return 1
    for name, what, rel, args in steps:
        head(f"{name} — {what}")
        if not run_module(rel, args, cwd=fb):
            return 1
        if name == "write" and not a.step:
            say(f"\n  {C['b']}Stop here and read some of them.{C['x']}")
            say(f"  They are ordinary files in feedback/summaries/ and you can edit")
            say(f"  any of them by hand — the build never overwrites your edits.")
            say(f"\n  This is judge feedback going out under your adjudication core's")
            say(f"  name, so a person should have read it.")
            say(f"\n  When you have:  {os.path.basename(PY)} run.py feedback --step build")
            say(f"                  {os.path.basename(PY)} run.py feedback --step check")
            say(f"                  {os.path.basename(PY)} run.py feedback --publish")
            return 0
    if a.publish:
        return 0 if publish(os.path.join(fb, "dist"), "feedback_project") else 1
    say(f"\n  Built. Publish with:  {os.path.basename(PY)} run.py feedback --publish")
    return 0


# ------------------------------------------------------------------- publish --
def publish(directory, project_key):
    """Put a built directory online. Uses npx, which exists on every platform."""
    sys.path.insert(0, os.path.join(ROOT, "core"))
    import config
    cfg = config.load()
    project = (cfg.get("publish") or {}).get(project_key) or ""
    host = (cfg.get("publish") or {}).get("host") or "cloudflare"
    if not project:
        bad(f'no site name set. Add "{project_key}" under "publish" in tournament.json')
        return False
    if not shutil.which("npx"):
        bad("publishing needs Node (for npx): https://nodejs.org")
        hint(f"the built page is in {directory} and works if you open it directly")
        return False
    if host == "cloudflare":
        cmd = ["npx", "--yes", "wrangler@latest", "pages", "deploy", directory,
               "--project-name", project, "--commit-dirty=true"]
        say(f"  publishing to https://{project}.pages.dev")
        say(f"  {C['d']}the first run opens a browser to sign in to Cloudflare{C['x']}")
    elif host == "netlify":
        cmd = ["npx", "--yes", "netlify-cli", "deploy", "--prod", "--dir", directory]
    else:
        cmd = ["npx", "--yes", "surge", directory, f"{project}.surge.sh"]
    r = subprocess.run(cmd, shell=WIN)
    if r.returncode:
        bad("the deploy failed — the message above says why")
        return False
    if host == "cloudflare":
        say(f"\n  {C['g']}Live at https://{project}.pages.dev{C['x']}")
        say(f"  {C['d']}the deploy also prints a one-off preview address; the one "
            f"above is the address to share{C['x']}")
    return True


# ---------------------------------------------------------------------- menu --
def cmd_menu(a):
    p = os.path.basename(PY)
    say(f"""
{C['b']}Tabbycat Adjcore Toolkit{C['x']}

  {C['b']}{p} run.py check{C['x']}     have I got what I need?
  {C['b']}{p} run.py demo{C['x']}      try all three tools on a fake tournament
  {C['b']}{p} run.py setup{C['x']}     point it at your tournament — asks 3 things

  {C['b']}{p} run.py testers{C['x']}   tester tracking: who has been watched
  {C['b']}{p} run.py fold{C['x']}      the public fold, break and simulator
  {C['b']}{p} run.py feedback{C['x']}  consolidated judge feedback

If you have never run this before, do {C['b']}demo{C['x']} first. It needs no
tournament and no sign-in, and it proves the install works.

Docs: https://tabbycat-adjcore-toolkit.pages.dev
""")
    return 0


def main():
    ap = argparse.ArgumentParser(add_help=False)
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("check")
    d = sub.add_parser("demo"); d.add_argument("--full", action="store_true")
    sub.add_parser("setup")
    sub.add_parser("testers")
    f = sub.add_parser("fold")
    f.add_argument("--publish", action="store_true")
    f.add_argument("--offline", action="store_true")
    b = sub.add_parser("feedback")
    b.add_argument("--publish", action="store_true")
    b.add_argument("--step", default=None)
    ap.add_argument("-h", "--help", action="store_true")
    a = ap.parse_args()

    if a.help or not a.cmd:
        return cmd_menu(a)
    return {"check": cmd_check, "demo": cmd_demo, "setup": cmd_setup,
            "testers": cmd_testers, "fold": cmd_fold,
            "feedback": cmd_feedback}[a.cmd](a)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nstopped")
        sys.exit(130)
