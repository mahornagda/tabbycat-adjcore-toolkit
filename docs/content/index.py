PAGE = {
    "title": "Three tools for an adjudication core",
    "lede": "Tester tracking, a public fold with a bracket simulator, and "
            "AI-consolidated judge feedback. They sit on top of Tabbycat, they "
            "read your tab and cannot write to it, and nothing about your "
            "tournament is written into them.",
    "body": """
<div class="btnrow">
  <a class="btn" href="./start/">Set it up</a>
  <a class="btn ghost" href="./samples/fold/">See a sample first</a>
  <a class="btn ghost" href="https://github.com/REPLACE_ME/tabbycat-adjcore-toolkit">Code on GitHub</a>
</div>

<div class="note">
  <p><b>Two ways to read this site.</b> The switch at the top right says
  <b>Plain</b> or <b>Technical</b>. Plain is enough to install everything and
  run it at your tournament. Technical adds how each part actually works —
  the data model, the checks, the API — for anyone who wants to change
  something or satisfy themselves it is safe. It is the same pages either way,
  so you can flip between them without losing your place.</p>
</div>

<div class="note warn">
  <p><b>Not affiliated with Tabbycat.</b> Tabbycat is a separate project by
  other people, and all credit for the tab itself belongs to
  <a href="https://github.com/TabbycatDebate/tabbycat">its team</a>. This is a
  set of tools that reads a Tabbycat tab and never writes to one. The name says
  Tabbycat because that is what it reads, not because they endorse it.</p>
</div>

<h2>The three tools</h2>

<div class="cards">
  <div class="card">
    <span class="pill">Runs on your laptop</span>
    <h3>Tester tracking</h3>
    <p>Who in your judge pool has actually been watched, by whom, and in which
    position. Worked out from the live draw rather than typed into a
    spreadsheet twice — so it is never out of date and never disagrees with
    the tab.</p>
    <p class="go"><a href="./tester-tracking/">How it works</a> ·
       <a href="./samples/tester-tracking/">Sample</a></p>
  </div>
  <div class="card">
    <span class="pill p">A public web page</span>
    <h3>The fold, and the simulator</h3>
    <p>The points stack folding into the break, the break itself, the
    break-round bracket, and the speaker tab once you release it — all built
    strictly from what your tab has already made public. Spectators can click
    who they think goes through and watch the next round re-form.</p>
    <p class="go"><a href="./fold/">How it works</a> ·
       <a href="./samples/fold/">Sample</a></p>
  </div>
  <div class="card">
    <span class="pill g">Private, one page per judge</span>
    <h3>Consolidated judge feedback</h3>
    <p>Every written comment about a judge turned into one coherent read they
    can act on. No scores, no round names, no teams, no quoted phrases,
    nothing that says which debate anything came from — and a person reviews
    it all before it goes out.</p>
    <p class="go"><a href="./feedback/">How it works</a> ·
       <a href="./samples/feedback/">Sample</a></p>
  </div>
</div>

<h2>Who it is for, and who it is not for</h2>

<p>Adjudication cores and tab teams. All three tools need a <b>tab-side
login</b> — adjudication core or tabulation — because feedback, panels and
unreleased draws simply are not visible to anybody else. If you do not have tab
access at your tournament, these will not work for you.</p>

<p>That is a deliberate limit rather than an oversight. Two of these tools read
things that are private until an adjudication core decides otherwise, and the
third publishes judge feedback. Both of those are the CAP's to hold.</p>

<div class="note warn">
  <p><b>You will probably have to ask someone for an account.</b> The page on
  <a href="./access/">getting access to your tab</a> is written partly so you
  can send it to your tab director: it explains exactly what these tools read,
  and why they cannot write anything, in terms you can point at.</p>
</div>

<h2>Try them before you install anything</h2>

<p>Nothing to set up — just open them.</p>

<p><b>The fold's sample is a real tournament</b>, because everything that page
can show was already public on that tournament's own Tabbycat. The other two
run on an invented tournament, with invented teams, judges and feedback,
because those two publish things no tab makes public.</p>

<div class="cards">
  <div class="card">
    <h3><a href="./samples/tester-tracking/">Tester tracking &rarr;</a></h3>
    <p>Open the <b>Testing</b> tab. That is the one that matters.</p>
  </div>
  <div class="card">
    <h3><a href="./samples/fold/">The fold &rarr;</a></h3>
    <p>A real 110-team intervarsity. Try the <b>Simulator</b> tab and pick some
    winners, then the <b>Speaker tab</b>.</p>
  </div>
  <div class="card">
    <h3><a href="./samples/feedback/">Judge feedback &rarr;</a></h3>
    <p>Three keys are offered at the bottom of the page.</p>
  </div>
</div>

<p>If you would rather run them yourself, there is a fake Tabbycat in the
repository, so you can put all three through their paces on your own machine
before you point anything at a real tab. See
<a href="./start/#demo">try it without your tournament</a>.</p>

<h2>Nothing about your tournament is configured</h2>

<p>You fill in one file. It holds your tab's web address, your tab slug, and
what you want any published pages called. That is the whole of it.</p>

<p>Everything about the <em>shape</em> of your tournament is read from Tabbycat
every time a tool runs — how many rounds you have, which are prelims and which
are break rounds, your break categories and their sizes and names, how many
teams are in a debate, your side names, your feedback scale, your panel sizes,
and every public / silent / released switch. Change any of it mid-tournament
and the tools follow on the next run.</p>

<p>That claim is worth being suspicious of, so the repository ships the means to
check it: three deliberately different invented tournaments and one command that
runs all three tools against all three. See
<a href="./how-it-works/#derived">what is read and what is configured</a>.</p>

<div class="tech">
  <h3>What that looks like in practice <span class="techflag">Technical</span></h3>
  <pre><code>$ python3 demo/verify.py --quick

Riverbend Open 2027        4 teams a debate · 9 prelims · 5 elim rounds · 2 break categories
Ashfield Invitational 2027 2 teams a debate · 5 prelims · 3 elim rounds · 1 break category
Kestrel Bay Novice Cup     4 teams a debate · 4 prelims · break not announced

Every tool ran against every tournament with no code changed.</code></pre>
  <p>The three shapes are chosen to break things: one has a sub-category whose
  break line does not fall at the top N of the points stack, one is a two-team
  format where British Parliamentary vocabulary would be nonsense, and one has
  no break yet, so every bracket view has to render an empty state rather than
  an error.</p>
</div>

<h2>Read-only, and not just as a promise</h2>

<p>The one piece of code that talks to Tabbycat refuses any request that is not
a read, before it leaves your machine. There is no function in the toolkit that
writes to a tab, and no setting that turns one on. The single exception is the
login form, which is how you sign in at all.</p>

<div class="tech">
  <p><span class="techflag">Technical</span> <code>core/tabread.py</code>
  subclasses <code>requests.Session</code> and overrides
  <code>request()</code>, the method every call in the library funnels through,
  raising <code>ReadOnlyViolation</code> on anything outside
  <code>{GET, HEAD, OPTIONS}</code>. The login POST runs on a separate,
  throwaway session that is closed immediately; only its cookies are carried
  into the read-only client. <code>tests/test_release.py</code> asserts this by
  parsing every Python file in the repository for calls to
  <code>.post/.patch/.put/.delete</code> — parsing rather than grepping, so
  that the docstring which explains the guarantee does not itself trip the
  check.</p>
</div>

<hr>

<h2>Everything on this site</h2>

<div class="map">
  <section>
    <h4>Running it</h4>
    <ul>
      <li><a href="./start/">Set it up</a> — the whole install, both ways</li>
      <li><a href="./start/#claude">With Claude Code</a> — paste one thing</li>
      <li><a href="./start/#manual">By hand</a> — the commands</li>
      <li><a href="./start/#demo">Without your tournament</a> — the demo</li>
      <li><a href="./start/#trouble">When it goes wrong</a></li>
    </ul>
  </section>
  <section>
    <h4>Your tab</h4>
    <ul>
      <li><a href="./access/">Getting access</a> — and why there is no API key</li>
      <li><a href="./access/#ask">What to send your TD</a></li>
      <li><a href="./access/#urlkeys">The private-URL warning</a></li>
    </ul>
  </section>
  <section>
    <h4>The three tools</h4>
    <ul>
      <li><a href="./tester-tracking/">Tester tracking</a></li>
      <li><a href="./fold/">The fold and the simulator</a></li>
      <li><a href="./feedback/">Consolidated judge feedback</a></li>
    </ul>
  </section>
  <section>
    <h4>Underneath</h4>
    <ul>
      <li><a href="./how-it-works/">How it all works</a></li>
      <li><a href="./how-it-works/#derived">Read vs configured</a></li>
      <li><a href="./how-it-works/#readonly">The read-only guarantee</a></li>
      <li><a href="./limits/">What it will not do</a></li>
    </ul>
  </section>
  <section>
    <h4>Samples</h4>
    <ul>
      <li><a href="./samples/tester-tracking/">Tester tracking</a></li>
      <li><a href="./samples/fold/">The fold</a></li>
      <li><a href="./samples/feedback/">Judge feedback</a></li>
    </ul>
  </section>
  <section>
    <h4>Code</h4>
    <ul>
      <li><a href="https://github.com/REPLACE_ME/tabbycat-adjcore-toolkit">The repository</a></li>
      <li><a href="https://github.com/REPLACE_ME/tabbycat-adjcore-toolkit/blob/main/automation/CLAUDE-CODE.md">The Claude Code doc</a></li>
      <li><a href="https://github.com/REPLACE_ME/tabbycat-adjcore-toolkit/issues">Report a problem</a></li>
    </ul>
  </section>
</div>
""",
}
