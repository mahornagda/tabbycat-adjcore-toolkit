DIAGRAM = """
<figure class="fig">
<div class="fig-frame" style="padding:18px;line-height:1.4">
<svg viewBox="0 0 880 330" width="100%" style="max-width:880px;height:auto"
     role="img" aria-label="Your Tabbycat feeds one read-only client, which feeds
     three tools: tester tracking produces a local dashboard, the fold produces a
     public page, and the feedback tool produces one private page per judge.">
  <defs>
    <marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6"
            markerHeight="6" orient="auto-start-reverse">
      <path d="M0 0 L10 5 L0 10 z" fill="var(--line-2)"/>
    </marker>
    <style>
      .bx{fill:var(--panel);stroke:var(--line-2);stroke-width:1.5;rx:9}
      .bx.core{stroke:var(--accent);stroke-width:2}
      .bx.out{fill:var(--panel-2);stroke-dasharray:4 3}
      .t{font:600 13px 'Inter Tight',system-ui,sans-serif;fill:var(--ink)}
      .s{font:11.5px 'Inter Tight',system-ui,sans-serif;fill:var(--dim)}
      .m{font:500 11px 'JetBrains Mono',monospace;fill:var(--faint)}
      .ln{stroke:var(--line-2);stroke-width:1.5;fill:none;marker-end:url(#ar)}
      .lbl{font:11px 'Inter Tight',system-ui,sans-serif;fill:var(--faint)}
    </style>
  </defs>

  <rect class="bx" x="8" y="128" width="150" height="74"/>
  <text class="t" x="83" y="156" text-anchor="middle">Your Tabbycat</text>
  <text class="s" x="83" y="176" text-anchor="middle">the only source</text>
  <text class="m" x="83" y="192" text-anchor="middle">read, never written</text>

  <path class="ln" d="M160 165 H 232"/>
  <text class="lbl" x="196" y="158" text-anchor="middle">GET only</text>

  <rect class="bx core" x="234" y="118" width="150" height="94"/>
  <text class="t" x="309" y="146" text-anchor="middle">One client</text>
  <text class="m" x="309" y="165" text-anchor="middle">core/tabread.py</text>
  <text class="s" x="309" y="184" text-anchor="middle">refuses any verb</text>
  <text class="s" x="309" y="199" text-anchor="middle">that is not a read</text>

  <path class="ln" d="M386 145 H 452"/>
  <path class="ln" d="M386 165 H 452"/>
  <path class="ln" d="M386 185 H 452"/>

  <rect class="bx" x="454" y="18" width="176" height="76"/>
  <text class="t" x="542" y="44" text-anchor="middle">Tester tracking</text>
  <text class="s" x="542" y="63" text-anchor="middle">derives who has been</text>
  <text class="s" x="542" y="78" text-anchor="middle">watched, from the draw</text>

  <rect class="bx" x="454" y="127" width="176" height="76"/>
  <text class="t" x="542" y="153" text-anchor="middle">The fold</text>
  <text class="s" x="542" y="172" text-anchor="middle">rules + allowlist decide</text>
  <text class="s" x="542" y="187" text-anchor="middle">what a spectator sees</text>

  <rect class="bx" x="454" y="236" width="176" height="82"/>
  <text class="t" x="542" y="262" text-anchor="middle">Judge feedback</text>
  <text class="s" x="542" y="281" text-anchor="middle">mask &rarr; model &rarr; gate</text>
  <text class="s" x="542" y="296" text-anchor="middle">&rarr; redraft &rarr; a person</text>

  <path class="ln" d="M632 56 H 700"/>
  <path class="ln" d="M632 165 H 700"/>
  <path class="ln" d="M632 277 H 700"/>

  <rect class="bx out" x="702" y="24" width="170" height="64"/>
  <text class="t" x="787" y="49" text-anchor="middle">Your laptop</text>
  <text class="s" x="787" y="68" text-anchor="middle">nothing published</text>

  <rect class="bx out" x="702" y="133" width="170" height="64"/>
  <text class="t" x="787" y="158" text-anchor="middle">A public page</text>
  <text class="s" x="787" y="177" text-anchor="middle">one static file</text>

  <rect class="bx out" x="702" y="245" width="170" height="64"/>
  <text class="t" x="787" y="270" text-anchor="middle">One page per judge</text>
  <text class="s" x="787" y="289" text-anchor="middle">reachable only by them</text>
</svg>
</div>
<figcaption>Everything comes from one place and goes through one client. The
three tools never talk to each other, and none of them writes anything
back.</figcaption>
</figure>
"""

