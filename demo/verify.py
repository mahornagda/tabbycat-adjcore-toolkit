#!/usr/bin/env python3
"""
verify.py — run all three tools against every demo tournament and report.

    python3 demo/verify.py              every shape, every tool
    python3 demo/verify.py --shape two-team
    python3 demo/verify.py --quick      skip the browser tests

This is the toolkit's own answer to "but is anything hardcoded to the tournament
you built it for?". Rather than asserting that nothing is, it points the three
tools at deliberately different tournaments — a four-team nine-round event with
two break categories, a two-team five-round one, and a small one whose break has
not been announced — and shows them adapting with no code changed and no
configuration beyond a slug.

Everything runs against demo/mocktab.py. No credentials, no network, no real
tournament is reachable from here.
"""
import argparse, json, os, re, socket, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import mocktab
from generate import load_shape

GREEN, RED, DIM, OFF = "\033[32m", "\033[31m", "\033[2m", "\033[0m"


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def run(cmd, cwd, env, timeout=600):
    r = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True,
                       timeout=timeout)
    out = "\n".join(l for l in (r.stdout + r.stderr).splitlines()
                    if "NotOpenSSLWarning" not in l and "warnings.warn" not in l)
    return r.returncode, out


def field(out, pattern, default="—"):
    m = re.search(pattern, out)
    return m.group(1).strip() if m else default


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shape", help="just one shape file's slug or filename")
    ap.add_argument("--quick", action="store_true", help="skip the browser tests")
    ap.add_argument("--port", type=int, default=0)
    a = ap.parse_args()

    port = a.port or free_port()
    base = f"http://127.0.0.1:{port}"
    mocktab.serve(port, block=False)
    time.sleep(0.6)
    bank = mocktab.Handler.bank

    slugs = sorted(bank.by_slug)
    if a.shape:
        want = a.shape.replace(".json", "")
        slugs = [s for s in slugs if s == want
                 or bank.by_slug[s]._shape_file.replace(".json", "") == want]
        if not slugs:
            sys.exit(f"no shape matching {a.shape!r}; have "
                     f"{[bank.by_slug[s]._shape_file for s in sorted(bank.by_slug)]}")

    base_env = dict(os.environ)
    base_env.update({"TABBY_BASE": base, "TABBY_USER": "demo", "TABBY_PASS": "demo"})

    results, failures = [], []
    for slug in slugs:
        t = bank.by_slug[slug]
        env = dict(base_env, TABBY_SLUG=slug)
        print(f"\n{'=' * 74}\n{t.sh['name']}  {DIM}({t._shape_file}, slug {slug}){OFF}")
        print(f"  {t.tpd} teams a debate · {len(t['prelim_rounds'])} prelims · "
              f"{len([r for r in t.rounds if r['stage'] == 'E'])} elim rounds · "
              f"{len(t.teams)} teams · {len(t.adjs)} judges · "
              f"{len(t.bcats)} break categor{'y' if len(t.bcats) == 1 else 'ies'}")
        row = {"tournament": t.sh["name"], "slug": slug, "teams_in_debate": t.tpd}

        # ---- tester tracking ----
        code, out = run([sys.executable, "pull.py"], os.path.join(ROOT, "tester-tracking"), env)
        ok = code == 0
        row["tester_tracking"] = field(out, r"done — (.*)$") if ok else "FAILED"
        print(f"  {GREEN + 'ok  ' + OFF if ok else RED + 'FAIL' + OFF} tester tracking   "
              f"{row['tester_tracking']}")
        if not ok:
            failures.append((slug, "tester-tracking/pull.py", out[-600:]))

        # ---- the fold ----
        code, out = run([sys.executable, "build.py"], os.path.join(ROOT, "fold"), env)
        ok = code == 0
        row["fold"] = field(out, r"(\d+ teams · .*rooms shown)") if ok else "FAILED"
        print(f"  {GREEN + 'ok  ' + OFF if ok else RED + 'FAIL' + OFF} the fold          "
              f"{row['fold']}")
        if not ok:
            failures.append((slug, "fold/build.py", out[-600:]))
        else:
            code, out = run([sys.executable, "tests/test_gate.py"],
                            os.path.join(ROOT, "fold"), env)
            ok = code == 0
            print(f"  {GREEN + 'ok  ' + OFF if ok else RED + 'FAIL' + OFF} fold gate checks  "
                  f"{'all passed' if ok else 'FAILED'}")
            row["fold_gate"] = "pass" if ok else "FAIL"
            if not ok:
                failures.append((slug, "fold/tests/test_gate.py", out[-900:]))
            if not a.quick:
                code, out = run([sys.executable, "tests/smoke.py"],
                                os.path.join(ROOT, "fold"), env, timeout=900)
                ok = code == 0
                n_ok = len(re.findall(r"^  ok ", out, re.M))
                n_skip = len(re.findall(r"^  -- ", out, re.M))
                print(f"  {GREEN + 'ok  ' + OFF if ok else RED + 'FAIL' + OFF} fold browser tests"
                      f" {n_ok} passed"
                      + (f", {n_skip} not applicable" if n_skip else ""))
                row["fold_smoke"] = f"{n_ok} passed" if ok else "FAIL"
                if not ok:
                    failures.append((slug, "fold/tests/smoke.py", out[-1500:]))

        # ---- feedback ----
        code, out = run([sys.executable, "pull.py", "--stats"],
                        os.path.join(ROOT, "feedback"), env)
        ok = code == 0
        row["feedback"] = field(out, r"\((\d+ written comments about \d+ judges)\)") if ok else "FAILED"
        print(f"  {GREEN + 'ok  ' + OFF if ok else RED + 'FAIL' + OFF} feedback pull     "
              f"{row['feedback']}")
        if not ok:
            failures.append((slug, "feedback/pull.py", out[-600:]))
        else:
            code, out = run([sys.executable, "bundle.py"],
                            os.path.join(ROOT, "feedback"), env)
            ok = code == 0
            fmt = field(out, r"format[^:]*: (.*)$")
            print(f"  {GREEN + 'ok  ' + OFF if ok else RED + 'FAIL' + OFF} feedback bundle   "
                  f"{field(out, r'(masked .*)$') if ok else 'FAILED'}")
            row["feedback_bundle"] = "pass" if ok else "FAIL"
            if not ok:
                failures.append((slug, "feedback/bundle.py", out[-900:]))
        results.append(row)

    print(f"\n{'=' * 74}")
    if failures:
        print(f"{RED}{len(failures)} failure(s){OFF}\n")
        for slug, what, tail in failures:
            print(f"--- {slug}: {what} ---\n{tail}\n")
        return 1
    print(f"{GREEN}Every tool ran against every tournament with no code changed.{OFF}")
    print("\nWhat each one read off the live config rather than being told:")
    for r in results:
        print(f"  · {r['tournament']}: {r['teams_in_debate']} teams a debate — "
              f"{r.get('fold', '')}")
    out = os.path.join(HERE, "verify-report.json")
    with open(out, "w") as fh:
        json.dump(results, fh, indent=2)
    print(f"\nwritten to {os.path.relpath(out, ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
