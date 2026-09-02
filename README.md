# Tabbycat Adjcore Toolkit

Three tools an adjudication core can run on its own tournament, built on top of
Tabbycat. They read your tab; none of them can write to it.

> **Not affiliated with Tabbycat.** Tabbycat is a separate project by other
> people; this is a set of tools that reads a Tabbycat tab and never writes to
> one. All credit for the tab itself belongs to
> [the Tabbycat team](https://github.com/TabbycatDebate/tabbycat).

**Docs, with a walkthrough of each one: https://tabbycat-adjcore-toolkit.pages.dev**
**Try them first — live samples, invented tournament, no setup:**
[tester tracking](https://tabbycat-adjcore-toolkit.pages.dev/samples/tester-tracking/) ·
[the fold simulator](https://tabbycat-adjcore-toolkit.pages.dev/samples/fold/) ·
[judge feedback](https://tabbycat-adjcore-toolkit.pages.dev/samples/feedback/)

---

## What the three tools do

**Tester tracking** — who on your judge pool has actually been watched, and by
whom. A judge counts as tested when one of your testers sits on their panel, and
that is worked out from the live draw rather than typed into a spreadsheet twice.
It records the position the tested judge held — chair, panellist or trainee — and
shows you the remaining gaps: who has never been seen, who has chaired but never
been watched chairing, who is cleared for a break-round chair. Runs on your
laptop; there is an optional hosted version so a whole adjcore shares one view.

**The fold, and the fold simulator** — a public page for spectators, built
strictly from what your tab has already made public. It shows the points stack
folding into the break, the break itself, and the break-round bracket. The
simulator lets anybody click who they think goes through and watch the next
round re-form. Picks stay in their own browser and are never sent anywhere.

**Judge feedback** — every written comment about a judge, consolidated by an AI
into one coherent read they can act on, published to a private page only that
judge can reach. No scores, no round names, no team names, no quoted phrases,
nothing that says which debate anything came from. Two independent mechanisms
enforce that, and a human reviews everything before it is sent.

## Who this is for

Adjudication cores and tab teams. All three tools need a **tab-side login** —
adjudication core or tabulation — because feedback, panels and unreleased draws
are not visible to anyone else. If you do not have tab access at your
tournament, these will not work for you, and that is deliberate.

## Getting started

One command does everything, and it works the same on Windows, macOS and Linux.
Use `python` instead of `python3` on Windows.

```
git clone https://github.com/mahornagda/tabbycat-adjcore-toolkit
cd tabbycat-adjcore-toolkit
python3 -m pip install requests

python3 run.py check      # have I got what I need?
python3 run.py demo       # try all three tools on a tournament that does not exist
python3 run.py setup      # point it at yours — asks three things
```

Then:

```
python3 run.py testers    # who has been watched, and who still needs to be
python3 run.py fold       # the public page, built and opened for you to check
python3 run.py feedback   # consolidated judge feedback, with a stop for you to read it
```

**Do the demo first.** There is a fake Tabbycat built in, so all three tools run
before you have a tab address, a token, or permission from anyone. If that
works, any later problem is about your tournament rather than your laptop.

**Or let an AI tool do it.** One paste block, works with Claude Code, Cowork,
Codex, Cursor, Gemini CLI and the rest —
[automation/ANY-AI-TOOL.md](automation/ANY-AI-TOOL.md). Claude Code users can
clone, run `claude`, and type `/setup`.

## Nothing about your tournament is configured

You edit one file, `tournament.json`, and it holds your tab's address, your tab
slug, and what you want the published sites called. That is all.

Everything about the *shape* of your tournament is read from Tabbycat every time
a tool runs: the number of rounds, which are prelims and which are break rounds,
your break categories and their sizes and names, how many teams are in a debate,
your side names, your feedback scale, your panel sizes, and every public /
silent / released switch. Change any of them mid-tournament and the tools
follow. `demo/verify.py` exists to prove that rather than assert it.

Credentials go in `.env`, never in `tournament.json`, so the config file stays
safe to commit and to paste into a chat when you want help.

## Read-only by construction

The Tabbycat client in `core/tabread.py` subclasses `requests.Session` and
raises on any verb that is not GET, HEAD or OPTIONS, before a packet leaves the
machine. There is no write method to call and no flag that turns one on. The
only POST in the whole toolkit is the Django login form, and it runs on a
separate session that is closed immediately.

You can check that in a minute, and you may need to in order to get an account:

```
python3 tests/test_release.py
```

Among other things that asserts, by parsing every file rather than grepping it,
that nothing outside the login form can write to a tab.

## What it will not do

- The fold needs a complete, announced break that divides evenly into rooms.
  Partial breaks, byes and partial double-octofinals produce no projection.
- The hosted version of tester tracking runs on Netlify functions. The local
  version is the one to start with.
- Judge feedback shells out to the `claude` command-line tool, so that needs to
  be installed.
- Nothing here generates a draw, allocates judges, or touches a ballot. Tabbycat
  does all of that, and these tools stay out of its way.

## Layout

```
core/              the one read-only Tabbycat client, config, world country data
tester-tracking/   the adjcore dashboard          (local; cloud/ is optional)
fold/              the public fold + simulator    (publishes a static site)
feedback/          consolidated judge feedback    (publishes a static site)
demo/              a fake Tabbycat, three invented tournaments, the verifier
docs/              the documentation site
automation/        the Claude Code setup path
tests/             checks that need no tournament and no credentials
```

## Licence and credit

MIT. Built by Mahor Nagda. Tabbycat is a separate project and this is not
affiliated with it — all credit for the tab itself belongs to the Tabbycat team.
