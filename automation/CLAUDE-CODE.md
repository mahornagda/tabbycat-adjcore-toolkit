# Setting this up with Claude Code

If you have [Claude Code](https://claude.com/claude-code), you do not have to
follow the manual instructions. Clone the repo, open it, and it will do the
setup with you.

## The short version

```
git clone https://github.com/REPLACE_ME/adjcore-toolkit
cd adjcore-toolkit
claude
```

Then type:

```
/setup
```

That is it. The repo ships a `/setup` skill, so Claude already knows what this
project is and what order things happen in. It will check what you have
installed, run all three tools against a fake tournament to prove the install
works before touching your real tab, ask you six questions, write your config,
connect read-only, show you what it found so you can catch a wrong setting, and
then run whichever tools you wanted.

## If `/setup` is not available

Some setups do not pick up a repo's own skills. Paste the block below into
Claude Code instead. It says the same thing.

---

```
I have just cloned the Adjcore Toolkit — three read-only tools that sit on top of
Tabbycat for an adjudication core. Please set it up for my tournament. Read
.claude/skills/setup/SKILL.md first and follow it; if that file is missing,
follow this instead.

Work in this order and do not skip ahead:

1. Check what I have: python3 (3.9+), the requests package, and — only if I want
   the feedback tool — the claude CLI. Tell me in ONE message what is missing and
   the single command that fixes it.

2. Before touching my real tournament, prove the install works by running
   `python3 demo/verify.py --quick`. That runs all three tools against three
   invented tournaments built into demo/. No credentials, no network. Show me the
   summary.

3. Then ask me, all in one message:
     · my tab's web address (everything before the tournament name, no trailing
       slash, no /admin)
     · my tab slug (the tournament's own bit of the address)
     · how to sign in. Offer the TOKEN first — Tabbycat puts one on the tab's
       home page under "Change Password", and it is safer to hand over than a
       password because it can be revoked on its own. Fall back to my username
       and password. Tell me that Tabbycat's feedback-progress and check-in
       views are ordinary admin pages, not API endpoints, so a token alone
       leaves two columns of tester tracking blank; if I want those, I need a
       username and password as well. Either way it has to be an adjudication
       core or tabulation account, because a public account cannot see
       feedback, panels or an unreleased draw
     · which of the three tools I want: tester tracking, the fold + simulator,
       judge feedback
     · if I picked the fold or feedback, whether to publish them and what to call
       the sites

   Do NOT ask me how many rounds I have, my break categories, my panel sizes or
   my format. All of that is read from my tab, and asking would mean something is
   hardcoded that should not be.

4. Write tournament.json from tournament.example.json and .env from .env.example,
   then chmod 600 .env. The password goes in .env only, never in
   tournament.json, and do not print it back to me.

5. Connect read-only with `cd tester-tracking && python3 pull.py` and then tell me
   what came back: the tournament name, the rounds and which are break rounds, the
   break categories and sizes, the team and judge counts, how many teams are in a
   debate. This is my chance to spot a wrong slug, so show me the numbers rather
   than saying it worked.

6. Run the tools I picked. For the fold, always `./refresh --dry` first so I can
   look at fold/dist/index.html before anything is published. For feedback, stop
   after `./summarise.py` and tell me to read summaries/*.json myself — I am
   allowed to edit them and build.py will not overwrite my edits.

7. Finish with: the addresses of anything published, the one command to re-run
   each tool, and two warnings — feedback/data/ holds every adjudicator's private
   URL key and must be deleted when the tournament ends, and .env must never be
   committed.

Two hard rules throughout: this toolkit is read-only towards Tabbycat, so if any
step seems to need a write, stop and tell me rather than working around it; and
run the demo before my real tab, every time.
```

---

## What it will and will not do

It will read your tab, build pages, run the checks, and publish to your own
hosting if you ask it to.

It will not write anything to Tabbycat — it cannot, the client refuses any
request that is not a GET before it leaves your machine. It will not send your
tab password anywhere; that stays in `.env` on your laptop. And it will not
publish the feedback summaries without you reading them first, because that step
is a human one on purpose.

## Doing it by hand instead

Everything above is also written out as ordinary instructions in the docs, under
**Set it up → the manual way**. The two paths end in the same place.
