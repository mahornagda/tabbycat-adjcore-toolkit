# Setting this up with any AI coding tool

You do not need Claude Code. Anything that can run a terminal command and read
what comes back will do this: **Claude Code**, **Claude Cowork**, **OpenAI
Codex**, **Cursor**, **Windsurf**, **Gemini CLI**, **Aider**, GitHub Copilot's
agent mode, and others.

Copy the block below and paste it in. Nothing in it is specific to one tool.

---

```
Set up the Tabbycat Adjcore Toolkit for my tournament.

It is a Python project. Do this and nothing else:

1. Clone https://github.com/REPLACE_ME/tabbycat-adjcore-toolkit and cd into it.
2. Run:  python3 run.py check      — tell me anything it says is missing.
3. Run:  python3 run.py demo       — this needs no tournament and no login.
                                     Show me the result. If it fails, stop and
                                     fix my install before going further.
4. Run:  python3 run.py setup      — it asks me three things. Let ME answer
                                     them; do not invent a tab address, a slug
                                     or a token. It prints my tournament's
                                     round and team counts at the end: show me
                                     those and ask if they look right.
5. Then tell me these three commands and what each does, and stop:
       python3 run.py testers
       python3 run.py fold
       python3 run.py feedback

Rules: the toolkit only ever reads my tab and cannot write to it, so if a step
looks like it needs to change something in Tabbycat, stop and tell me. Do not
publish anything. Do not run the feedback tool past the point where it asks me
to read the summaries.
```

---

## On Windows

Same block, but the commands are `python` rather than `python3`. Most tools work
that out on their own; if yours does not, say so and it will fix it.

## Two things to keep in that prompt

**Do not let it invent your tab address or token.** Those come from you and from
your tab's own *Change Password* page. An assistant that guesses will produce a
setup that looks finished and reads nothing.

**Do not let it publish judge feedback.** The tool deliberately stops after
writing the summaries so a person reads them before they go out under your
adjudication core's name. That stop is the feature.

## If you use Claude Code

There is a shorter way, because the repository ships a skill:

```
git clone https://github.com/REPLACE_ME/tabbycat-adjcore-toolkit
cd tabbycat-adjcore-toolkit
claude
```

then type `/setup`. See [CLAUDE-CODE.md](CLAUDE-CODE.md).

## Doing it without any of this

Three commands, written out at
[the docs' setup page](https://tabbycat-adjcore-toolkit.pages.dev/start/#self),
with the Windows, macOS and Linux versions of each.
