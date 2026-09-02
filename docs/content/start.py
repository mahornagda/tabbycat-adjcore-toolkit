AGENT_PROMPT = """Set up the Tabbycat Adjcore Toolkit for my tournament.

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
to read the summaries."""

PAGE = {
    "title": "Set it up",
    "lede": "One command does everything, and it works the same on Windows, "
            "macOS and Linux. Pick whichever of these two suits you.",
    "body": f"""
<div class="pick">
  <a href="#ai">
    <span class="n">Fastest</span>
    <h3>Let an AI tool do it</h3>
    <p>Paste one block into Claude Code, Codex, Cursor, Gemini CLI, Cowork or
    anything similar. It checks your machine, proves the install works, and asks
    you three questions.</p>
    <span class="t">About five minutes &rarr;</span>
  </a>
  <a href="#self">
    <span class="n">No AI tool needed</span>
    <h3>Do it yourself</h3>
    <p>Three steps. Every one is a command you copy and paste — you do not need
    to know any Python.</p>
    <span class="t">About fifteen minutes &rarr;</span>
  </a>
</div>

<div class="note">
  <p><b>Whichever you pick, do the demo first.</b> There is a fake Tabbycat
  built in, so you can run all three tools before you have a tab address, a
  token, or permission from anyone. If it works there, any later problem is
  about your tournament and not about your laptop — which is a much easier
  thing to fix.</p>
</div>

<h2 id="ai">Let an AI tool do it</h2>

<p>Any coding assistant that can run commands will do this. Copy the block and
paste it in:</p>

<div class="copywrap"><pre><code>{AGENT_PROMPT}</code></pre></div>

<p>That works in <b>Claude Code</b>, <b>Claude Cowork</b>, <b>OpenAI Codex</b>,
<b>Cursor</b>, <b>Windsurf</b>, <b>Gemini CLI</b>, <b>Aider</b>, GitHub Copilot's
agent mode — anything that can run a terminal command and read what comes back.
Nothing in it is specific to one tool.</p>

<div class="note">
  <p><b>If you use Claude Code</b> there is a shorter way: clone the repo, run
  <code>claude</code> inside it, and type <code>/setup</code>. The repo ships
  that as a skill, so it already knows the order things happen in.</p>
</div>

<p>Two things the prompt deliberately tells it <em>not</em> to do, and you should
keep them: do not let it make up your tab address or token, and do not let it
publish judge feedback without you reading it. Both of those are yours.</p>

<h2 id="self">Do it yourself — three steps</h2>

<div class="osbar" role="group" aria-label="Your operating system">
  <button data-os="mac" aria-pressed="true">macOS</button>
  <button data-os="win" aria-pressed="false">Windows</button>
  <button data-os="linux" aria-pressed="false">Linux</button>
</div>
<p style="margin-top:6px;font-size:.92rem;color:var(--faint)">
  The commands below change to match.</p>

<ol class="steps">
  <li><b>Get it, and check your machine</b>
  <div class="os" data-os="mac linux">
  <div class="copywrap"><pre><code>git clone https://github.com/REPLACE_ME/tabbycat-adjcore-toolkit
cd tabbycat-adjcore-toolkit
python3 -m pip install requests
python3 run.py check</code></pre></div>
  <p>No <code>git</code>? Download the
  <a href="../downloads/tabbycat-adjcore-toolkit.zip">zip</a>, unzip it,
  and <code>cd</code> into the folder instead.</p>
  </div>
  <div class="os" data-os="win">
  <p>Open <b>PowerShell</b> — press the Start key, type <code>powershell</code>,
  press enter.</p>
  <div class="copywrap"><pre><code>git clone https://github.com/REPLACE_ME/tabbycat-adjcore-toolkit
cd tabbycat-adjcore-toolkit
python -m pip install requests
python run.py check</code></pre></div>
  <p>No <code>git</code> or no <code>python</code>? Get Python from
  <a href="https://www.python.org/downloads/">python.org</a> (tick <b>Add
  Python to PATH</b> in the installer), and download the
  <a href="../downloads/tabbycat-adjcore-toolkit.zip">zip</a> instead of
  cloning. You do <b>not</b> need WSL.</p>
  </div>
  <p><code>check</code> tells you in plain words whether anything is missing,
  and the one command that fixes it.</p></li>

  <li><b>Try it on a tournament that does not exist</b>
  <div class="os" data-os="mac linux">
  <div class="copywrap"><pre><code>python3 run.py demo</code></pre></div>
  </div>
  <div class="os" data-os="win">
  <div class="copywrap"><pre><code>python run.py demo</code></pre></div>
  </div>
  <p>This runs all three tools against three invented tournaments. No tab, no
  sign-in, nothing leaves your machine. It takes about a minute and it is the
  cheapest possible way to find out whether anything is wrong.</p></li>

  <li><b>Point it at your tournament</b>
  <div class="os" data-os="mac linux">
  <div class="copywrap"><pre><code>python3 run.py setup</code></pre></div>
  </div>
  <div class="os" data-os="win">
  <div class="copywrap"><pre><code>python run.py setup</code></pre></div>
  </div>
  <p>It asks three things:</p>
  <ul>
    <li><b>Your tab's web address</b> — everything before the tournament name,
    like <code>https://yourtournament.calicotab.com</code></li>
    <li><b>The tournament's bit of the address</b> — if your tab is at
    <code>https://x.calicotab.com/openx26/</code> this is <code>openx26</code></li>
    <li><b>Your API token</b> — sign in to your tab in a browser and open
    <b>Change Password</b> on the home page. It is on that page.
    (<a href="../access/">More about that, including what to tell your tab
    director.</a>)</li>
  </ul>
  <p>Then it reads your tab and prints your round count, team count, judge count
  and break categories. <b>Check those look like your tournament.</b> If they do
  not, it is almost always the slug — and you have found that out in ten seconds
  rather than an hour.</p></li>
</ol>

<p>That is the setup. Nothing about how many rounds you have, your break
categories, your panel sizes or your format — all of that is read from your tab
every time a tool runs.</p>

<h2 id="use">Then, the three tools</h2>

<div class="os" data-os="mac linux">
<pre><code>python3 run.py testers     # who has been watched, and who still needs to be
python3 run.py fold        # builds the public page and opens it for you to check
python3 run.py fold --publish
python3 run.py feedback    # consolidated judge feedback, with a stop for you to read it</code></pre>
</div>
<div class="os" data-os="win">
<pre><code>python run.py testers      # who has been watched, and who still needs to be
python run.py fold         # builds the public page and opens it for you to check
python run.py fold --publish
python run.py feedback     # consolidated judge feedback, with a stop for you to read it</code></pre>
</div>

<table>
  <thead><tr><th>Tool</th><th>When to run it</th><th>What to know</th></tr></thead>
  <tbody>
    <tr><td><a href="../tester-tracking/">Tester tracking</a></td>
        <td>After each draw goes out</td>
        <td>Opens in your browser. Go to the <b>Testing</b> tab.</td></tr>
    <tr><td><a href="../fold/">The fold</a></td>
        <td>Whenever you want the public page current</td>
        <td><code>fold</code> builds and shows you. <code>fold --publish</code>
        puts it online. It refuses to publish a page that fails its own
        checks.</td></tr>
    <tr><td><a href="../feedback/">Judge feedback</a></td>
        <td>Once, at the end</td>
        <td>It stops after writing the summaries and tells you to read them.
        That stop is the point.</td></tr>
  </tbody>
</table>

<div class="note warn">
  <p><b>Opening a new terminal window?</b> Your token is in a file called
  <code>.env</code> and each new window needs it loaded.</p>
  <div class="os" data-os="mac linux">
  <div class="copywrap"><pre><code>set -a; . .env; set +a</code></pre></div>
  </div>
  <div class="os" data-os="win">
  <div class="copywrap"><pre><code>Get-Content .env | ForEach-Object {{ if ($_ -match '^export (\\w+)=(.*)$') {{ [Environment]::SetEnvironmentVariable($Matches[1], $Matches[2]) }} }}</code></pre></div>
  </div>
  <p><code>python3 run.py check</code> will tell you if you have forgotten.</p>
</div>

<h2 id="trouble">If something goes wrong</h2>

<p>Run <code>run.py check</code> first — it catches most of it and says what to
do. Otherwise:</p>

<table>
  <thead><tr><th>What you see</th><th>What it is</th></tr></thead>
  <tbody>
    <tr><td><code>python3: command not found</code> (or <code>python</code>)</td>
        <td>On Windows use <code>python</code>, not <code>python3</code> — and
        make sure you ticked <b>Add Python to PATH</b> when installing.</td></tr>
    <tr><td><code>No module named requests</code></td>
        <td><code>python3 -m pip install requests</code></td></tr>
    <tr><td><code>No way to sign in to the tab was found</code></td>
        <td><code>.env</code> is not loaded in this window — see the box
        above.</td></tr>
    <tr><td>The numbers after <code>setup</code> are not your tournament</td>
        <td>The slug. You are reading a different tournament on the same
        host.</td></tr>
    <tr><td><code>403 Forbidden</code></td>
        <td>You signed in, but the account is not on the tab side. You need
        adjudication core or tabulation access — <a href="../access/#why">why
        that is unavoidable</a>.</td></tr>
    <tr><td>The fold refuses to publish</td>
        <td>Working as intended. It stops rather than publishing when one of its
        checks fails, and the message names the check.</td></tr>
    <tr><td>A judge has no feedback summary</td>
        <td>Either nobody wrote about them, or their drafts failed the content
        rules four times. Run <code>run.py feedback --step write</code> again;
        it only does the missing ones.</td></tr>
    <tr><td>Anything else</td>
        <td><a href="https://github.com/REPLACE_ME/tabbycat-adjcore-toolkit/issues">Open
        an issue</a> with what you ran and what it printed. Not your token.</td></tr>
  </tbody>
</table>

<div class="note warn">
  <p><b>When your tournament is over,</b> delete the <code>feedback/data</code>
  folder. It holds every adjudicator's private link, and those are credentials —
  <a href="../access/#urlkeys">why</a>.</p>
</div>

<div class="tech">
  <h3>What run.py actually does, and doing it without run.py</h3>
  <p>Nothing, beyond calling the same modules directly and printing more
  helpfully. It exists because the direct route means changing directory,
  knowing which script comes next, and running shell scripts that do not exist
  on Windows — none of which is the interesting part.</p>
  <pre><code>run.py check      prerequisites, config and whether .env is loaded
run.py demo       demo/verify.py
run.py setup      writes tournament.json and .env, then reads your tab once
run.py testers    tester-tracking/pull.py, then server.py
run.py fold       fold/build.py, then fold/tests/test_gate.py, then opens dist/
run.py feedback   feedback/{{pull,bundle,summarise,build}}.py + the gate, in order,
                  stopping after summarise so a person reads the output</code></pre>
  <p>Every one of those is runnable on its own, and the shell equivalents
  (<code>fold/refresh</code>, <code>feedback/refresh</code>,
  <code>tester-tracking/start</code>) are still there for anyone who prefers
  them. They are POSIX shell, so on Windows use <code>run.py</code>.</p>
  <p>Publishing goes through <code>npx</code> — Cloudflare Pages by default,
  Netlify and surge also supported by one word in
  <code>tournament.json</code>. That is the only step that needs Node.</p>
</div>

<hr>
<p><a href="../tester-tracking/">Next: what tester tracking actually does &rarr;</a></p>
""",
}
