PAGE = {
    "title": "Set it up",
    "lede": "Twenty minutes, most of it waiting. You can do the whole thing by "
            "pasting one instruction into Claude Code, or by hand — both paths "
            "end in the same place, and both start by running everything "
            "against a fake tournament so you find any problem before your "
            "real one is involved.",
    "body": """
<h2 id="need">Before you start</h2>

<p>You need three things:</p>

<ul>
  <li><b>A laptop with a terminal.</b> macOS or Linux out of the box; on Windows,
  use WSL. You do not need to know much — every command on this page is one you
  copy and paste.</li>
  <li><b>Python 3.9 or newer.</b> Check with <code>python3 --version</code>. It
  is already there on macOS and almost every Linux.</li>
  <li><b>A tab-side account on your tournament's Tabbycat</b>, and its API token.
  See <a href="../access/">getting access to your tab</a> — that page is also
  written so you can forward it to whoever controls the tab.</li>
</ul>

<p>Two things you only need for particular tools:</p>

<ul>
  <li>The <b>judge feedback</b> tool writes its summaries using
  <a href="https://claude.com/claude-code">Claude Code</a>, so that needs
  installing. Nothing else uses it.</li>
  <li><b>Publishing</b> the fold or the feedback pages publicly needs a
  Cloudflare account (free, and unmetered on bandwidth, which matters more than
  you would think during a break announcement). You can skip this and just open
  the pages locally.</li>
</ul>

<h2 id="get">Get the code</h2>

<pre><code>git clone https://github.com/REPLACE_ME/tabbycat-adjcore-toolkit
cd tabbycat-adjcore-toolkit
python3 -m pip install requests</code></pre>

<p><code>requests</code> is the only thing the toolkit needs installed. Everything
else it uses comes with Python.</p>

<h2 id="demo">Try it without your tournament first</h2>

<p>Do this before anything else. The repository contains a fake Tabbycat and
three invented tournaments, so you can put all three tools through their paces
with no credentials, no network and nothing at stake:</p>

<pre><code>python3 demo/verify.py --quick</code></pre>

<p>It runs every tool against every invented tournament and tells you what came
back. Two reasons this is worth the two minutes:</p>

<ol>
  <li><b>Anything broken about your install shows up here</b>, where the error
  is about your laptop rather than tangled up with a wrong slug or a permissions
  problem on a live tab.</li>
  <li><b>It is the clearest explanation of what the tools do.</b> The three
  tournaments are deliberately different from each other — different formats,
  different round counts, different break structures, one with no break at all —
  and the same tools handle all of them without being told anything.</li>
</ol>

<p>You can also just look at the results in a browser. The
<a href="../samples/tester-tracking/">three samples</a> on this site are built
from exactly that fake tournament.</p>

<div class="tech">
  <h3>What the demo actually is <span class="techflag">Technical</span></h3>
  <p><code>demo/mocktab.py</code> is a small HTTP server that answers Tabbycat's
  URL shapes — <code>/accounts/login/</code>, <code>/api/v1/tournaments/…</code>
  with RFC 5988 <code>Link</code> pagination, and the two admin pages, served as
  HTML with a <code>window.vueData</code> global. The tools are not modified and
  know nothing about it; you point <code>TABBY_BASE</code> at it and they run
  their real code paths.</p>
  <p>It also reproduces the things that catch people out, on purpose: it 404s on
  <code>/api/v1/</code> with a trailing slash, it pages only when asked, and its
  admin routes refuse a token-only client. A mock that is more forgiving than
  the real thing hides exactly the bugs you want it to find.</p>
  <p><code>demo/generate.py</code> builds each tournament deterministically from
  a shape file, and the shapes are chosen to be awkward: a sub-category whose
  break line does not fall at the top N of the points stack; a break round that
  is only half decided; judges with nineteen comments and judges with two;
  comments containing scores, team names and quotable phrases so the feedback
  tool's masking has real work to do.</p>
</div>

<h2 id="claude">The easy way — let Claude Code do it</h2>

<p>If you have Claude Code installed, you do not have to follow the manual steps
at all:</p>

<pre><code>cd tabbycat-adjcore-toolkit
claude</code></pre>

<p>then type:</p>

<pre><code>/setup</code></pre>

<p>The repository ships that as a skill, so Claude already knows what this
project is and in what order things happen. It will check what you have
installed, run the demo to prove it works, ask you a handful of questions, write
your configuration, connect to your tab read-only, show you what it found so you
can catch a wrong setting, and then run whichever tools you wanted.</p>

<p>If <code>/setup</code> is not available in your setup, there is a block to
paste instead in
<a href="https://github.com/REPLACE_ME/tabbycat-adjcore-toolkit/blob/main/automation/CLAUDE-CODE.md">automation/CLAUDE-CODE.md</a>.
It says the same thing in longer form.</p>

<div class="note">
  <p><b>It will not skip the parts that need you.</b> The instruction tells it
  to stop and hand back at the two points where a person has to look: before
  publishing the fold, and before sending judge feedback. Those are judgement
  calls, and they stay yours.</p>
</div>

<h2 id="manual">By hand</h2>

<ol class="steps">
  <li><b>Tell it which tab to read</b>
  <pre><code>cp tournament.example.json tournament.json</code></pre>
  <p>Open <code>tournament.json</code> and fill in two things:</p>
  <pre><code>"tab": {
  "url":  "https://yourtournament.calicotab.com",
  "slug": "yourtournament"
}</code></pre>
  <p>The <b>url</b> is everything before the tournament name — no trailing
  slash, no <code>/admin</code>. The <b>slug</b> is the tournament's own bit of
  the address: if your tab is at
  <code>https://x.calicotab.com/openx26/</code> then the slug is
  <code>openx26</code>.</p>
  <p>There is deliberately nothing here about how many rounds you have, your
  break categories, your panel sizes or your format. All of that is read from
  your tab. If you find yourself looking for somewhere to put it, you are done
  already.</p></li>

  <li><b>Put your token somewhere it will not leak</b>
  <pre><code>cp .env.example .env
$EDITOR .env          # paste your token
chmod 600 .env</code></pre>
  <p>Your token is on your tab's home page under <b>Change Password</b>. It goes
  in <code>.env</code>, never in <code>tournament.json</code> — which is what
  keeps the config file safe to commit, screenshot, or paste into a chat when
  you are asking someone for help.</p>
  <p>Then load it into your shell. You will need this line in any new terminal
  window:</p>
  <pre><code>set -a; . .env; set +a</code></pre></li>

  <li><b>Check it can read your tab</b>
  <pre><code>cd tester-tracking
python3 pull.py</code></pre>
  <p>Read what it prints. This is your one chance to catch a wrong setting
  cheaply — it tells you the tournament name, how many rounds you have and which
  are break rounds, your break categories and their sizes, and how many teams
  and judges it found. If those numbers are not your tournament, it is almost
  certainly the slug.</p></li>

  <li><b>Run tester tracking</b>
  <pre><code>./start</code></pre>
  <p>Open the address it prints, and go to the <b>Testing</b> tab. That is the
  one worth your time. Everything else in the dashboard is supporting
  material.</p>
  <p>The judges who count as testers come from Tabbycat's own “adjudication
  core” flag, so it is right from the start; you can add more people from inside
  the dashboard if your testers are not all on the core.</p>
  <p><a href="../tester-tracking/">More about this tool &rarr;</a></p></li>

  <li><b>Build the fold, look at it, then publish</b>
  <pre><code>cd ../fold
./refresh --dry</code></pre>
  <p><code>--dry</code> builds the page and runs every check but publishes
  nothing, so you can open <code>fold/dist/index.html</code> and see exactly
  what spectators would. Look at the “results shown for” and “panels shown for”
  lines it prints — those come from your tab's own public switches. If something
  is on the page that you did not expect to be public, the fix is in Tabbycat,
  not here.</p>
  <p>When you are happy, add a site name to <code>tournament.json</code> and
  publish:</p>
  <pre><code>./refresh</code></pre>
  <p><a href="../fold/">More about this tool &rarr;</a></p></li>

  <li><b>Consolidate judge feedback — with a stop in the middle</b>
  <pre><code>cd ../feedback
./pull.py --stats     # what written feedback you actually have
./bundle.py           # replace every name with a placeholder
./summarise.py        # write the summaries (a few minutes)
./review              # READ THEM. In a browser.
./refresh --dry       # build, and re-run every check
./refresh             # publish</code></pre>
  <p>The <code>./review</code> step is not decoration. The summaries land in
  <code>feedback/summaries/</code> as ordinary files, you are meant to read some
  of them, and you can edit any of them by hand — the build never regenerates
  what you have edited. This is judge feedback going out under your adjudication
  core's name, and a person should have read it.</p>
  <p><a href="../feedback/">More about this tool &rarr;</a></p></li>
</ol>

<h2 id="daily">Running it during the tournament</h2>

<table>
  <thead><tr><th>Tool</th><th>How often</th><th>Command</th></tr></thead>
  <tbody>
    <tr><td>Tester tracking</td><td>Press <b>Refresh</b> in the dashboard after
        each draw goes out</td><td><code>./start</code> once, then the button</td></tr>
    <tr><td>The fold</td><td>Every few minutes, if you want it to keep itself
        current</td><td><code>./refresh</code></td></tr>
    <tr><td>Judge feedback</td><td>Once, at the end</td>
        <td>the six commands above</td></tr>
  </tbody>
</table>

<div class="tech">
  <p><span class="techflag">Technical</span> <code>fold/refresh</code> is safe
  to run on a timer and is the only one worth automating — it takes a lock so a
  scheduled run and a manual one cannot collide, and it refuses to publish a
  build that fails its checks. On macOS a <code>launchd</code> job every five
  minutes works well. Do not automate the feedback tool: the review step is the
  point.</p>
</div>

<h2 id="trouble">When it goes wrong</h2>

<table>
  <thead><tr><th>What you see</th><th>What to do</th></tr></thead>
  <tbody>
    <tr><td><code>ModuleNotFoundError: requests</code></td>
        <td><code>python3 -m pip install requests</code></td></tr>
    <tr><td><code>No way to sign in to the tab was found</code></td>
        <td>You have not loaded <code>.env</code> into this terminal. Run
        <code>set -a; . .env; set +a</code> and try again — it is per-window.</td></tr>
    <tr><td><code>I do not know which tab to read</code></td>
        <td><code>tournament.json</code> is missing or its <code>tab</code>
        section is empty.</td></tr>
    <tr><td><code>403 Forbidden</code></td>
        <td>Signed in fine, but the account is not tab-side. You need
        adjudication core or tabulation access — see
        <a href="../access/#why">why</a>.</td></tr>
    <tr><td><code>404</code> on an API path</td>
        <td>The slug. It is the part of the web address straight after the host
        name.</td></tr>
    <tr><td>The numbers do not match your tournament</td>
        <td>Also the slug. You are reading somebody else's tournament on the
        same host.</td></tr>
    <tr><td>“feedback progress skipped”</td>
        <td>Expected on a token alone. Add <code>TABBY_USER</code> and
        <code>TABBY_PASS</code> to <code>.env</code> if you want those two
        columns — see <a href="../access/#both">when you need your password</a>.</td></tr>
    <tr><td>The fold refuses to publish</td>
        <td>Read what it says. It stops rather than publishes when a check
        fails, and the message names the check. The commonest is a break that
        came back empty when the previous build had one — which is the guard
        working.</td></tr>
    <tr><td>A judge has no feedback summary</td>
        <td>Either nobody wrote anything about them, or their drafts failed the
        content rules four times. Re-run <code>./summarise.py</code>; it only
        does the ones that are missing.</td></tr>
    <tr><td>Something else</td>
        <td><a href="https://github.com/REPLACE_ME/tabbycat-adjcore-toolkit/issues">Open
        an issue</a>. Include what you ran and what it printed; do not include
        your token.</td></tr>
  </tbody>
</table>

<div class="note warn">
  <p><b>When your tournament is over,</b> delete <code>feedback/data/</code>. It
  holds every adjudicator's private URL key, and those keys are credentials —
  see <a href="../access/#urlkeys">the warning</a>.</p>
</div>

<hr>
<p><a href="../tester-tracking/">Next: what tester tracking actually does &rarr;</a></p>
""",
}
