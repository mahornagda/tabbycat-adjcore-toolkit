---
name: setup
description: Set up the Adjcore Toolkit for a tournament — check prerequisites, prove the install works against the built-in fake Tabbycat, collect the tab details, write the config, connect read-only, run the chosen tools and optionally publish them. Use when the user has just cloned this repo, types /setup, or asks to point the toolkit at their tournament.
---

# Setting up the Adjcore Toolkit

You are setting this repository up for one specific tournament. The person you
are talking to is on an adjudication core. Assume they are comfortable with a
terminal but are not a developer, and that they are probably doing this the
week of their tournament with other things on their mind.

## Two rules that matter more than speed

**Prove the install before you touch their tab.** There is a fake Tabbycat in
`demo/`. Run everything against that first. If something is broken — a missing
Python package, a wrong Python version — you find it there, where nothing is at
stake, rather than in a confusing error against their live tournament.

**Never write to their tab, and never suggest anything that could.** The whole
toolkit is read-only by construction. If a step seems to need a write, stop and
say so; do not work around it.

## Step 1 — prerequisites

Check and report, in one message, rather than one at a time:

- `python3 --version` — 3.9 or newer.
- `python3 -c "import requests"` — if it fails, `python3 -m pip install requests`.
- Only if they want the feedback tool: `claude --version`. That tool shells out
  to the Claude Code CLI to write the summaries.
- Only if they want to publish the fold or feedback publicly:
  `npx wrangler --version` (Cloudflare, recommended) or `npx netlify --version`.
  Do not install anything yet; `npx` fetches on first use.

If something is missing, give them the one command that fixes it and wait.

## Step 2 — prove it works, with no tournament involved

```
python3 demo/verify.py --quick
```

This runs all three tools against three invented tournaments. It needs no
credentials and reaches no network. Show them the summary lines — it is also the
clearest explanation of what the tools do.

If they want to see the browser tests too, drop `--quick`; it needs Playwright
(`python3 -m pip install playwright && python3 -m playwright install chromium`)
and takes a few minutes. It is optional.

## Step 3 — ask for the tournament

Ask these together, in one message, not one at a time. Explain briefly where
each comes from:

1. **Their tab's web address** — everything before the tournament name, e.g.
   `https://theirtournament.calicotab.com`. No trailing slash, no `/admin`.
2. **The tab slug** — the tournament's own bit of the address. If their tab is
   at `https://x.calicotab.com/openx26/`, the slug is `openx26`.
3. **How to sign in.** Offer the token first, because it is better for them:

   > Tabbycat gives every user an API token. It is on your tab's home page under
   > **Change Password**. A token is safer to hand to a tool than your password,
   > because you can revoke just the token from that same page.

   Ask for the token if they can find it, and for their username and password
   otherwise. Then tell them the one caveat: Tabbycat's feedback-progress and
   check-in views are ordinary admin pages rather than API endpoints, so a token
   alone leaves two columns of tester tracking blank. If they want those, they
   need a username and password as well as the token — both can go in `.env`.

   Either way, say plainly that it must be an adjudication-core or tabulation
   account: a public or participant account cannot see feedback, panels or an
   unreleased draw, which is most of what these tools read. Tell them it goes
   into `.env`, which is gitignored, and that you will not echo it back.
4. **Which of the three tools they want** — tester tracking, the fold and its
   simulator, judge feedback. Any combination. Tester tracking is the usual
   place to start.
5. **Only if they picked the fold or feedback:** whether they want those
   published publicly, and what to call the sites. The names become the web
   addresses, e.g. `openx26-fold.pages.dev`, so they should be recognisable.

There is deliberately nothing to ask about round counts, break categories, panel
sizes or format. All of that is read from their tab. If they offer it anyway,
tell them they do not need to and why.

## Step 4 — write the config

Copy `tournament.example.json` to `tournament.json` and fill in what they gave
you. Leave `tournament.name` empty unless they asked for a specific display
name — the pages take the name from the tab, which is one less thing to get
wrong.

Write `.env` from `.env.example` with their login, then `chmod 600 .env`.

Never put the password in `tournament.json`. Never print it back to them.

## Step 5 — connect, read-only, and show them what came back

```
set -a; . .env; set +a
cd tester-tracking && python3 pull.py
```

Then report what it found, because this is their chance to catch a wrong slug
before anything else runs: the tournament name, how many rounds and which are
break rounds, the break categories and their sizes, how many teams and judges,
how many teams are in a debate. If any of that looks wrong to them, it is almost
always the slug.

Common failures and what they actually mean:

| What they see | What it is |
|---|---|
| `403 Forbidden` | The login worked but the account is not tab-side. They need adjudication-core or tabulation access. |
| `404` on an API path | Wrong slug. |
| `did not look like a Tabbycat login page` | The url points at a tournament path or a front page rather than the site root. |
| `Tabbycat did not accept that login` | Wrong username or password, or they gave a private URL instead. |
| `401` with a token set | The token is wrong or has been revoked. Re-read it from the tab's home page, under Change Password. |
| feedback progress / check-ins `skipped` | Expected on a token alone. Add `TABBY_USER` and `TABBY_PASS` to fill those two columns. |

## Step 6 — run what they picked

**Tester tracking** — `cd tester-tracking && ./start`, then open the address it
prints. Tell them the judges who count as testers come from Tabbycat's own
"adjudication core" flag, and they can add more people from inside the
dashboard. Point them at the Testing tab first; it is the one worth their time.

**The fold** — `cd fold && ./refresh --dry` first. That builds the page and runs
the gate checks without publishing anything, so they can open
`fold/dist/index.html` and look at it. Only then `./refresh` to publish. Show
them the "results shown for" and "panels shown for" lines: those come from their
tab's own public switches, and if something is on the page that they did not
expect to be public, the fix is in Tabbycat, not here.

**Judge feedback** — this one has a review step and it is not optional:

```
cd feedback
./pull.py --stats          # what written feedback exists
./bundle.py               # replace every name with a placeholder
./summarise.py            # write the summaries (slow — a few minutes)
./review                  # read them yourself, in a browser
./refresh --dry           # build and re-run every check
./refresh                 # publish
```

Tell them clearly: `summarise.py` writes to `summaries/*.json`, they are meant
to read a few and can hand-edit any of them, and `build.py` never regenerates
what they edited. Also tell them `feedback/data/` holds every adjudicator's
private URL key and should be deleted when the tournament is over.

## Step 7 — hand it over

End with a short list they can act on: the addresses of anything published, the
one command to re-run each tool, and the two warnings — `feedback/data/` is
credential material, and `.env` must never be committed.

Do not offer to set up a scheduled job unless they ask. If they do, the fold's
`./refresh` is safe to run repeatedly and is the only one worth automating.
