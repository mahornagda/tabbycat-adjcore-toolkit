#!/usr/bin/env python3
"""
summarise.py — one consolidated summary per judge, written by Claude, checked by
the gate before it is allowed to exist on disk.

The loop that makes this trustworthy: draft -> gate.check() -> if anything failed,
hand the violations back to the model as an edit instruction and redraft. Only a
draft that passes every check is written to summaries/. So a leak is not
something the reviewer has to catch by eye.

  ./summarise.py                 write every judge that has no summary yet
  ./summarise.py --force         rewrite everyone
  ./summarise.py --only Adel     just the judges whose name matches
  ./summarise.py -j 6            six at a time (default 5)
  ./summarise.py --model NAME    default claude-opus-5

Nothing here reaches the internet. summaries/*.json is the reviewable artefact:
edit one by hand and it stays edited — build.py never regenerates.
"""
import argparse, concurrent.futures as cf, json, os, re, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gate, terms as T

BUNDLES = os.path.join(HERE, "data", "bundles.json")
OUTDIR = os.path.join(HERE, "summaries")
PROMPT = os.path.join(HERE, "prompt.md")
# Three was enough when one rule broke at a time. When two or three fire
# together — a near-quote and a stage word in the same draft — the model
# spends a try on each, so a fourth pass is the difference between a summary
# that exists and a judge who gets nothing.
MAX_TRIES = 4


def render_prompt(vocab):
    """prompt.md with this tournament's format filled in, written to a temp file
    because the CLI takes a system prompt as a path.

    The point of doing it here rather than in the file: a BP prompt handed to a
    two-team tournament tells the model to talk about extensions and the bench,
    and the summaries come back describing a debate that never happened."""
    fmt = (vocab or {}).get("format") or {}
    text = open(PROMPT, encoding="utf-8").read()
    for token, value in (
        ("{{FORMAT_LINE}}", fmt.get("format_line", "a debating tournament")),
        ("{{CRAFT_VOCAB}}", fmt.get("craft_vocab", "the case line, the comparative, deliberation")),
        ("{{SIDE_LABELS}}", fmt.get("side_labels", "government, opposition")),
    ):
        text = text.replace(token, value)
    left = re.findall(r"\{\{[A-Z_]+\}\}", text)
    if left:
        raise RuntimeError(f"prompt.md has placeholders nothing fills in: {sorted(set(left))}")
    fh = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8")
    fh.write(text); fh.close()
    return fh.name


def ask(payload, model, extra_system="", prompt_path=None):
    """One headless Claude call. No tools, no skills, no project context — this
    is a pure text transform and anything else is a way for something unrelated
    to end up in a judge's feedback."""
    cmd = ["claude", "-p", "--output-format", "json", "--model", model,
           "--system-prompt-file", prompt_path or PROMPT,
           "--exclude-dynamic-system-prompt-sections",
           "--disable-slash-commands", "--tools", ""]
    if extra_system:
        cmd += ["--append-system-prompt", extra_system]
    r = subprocess.run(cmd, input=payload, capture_output=True, text=True,
                       cwd=tempfile.gettempdir(), timeout=600)
    if r.returncode != 0:
        raise RuntimeError(f"claude exited {r.returncode}: {r.stderr[-400:]}")
    body = json.loads(r.stdout)
    if body.get("is_error"):
        raise RuntimeError(f"claude reported an error: {str(body.get('result'))[:300]}")
    txt = body["result"].strip()
    txt = re.sub(r"^```(?:json)?\s*|\s*```$", "", txt).strip()
    return json.loads(txt)


def render(comments):
    return ("Written comments about this judge:\n\n" +
            "\n".join(f"---\n{c}\n" for c in comments))


def one(aid, rec, model, vocab, prompt_path):
    payload = render(rec["comments"])
    notes, last = "", []
    for attempt in range(1, MAX_TRIES + 1):
        draft = ask(payload, model, notes, prompt_path)
        out = {k: draft.get(k) for k in ("overview", "strengths", "growth", "themes")}
        out["name"] = rec["name"]
        out["thin"] = bool(rec["thin"])
        out["generated"] = model
        bad = gate.check(out, rec["comments"], vocab)
        if not bad:
            path = os.path.join(OUTDIR, f"{aid}.json")
            json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            return aid, rec["name"], attempt, []
        last = bad
        # Feed the violations back as an instruction rather than starting over:
        # the draft is usually right and one rule is broken in one clause.
        notes = ("Your previous draft was rejected by the publication checks. Fix "
                 "exactly these and change nothing else:\n" +
                 "\n".join(f"- {b}" for b in bad) +
                 "\nReply with the corrected JSON object only.")
    return aid, rec["name"], MAX_TRIES, last


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--only", default=None)
    ap.add_argument("-j", "--jobs", type=int, default=5)
    ap.add_argument("--model", default="claude-opus-5")
    a = ap.parse_args()

    bundles = json.load(open(BUNDLES, encoding="utf-8"))
    vocab = T.build()
    prompt_path = render_prompt(vocab)
    fmt = vocab.get("format") or {}
    os.makedirs(OUTDIR, exist_ok=True)

    todo = []
    for aid, rec in bundles.items():
        if not rec["comments"]:
            continue
        if a.only and a.only.lower() not in rec["name"].lower():
            continue
        if not a.force and os.path.exists(os.path.join(OUTDIR, f"{aid}.json")):
            continue
        todo.append((aid, rec))

    if not todo:
        print("nothing to do — every judge already has a summary (--force to redo)")
        return 0
    print(f"writing {len(todo)} summaries with {a.model}, {a.jobs} at a time")
    print(f"  format read from the tab: {fmt.get('format_line', 'unknown')}"
          f" ({fmt.get('teams_in_debate', '?')} teams in a debate)\n")

    failed = []
    with cf.ThreadPoolExecutor(a.jobs) as ex:
        futs = {ex.submit(one, aid, rec, a.model, vocab, prompt_path): rec["name"]
                for aid, rec in todo}
        for i, f in enumerate(cf.as_completed(futs), 1):
            try:
                aid, name, tries, bad = f.result()
            except Exception as e:
                print(f"  [{i}/{len(todo)}] ERROR {futs[f]}: {e}")
                failed.append((futs[f], [str(e)]))
                continue
            if bad:
                print(f"  [{i}/{len(todo)}] GATE FAIL {name} after {tries} tries")
                for b in bad:
                    print("        ·", b)
                failed.append((name, bad))
            else:
                mark = "" if tries == 1 else f" (fixed on try {tries})"
                print(f"  [{i}/{len(todo)}] ok {name}{mark}")

    try:
        os.unlink(prompt_path)
    except OSError:
        pass
    print(f"\n{len(todo) - len(failed)}/{len(todo)} written to summaries/")
    if failed:
        print(f"{len(failed)} could not be written cleanly — rerun to retry:")
        for n, _ in failed:
            print("   ·", n)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
