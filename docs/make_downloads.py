#!/usr/bin/env python3
"""
make_downloads.py — the zip mirror, for people who do not use git.

    python3 docs/make_downloads.py

Writes docs/dist/downloads/adjcore-toolkit.zip.

The archive is built from an EXPLICIT list of what belongs in it, not by zipping
the working directory and hoping .gitignore covers everything. A working copy
holds a real tournament's pull, a real .env and a real tournament.json, and the
consequence of a mistake here is publishing somebody's private URL keys — so the
rule is that a file has to be named to get in, rather than named to stay out.
"""
import os, sys, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "dist", "downloads")
NAME = "adjcore-toolkit"

# Directories whose contents are included, and the extensions allowed in them.
TREES = {
    "core": (".py",),
    "tester-tracking": (".py", ".html", ""),
    "tester-tracking/cloud": (".mjs", ".html", ".json", ".toml"),
    "tester-tracking/cloud/functions": (".mjs",),
    "fold": (".py", ""),
    "fold/src": (".js", ".css", ".html"),
    "fold/tests": (".py",),
    "feedback": (".py", ".md", ""),
    "feedback/src": (".js", ".css", ".html"),
    "feedback/tests": (".py",),
    "demo": (".py",),
    "demo/shapes": (".json",),
    "demo/corpus": (".txt",),
    "docs": (".py",),
    "docs/content": (".py",),
    "automation": (".md",),
    "tests": (".py",),
    ".claude/skills/setup": (".md",),
}

FILES = ["README.md", "LICENSE", ".gitignore",
         "tournament.example.json", ".env.example"]

# Never, under any circumstances, whatever the extension rules say.
NEVER = {".env", "tournament.json", "raw.json", "bundles.json", "data.json",
         "adjcore_state.json", "verify-report.json"}
NEVER_DIRS = {"dist", "samples", "data", "summaries", "shots", "__pycache__",
              "node_modules", ".netlify", ".wrangler", "backups"}


def wanted():
    out = []
    for f in FILES:
        p = os.path.join(ROOT, f)
        if os.path.exists(p):
            out.append((p, f))
        else:
            print(f"  ! missing {f}")
    for tree, exts in TREES.items():
        d = os.path.join(ROOT, tree)
        if not os.path.isdir(d):
            print(f"  ! missing directory {tree}")
            continue
        for fn in sorted(os.listdir(d)):
            full = os.path.join(d, fn)
            if not os.path.isfile(full):
                continue
            if fn in NEVER or fn.startswith("." ) and fn not in (".gitignore",):
                continue
            ext = os.path.splitext(fn)[1]
            # "" allows extensionless scripts: refresh, review, start
            if ext not in exts and not (ext == "" and "" in exts):
                continue
            if any(part in NEVER_DIRS for part in tree.split("/")):
                continue
            out.append((full, f"{tree}/{fn}"))
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    entries = wanted()
    bad = [a for _, a in entries
           if os.path.basename(a) in NEVER
           or any(p in NEVER_DIRS for p in a.split("/"))]
    if bad:
        sys.exit(f"refusing to build: {bad}")

    path = os.path.join(OUT, f"{NAME}.zip")
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for full, arc in entries:
            info = zipfile.ZipInfo.from_file(full, f"{NAME}/{arc}")
            # keep the executable bit on the three shell entry points
            if os.access(full, os.X_OK) and "." not in os.path.basename(arc):
                info.external_attr = (0o755 << 16)
            with open(full, "rb") as fh:
                z.writestr(info, fh.read())
    kb = os.path.getsize(path) // 1024
    print(f"wrote docs/dist/downloads/{NAME}.zip — {len(entries)} files, {kb} KB")

    with zipfile.ZipFile(path) as z:
        names = z.namelist()
    # `.env.example` and `tournament.example.json` are meant to be in here; the
    # real ones must never be. Match the exact basename rather than a substring,
    # or the templates trip their own guard.
    for guard in ("data/", "dist/", "summaries/"):
        hit = [n for n in names if guard in n]
        if hit:
            sys.exit(f"archive contains {guard}: {hit[:3]}")
    for guard in (".env", "tournament.json"):
        hit = [n for n in names if os.path.basename(n) == guard]
        if hit:
            sys.exit(f"archive contains {guard}: {hit[:3]}")
    print("  checked: no pulled data, no config, no build output")
    return 0


if __name__ == "__main__":
    sys.exit(main())