PAGE = {
    "title": "How it all works",
    "lede": "The architecture, the two guarantees worth checking rather than "
            "believing, and exactly which parts of your tournament are read "
            "from the tab rather than configured.",
    "body": f"""
{DIAGRAM}

<h2>Why the three tools do not know about each other</h2>

<p>They share a Tabbycat client and nothing else. No shared database, no shared
state, no tool reading another's output. That separation is doing real work.</p>

<p>The clearest example: the fold's public page is built directly from the tab
and <b>never</b> reads any private draft of a break-round draw. So a room that
has not been drawn yet is genuinely empty on the public page, rather than merely
hidden — there is nothing there to leak. Wiring the tools together would make
that a matter of care instead of a matter of fact.</p>

<h2 id="readonly">The read-only guarantee</h2>

<p>One file talks to Tabbycat. It subclasses the HTTP session class and overrides
the single method every request funnels through, raising on anything that is not
a read, before a packet leaves the machine.</p>

<pre><code>SAFE = {{"GET", "HEAD", "OPTIONS"}}

class _GetOnlySession(requests.Session):
    def request(self, method, url, *a, **kw):
        if str(method).upper() not in SAFE:
            raise ReadOnlyViolation(...)
        return super().request(method, url, *a, **kw)</code></pre>

<p>There is no write function in the toolkit to call and no setting that enables
one. The single POST anywhere is the sign-in form, and it runs on a separate,
throwaway session that is closed immediately; only its cookies are carried into
the read-only client.</p>

<p>You do not have to take that on faith, and if you are asking a tab director
for an account you should not:</p>

<pre><code>python3 tests/test_release.py</code></pre>

<div class="tech">
  <p><span class="techflag">Technical</span> That suite parses every Python file
  with <code>ast</code> and asserts no call to
  <code>.post/.patch/.put/.delete</code> exists outside the sign-in form —
  parsing rather than grepping, specifically so the docstring that explains the
  guarantee does not itself trip the check. It also instantiates the session and
  asserts each write verb raises, and asserts the class has no
  <code>write</code> attribute at all.</p>
  <p>This was a real change made for release. The feedback tool used to use a
  second client that <em>did</em> have a write method — publishing a
  “read-only by construction” toolkit with a writable client inside it would have
  been a lie, so the two were collapsed into one and the write path deleted.</p>
</div>

<h2 id="derived">What is read from your tab, and what you configure</h2>

<p>You configure four things. Everything else is read, every run.</p>

<div class="cards">
  <div class="card">
    <h3>You configure</h3>
    <ul>
      <li>your tab's web address</li>
      <li>your tab slug</li>
      <li>what to call any published site</li>
      <li>your token (in <code>.env</code>, separately)</li>
    </ul>
  </div>
  <div class="card">
    <h3>Read from the tab</h3>
    <ul>
      <li>the tournament's name</li>
      <li>how many rounds, and which are break rounds</li>
      <li>break categories: names, sizes, how many</li>
      <li>teams per debate, speakers per team, side names</li>
      <li>panel sizes, per round</li>
      <li>the feedback scale, and which question is written</li>
      <li>every public / silent / released switch</li>
      <li>motions, institutions, regions</li>
      <li>who is on the adjudication core</li>
    </ul>
  </div>
</div>

<p>This is the claim most worth being suspicious of, because almost every tool
like this is quietly bound to the tournament it was written at. So the repository
ships the means to check it rather than an assurance:</p>

<pre><code>$ python3 demo/verify.py

Riverbend Open 2027         4 teams a debate · 9 prelims · 5 elim rounds · 2 categories
Ashfield Invitational 2027  2 teams a debate · 5 prelims · 3 elim rounds · 1 category
Kestrel Bay Novice Cup      4 teams a debate · 4 prelims · break not announced

Every tool ran against every tournament with no code changed.</code></pre>

<div class="tech">
  <h3>The three shapes are chosen to break things <span class="techflag">Technical</span></h3>
  <ul>
    <li><b>A sub-category break line that is not the top N.</b> Teams eligible
    for the second category break the general one instead, so the second
    category's line falls below its own top eight.</li>
    <li><b>A two-team format.</b> Points are 1/0 rather than 3/2/1/0, the side
    codes are <code>aff</code>/<code>neg</code> rather than the four benches, and
    British Parliamentary craft vocabulary would read as nonsense.</li>
    <li><b>A break that has not been announced.</b> Every bracket and simulator
    view has to render an empty state rather than an error — and the test suite
    has to report those checks as <em>not applicable</em> rather than failed, or
    it cries wolf at anyone who runs it before their break.</li>
    <li><b>Panels that change size mid-tournament</b>, because that is normal and
    a configured panel size would be wrong from round two.</li>
    <li><b>A half-decided break round</b>, where some rooms have ballots in and
    some do not.</li>
  </ul>
  <p>Building this found real bugs, which is the argument for it. Among them: a
  guard that compared the current break against the previous pull without
  checking it was the <em>same tournament</em>, so pointing the tool at a second
  tab refused to publish; six test assertions hardcoded to one tournament's team
  count, break size and round names; and a break count that reported the whole
  eligible field as having broken.</p>
</div>

<h2>The pattern that shows up twice: two mechanisms, not one</h2>

<p>Both the fold and the feedback tool protect something, and both do it the same
way — because one mechanism is never enough to trust.</p>

<table>
  <thead><tr><th></th><th>The cheap fix</th><th>The proof</th></tr></thead>
  <tbody>
    <tr><td><b>The fold</b></td>
        <td>Rules read from your tab's own switches decide what may be shown</td>
        <td>An allowlist declares every permitted field, and the build refuses
        anything undeclared</td></tr>
    <tr><td><b>Judge feedback</b></td>
        <td>Names are masked out before the model sees a comment</td>
        <td>A gate checks every draft and redrafts; and runs again at build
        time, because a hand-edit leaks just as easily</td></tr>
  </tbody>
</table>

<p>In both cases the second mechanism is a <em>deploy gate</em>, not a warning.
The refresh script will not publish a build that fails it. That distinction is
the difference between a check and a habit.</p>

<h2 id="failures">Failures are made loud on purpose</h2>

<p>The most dangerous bug in a tool like this is not a crash. It is a soft
failure that produces a plausible page.</p>

<p>A transient error on one endpoint was once being swallowed and treated as an
empty result — so the public site announced that a break had not happened, over a
break that had been out for a day. No error, no log line. Both of the things that
fixed it are now general principles here:</p>

<ul>
  <li><b>An empty result that is also a real state must never be inferred from a
  failure.</b> “No break yet” is a true state before the break, which is exactly
  why it may not be guessed at.</li>
  <li><b>Compare against the last known good.</b> A successful response with an
  empty body is indistinguishable from “not announced”, so retrying cannot catch
  it; only noticing that something used to be there can.</li>
</ul>

<h2>Extending it</h2>

<p>The things most likely to want changing, and where they are:</p>

<table>
  <thead><tr><th>To change</th><th>Edit</th></tr></thead>
  <tbody>
    <tr><td>What the feedback summaries say and sound like</td>
        <td><code>feedback/prompt.md</code> — the whole instruction set, meant
        to be edited</td></tr>
    <tr><td>What the feedback gate allows</td>
        <td><code>feedback/gate.py</code>, and the common-word list in
        <code>core/common_english.py</code> if an ordinary word is being
        banned</td></tr>
    <tr><td>What the public page may show</td>
        <td><code>fold/gate.py</code> — add the field to the allowlist
        deliberately, which is the point of it</td></tr>
    <tr><td>Who counts as a tester</td>
        <td>the dashboard itself; the default is Tabbycat's adjudication-core
        flag</td></tr>
    <tr><td>A country missing a flag</td>
        <td><code>core/countries.py</code>, then re-run
        <code>core/gen_flags.py</code> — one source feeds both the flags and the
        feedback ban list</td></tr>
    <tr><td>Anything at all</td>
        <td>add a shape to <code>demo/shapes/</code> that exercises it, and
        <code>demo/verify.py</code> will keep you honest</td></tr>
  </tbody>
</table>

<hr>
<p><a href="../limits/">Next: what it will not do &rarr;</a></p>
""",
}
