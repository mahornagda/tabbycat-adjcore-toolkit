#!/usr/bin/env python3
"""
test_release.py — the checks that must pass before this repo is published or
handed to anybody.

    python3 tests/test_release.py

None of these need a tournament, a network or credentials. They are about the
repository itself: that it carries no secrets, that the read-only guarantee is
still true, that the generated files are in sync with their source, and that
nothing about one particular tournament has crept back in.

The last of those is the one that needs saying plainly. This toolkit was written
during a real tournament and then separated from it. A check that greps for that
tournament's names cannot live in a public repo — publishing the list of names
you are hiding defeats the point. So the split is:

  · here            structural checks anybody can run and keep passing
  · before release  a private scan against the actual pulled data, which is the
                    only way to prove a specific participant is not mentioned

If you fork this for your own tournament, the checks here keep working, and the
private scan is yours to run against your own pull.
"""
import ast, json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
fails, passes = [], []


def check(ok, msg, detail=""):
    (passes if ok else fails).append(msg)
    print(("  ok   " if ok else "  FAIL ") + msg + (("\n         " + detail) if detail and not ok else ""))


def walk(exts=(".py", ".js", ".mjs", ".html", ".css", ".md", ".json", ".txt", ".sh", ".toml"),
         skip=("node_modules", "__pycache__", ".git", "dist", "samples", "shots",
               ".venv", ".wrangler", ".netlify")):
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in skip]
        for fn in filenames:
            if os.path.splitext(fn)[1] in exts or fn in ("refresh", "review", "start"):
                yield os.path.join(dirpath, fn)


def rel(p):
    return os.path.relpath(p, ROOT)


# ---------------------------------------------------------------- 1. secrets --
print("\nsecrets and pulled data")

SECRET_PATTERNS = [
    (r"(?i)\b(?:api[_-]?key|secret[_-]?key|access[_-]?token|bearer)\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}",
     "a hardcoded key or token"),
    # "demo" is what the demo signs in to the fake tab with, and the fake tab
    # accepts anything, so it is not a credential. A real one is longer and is
    # not one of the obvious placeholders.
    (r"(?i)\bTABBY_PASS\s*=\s*[\"']?(?!your-|demo|changeme|\$|\s|$)[^\s\"']{8,}",
     "a real-looking tab password"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "a private key"),
    (r"(?i)\bpassphrase\s*[:=]\s*['\"][^'\"]{6,}['\"]", "a hardcoded passphrase"),
]
found = []
for p in walk():
    if rel(p).startswith("tests/"):
        continue
    text = open(p, encoding="utf-8", errors="ignore").read()
    for rx, what in SECRET_PATTERNS:
        m = re.search(rx, text)
        if m:
            found.append(f"{rel(p)}: {what} — {m.group(0)[:48]}")
check(not found, "no credential, key or passphrase is committed", "; ".join(found[:4]))

FORBIDDEN = ["feedback/data/raw.json", "feedback/data/bundles.json", ".env",
             "tournament.json", "tester-tracking/data.json",
             "tester-tracking/adjcore_state.json", "fold/raw.json"]
# In a working copy these files exist and should: you have just pulled your own
# tournament. What must never be true is that one of them is publishable, so the
# check is "is it ignored", not "is it absent".
def ignored(path):
    try:
        r = subprocess.run(["git", "check-ignore", "-q", path], cwd=ROOT,
                           capture_output=True, text=True)
    except FileNotFoundError:
        return None
    # 0 = ignored, 1 = not ignored, 128 = there is no repository here yet.
    # Conflating the last two reports a clean tree as leaking.
    if r.returncode == 0:
        return True
    if r.returncode == 1:
        return False
    return None

present = [f for f in FORBIDDEN if os.path.exists(os.path.join(ROOT, f))]
leaky = [f for f in present if ignored(f) is False]
if ignored(".env") is None:
    # No git here — a zip download, or a copied directory. The presence of a
    # pull is then entirely normal (you have just run something) and .gitignore
    # is what protects it if this ever becomes a repository. Reporting that as a
    # failure teaches people to ignore the suite, so it is a note.
    if present:
        print("  note  " + f"{len(present)} pulled-data file(s) present: "
              + ", ".join(present))
        print("         Normal in a working copy. They are listed in .gitignore, "
              "and\n         feedback/data/ holds private URL keys — delete it "
              "when your\n         tournament is over.")
    check(True, "pulled data is accounted for (no git here, so nothing can be "
                "committed by accident yet)")
else:
    check(not leaky, f"every file that holds tournament data is ignored by git "
                     f"({len(present)} present locally, {len(present) - len(leaky)} ignored)",
          "NOT ignored: " + ", ".join(leaky))

gi = open(os.path.join(ROOT, ".gitignore"), encoding="utf-8").read()
missing = [f for f in (".env", "tournament.json", "feedback/data/") if f not in gi]
check(not missing, "the files that carry secrets are gitignored",
      "not ignored: " + ", ".join(missing))


# ------------------------------------------------------- 2. read-only proof --
print("\nthe read-only guarantee")

# Parsed, not grepped. A docstring that explains the guarantee mentions
# `session.post(...)`, and a grep counts that as a violation — which would make
# the check unusable exactly where the reasoning is written down.
writes = []
for p in walk(exts=(".py",)):
    if rel(p).startswith(("tests/", "demo/")):
        continue
    try:
        tree = ast.parse(open(p, encoding="utf-8").read())
    except SyntaxError:
        continue
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr not in ("post", "patch", "put", "delete"):
            continue
        obj = node.func.value
        owner = obj.id if isinstance(obj, ast.Name) else getattr(obj, "attr", "?")
        # The login form is the one allowed POST, and it runs on the throwaway
        # `boot` session — never on the read-only client.
        if owner == "boot" and node.func.attr == "post":
            continue
        writes.append(f"{rel(p)}:{node.lineno}: {owner}.{node.func.attr}()")
check(not writes, "no Python outside the login form can write to a tab",
      "; ".join(writes[:4]))

sys.path.insert(0, os.path.join(ROOT, "core"))
import tabread  # noqa: E402
blocked = []
for verb in ("POST", "PATCH", "PUT", "DELETE"):
    try:
        tabread._GetOnlySession().request(verb, "https://example.invalid/x")
        blocked.append(verb)
    except tabread.ReadOnlyViolation:
        pass
    except Exception:
        blocked.append(verb + " (raised something else)")
check(not blocked, "the client refuses every write verb before it reaches the network",
      "not blocked: " + ", ".join(blocked))

check(not hasattr(tabread.TabRead, "write"),
      "the client has no write method to call at all")


# ------------------------------------------- 3. generated files are in sync --
print("\ngenerated files")

sys.path.insert(0, os.path.join(ROOT, "core"))
import countries  # noqa: E402
import importlib  # noqa: E402
flags_js = open(os.path.join(ROOT, "fold", "src", "flags.js"), encoding="utf-8").read()
m = re.search(r"const COUNTRY_CODES = (\{.*?\});", flags_js, re.S)
check(bool(m), "fold/src/flags.js carries a country table")
if m:
    in_js = json.loads(m.group(1))
    check(in_js == countries.COUNTRIES,
          f"flags.js is in sync with core/countries.py ({len(in_js)} countries)",
          "re-run: python3 core/gen_flags.py")

check(len(countries.COUNTRIES) > 150,
      f"the country table covers the world, not one region "
      f"({len(countries.COUNTRIES)} countries)")
for region in ("Vietnam", "UK", "USA", "Korea", "Brazil", "Nigeria", "Poland"):
    if not countries.flag(region):
        check(False, f"a flag resolves for {region!r}")
        break
else:
    check(True, "flags resolve for countries on every continent, and for the "
                "common alternate spellings")


# --------------------------------------------------- 4. nothing format-bound --
print("\nnothing hardcoded to one tournament or one format")

# A default argument or a dict-get fallback is how you cope with a tab that did
# not answer; it is not a hardcode. What matters is an ASSIGNMENT that fixes the
# shape of the tournament, so the patterns exclude `def f(x=4)` and `.get(k, 4)`.
BAD = [
    (r"^(?!.*def )(?!.*\.get\().*\bteams_in_debate\s*=\s*4\b",
     "teams-in-a-debate assigned a constant"),
    (r"^(?!.*def )(?!.*\.get\().*\bprelims\s*=\s*[0-9]+\b",
     "a round count assigned a constant"),
    (r"^(?!.*def )(?!.*\.get\().*\bbreak_size\s*=\s*\d+", "a break size assigned a constant"),
]
bound = []
for p in walk(exts=(".py", ".js")):
    if rel(p).startswith(("tests/", "demo/")):
        continue
    for i, line in enumerate(open(p, encoding="utf-8", errors="ignore"), 1):
        if line.lstrip().startswith(("#", "*", "//")):
            continue
        for rx, what in BAD:
            if re.search(rx, line):
                bound.append(f"{rel(p)}:{i}: {what}")
check(not bound, "no tool hardcodes a round count, break size or format",
      "; ".join(bound[:4]))

prompt = open(os.path.join(ROOT, "feedback", "prompt.md"), encoding="utf-8").read()
tokens = set(re.findall(r"\{\{([A-Z_]+)\}\}", prompt))
summarise = open(os.path.join(ROOT, "feedback", "summarise.py"), encoding="utf-8").read()
filled = set(re.findall(r'\("\{\{([A-Z_]+)\}\}"', summarise))
check(tokens and tokens <= filled,
      f"every placeholder in prompt.md is filled at run time ({sorted(tokens)})",
      f"unfilled: {sorted(tokens - filled)}")


# ------------------------------------------------------------ 5. it compiles --
print("\nit runs")

broken = []
for p in walk(exts=(".py",)):
    if not p.endswith(".py"):
        continue          # refresh / review / start are shell scripts
    try:
        ast.parse(open(p, encoding="utf-8").read())
    except SyntaxError as e:
        broken.append(f"{rel(p)}:{e.lineno}: {e.msg}")
check(not broken, "every Python file parses", "; ".join(broken[:4]))

for name in ("tournament.example.json", ".env.example", "LICENSE", "README.md",
             "core/tabread.py", "core/config.py", "core/countries.py",
             "demo/mocktab.py", "demo/generate.py", "demo/verify.py",
             "feedback/prompt.md"):
    if not os.path.exists(os.path.join(ROOT, name)):
        check(False, f"{name} is present")
        break
else:
    check(True, "every file the setup instructions refer to exists")

try:
    json.load(open(os.path.join(ROOT, "tournament.example.json"), encoding="utf-8"))
    check(True, "tournament.example.json is valid JSON")
except Exception as e:
    check(False, "tournament.example.json is valid JSON", str(e))


# --------------------------------------------------------------------- done --
print(f"\n{len(passes)} passed, {len(fails)} failed")
if fails:
    print("\nfailed:")
    for f in fails:
        print("  ·", f)
    sys.exit(1)
print("\nready to publish.")
