import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from annotate import figure, Pin

PAGE = {
    "title": "The fold, and the simulator",
    "lede": "A public page for everyone who is not on the adjudication core: "
            "the points stack folding into the break, the break itself, the "
            "break-round bracket — and a simulator where anybody can play out "
            "the rest of the tournament themselves.",
    "body": f"""
<div class="btnrow">
  <a class="btn" href="../samples/fold/">Open the sample</a>
  <a class="btn ghost" href="../samples/fold/#sim">Go straight to the simulator</a>
</div>

<h2>The problem it solves</h2>

<p>Between the last prelim and the break announcement, a few hundred people all
want the same thing: to work out who is breaking. They do it on paper, badly, in
a hallway, and then argue about it. And once the break rounds start, nobody
outside the room can follow which room feeds which — so the bracket exists only
in the heads of the people who drew it.</p>

<p>Both of those are just a rendering problem. The tab already knows everything
required; it is simply not shown that way. This is that page.</p>

<div class="note">
  <p><b>It shows only what your tab has already made public.</b> Not “the parts
  we judged safe” — literally the switches you have already set in Tabbycat. If
  results are not public, they are not on the page. If a round is silent, it
  stays silent. If the draw is not released, the rooms are empty. Turning
  something on in Tabbycat turns it on here at the next refresh, and nowhere
  else. See <a href="#gate">how that is enforced</a>.</p>
</div>

<h2>The fold</h2>

{figure("fold-stack.png",
        caption="Every team stacked by points, with the break line cut across "
                "it. This is the page people actually want between the last "
                "prelim and the announcement.",
        pins=[
    Pin(0.33, 0.183, "What your tab is currently saying", "The round in play, whether its draw is out, whether its rankings are "
        "public. Read from the tab, not asserted by us.", to=(0.325, 0.232)),
    Pin(0.145, 0.405, "Break categories come from the tab", "Their names, their sizes and how many there are. Nothing here knows "
        "what your categories are called.", to=(0.152, 0.446)),
    Pin(0.36, 0.405, "Scrub back through the tournament",
        "How the fold looked after any earlier round. Useful for the argument "
        "about who would have broken if.",
        to=(0.31, 0.447)),
    Pin(0.565, 0.515, "The team on the line", "Named, with the points total that got them there — which is the first "
        "thing anyone asks.", to=(0.525, 0.562)),
    Pin(0.055, 0.665, "One row per points total", "Grouped by bracket rather than listed 1 to 48, because that is how a "
        "break is actually read.", to=(0.098, 0.695)),
])}

<div class="note warn">
  <p><b>A sub-category's break line is not the top N of its own stack.</b> This
  caught us out live. If two teams eligible for a sub-category break the main
  category instead, they are marked as such and sit <em>above</em> the
  sub-category's line — so cutting after the first N positions strands the last
  teams that genuinely broke. The line is drawn after the last team that
  actually broke, and the page says so: “8 teams, with 2 above the line out of
  this break”. The demo tournament reproduces the condition on purpose, so the
  fix stays tested.</p>
</div>

<h2>The break rounds</h2>

<p>The bracket, drawn so you can see which room feeds which. Two things about it
are worth stating plainly, because getting either wrong makes a correct bracket
look broken:</p>

<ul>
  <li><b>Rooms fold, they do not pair off with their neighbour.</b> With
  <em>P</em> rooms in a break round, room <em>i</em> meets room
  <em>P+1&minus;i</em>. So with eight octofinal rooms it is 1+8, 2+7, 3+6, 4+5 —
  not 1+2, 3+4.</li>
  <li><b>The fold happens once, at the break, and nothing is re-seeded
  afterwards.</b> Survivors keep their break seed and follow a fixed tree. This
  is the part people most often assume works the other way.</li>
</ul>

<p>Which means everything past the first break round is genuinely knowable in
shape and genuinely unknowable in occupants — so the shape is drawn and the
rooms stay empty until the round before has been debated.</p>

<h2>The simulator</h2>

{figure("fold-sim.png",
        caption="Run your own break. Pick who goes through and the next round "
                "re-forms — following the same fixed tree the real rounds do.",
        pins=[
    Pin(0.062, 0.545, "The first round is folded off the break", "Room 1 takes seeds 1, 8, 9 and 16 here. The rule is derived from the "
        "break size and how many teams are in a debate, so it reads correctly "
        "for a two-team break too.", to=(0.098, 0.578)),
    Pin(0.113, 0.44, "This round is already decided", "Where a result is public, the simulator locks it to what actually "
        "happened rather than letting you re-run history.", to=(0.113, 0.474)),
    Pin(0.318, 0.44, "This one is yours to pick", "Per room, not per round — ballots land one room at a time, so a "
        "half-decided round shows its results and stays pickable elsewhere.", to=(0.318, 0.474)),
    Pin(0.35, 0.685, "Room 1 meets room 4, not room 2",
        "Four quarterfinal rooms, so room i meets room P+1−i. The lines are "
        "drawn so no connector crosses another.",
        to=(0.268, 0.715)),
    Pin(0.735, 0.905, "Honest about what it cannot know yet", "“Waiting on OSF rooms 1 and 2” rather than a blank box or a guess.", to=(0.63, 0.945)),
    Pin(0.845, 0.33, "Chalk, Surprise me, Share, Clear", "Share produces a link that encodes your picks. Nothing is sent "
        "anywhere; it is all in the address.", to=(0.845, 0.372)),
])}

<p>The simulator is a separate tab from the real bracket on purpose. One is your
adjudication core's answer and the other is a spectator's guess, and those should
never be a click apart from looking like the same thing.</p>

<div class="tech">
  <h3>Picks never leave the browser <span class="techflag">Technical</span></h3>
  <p>Picks live in <code>localStorage</code> and in a
  <code>#sim=&lt;slug&gt;.&lt;digits&gt;</code> fragment. A URL fragment is
  never sent to a server, so a shared bracket is shared peer-to-peer through
  whatever you pasted the link into. The share code is <b>fixed width</b> — one
  character per seat, <code>x</code> for unpicked — because a variable-width
  code let a half-finished round shift every later digit by one, and a shared
  link decoded into somebody else's bracket.</p>
  <p>The page makes no network requests at all after it loads, and the test
  suite asserts that: it checks the inlined script contains no
  <code>fetch</code>, <code>WebSocket</code> or <code>XMLHttpRequest</code>.
  It keeps itself current by <em>navigating</em> — a full reload once the page
  is five minutes old, and only when nothing is open, the tab is visible, and
  nobody has typed for two minutes — which is why the “makes no requests” claim
  and the content security policy both still hold.</p>
</div>

<h2 id="gate">How “only what is public” is enforced</h2>

<p>Two independent mechanisms, because one would not be enough to trust.</p>

<ol class="steps">
  <li><b>Rules, re-read every build</b>
  <p>One module decides what a spectator may see, and it reads your tab's own
  preferences every time rather than remembering them. Rankings need results
  public <em>and</em> the round finished <em>and</em> the round not silent. Rooms
  and panels need the draw released and your public-draw setting to permit it.
  The break needs breaking teams to be public. A motion needs public motions
  and that round's motions released.</p>
  <p>So the page follows your tab rather than tracking it. Turn something off in
  Tabbycat and it comes off the page on the next refresh.</p></li>

  <li><b>An allowlist, checked against the finished page</b>
  <p>Rules stop the wrong values. They cannot stop a wrong <em>field</em> — one
  extra key added in a hurry, carrying something private. So every key that may
  appear in the published data is declared, and the build walks what it is about
  to publish and refuses anything undeclared. A new field cannot leak by
  accident; it has to be declared, which means somebody has to think about
  it.</p></li>

  <li><b>And the checks are the deploy gate</b>
  <p><code>./refresh</code> will not publish a build that fails them. Not warn —
  refuse.</p></li>
</ol>

<div class="tech">
  <h3>The sharpest check is “no float anywhere” <span class="techflag">Technical</span></h3>
  <p>Speaker scores and feedback averages are floats in Tabbycat. Points and
  counts are integers. So a float anywhere in the published payload is the tell
  that something score-shaped has got in, wherever it came from and whatever it
  is called — a much better check than trying to enumerate the fields you do not
  want.</p>
  <p>The others: per-round points exist only for rounds whose rankings are
  public; every points value is inside this format's scale, read from
  teams-per-debate rather than assumed to be 3/2/1/0; no room name or panel
  outside the rounds whose draw is public; silent rounds are silent; the script
  makes no network call; the only outside references are the font host and your
  own tab. See <code>fold/gate.py</code> and
  <code>fold/tests/test_gate.py</code>.</p>
</div>

<h2>Two failures that taught us something</h2>

<p>Both of these happened live, and both are now guarded, which is more useful
to you than a claim that nothing goes wrong.</p>

<div class="note stop">
  <p><b>An empty break is a real state, so it must never be inferred from a
  failure.</b> A transient error on the break endpoint was being swallowed and
  returning “no break”, so the site published “the break has not been announced”
  over a break that had been out for a day. No error, no log line — the page
  just forgot who broke.</p>
  <p>Now: the endpoint is retried and then raises; and separately the build
  compares against the previous pull and refuses to publish a category that had
  ranked teams and now has none. The retry alone cannot catch it, because a
  successful response with an empty body looks exactly like “not announced
  yet”.</p>
</div>

<div class="note stop">
  <p><b>“Results are public” is not the same as “the result is in”.</b> A round
  was un-silenced before a single ballot was confirmed. The page read the flag,
  concluded the round was decided, locked the simulator, and left every later
  round waiting forever.</p>
  <p>Now the ballots decide, not the flag — and per room, because ballots land
  one room at a time. A decided room shows its result while its neighbours stay
  pickable.</p>
</div>

<h2>Publishing it</h2>

<p>The whole site is one static HTML file plus a headers file. That is a
deliberate constraint rather than an aesthetic one: a break announcement is the
one moment a tournament page gets hammered, and a single file on a static host
does not fall over.</p>

<p>Cloudflare Pages is the default because it is unmetered on bandwidth. Netlify
and surge are also supported — one word in <code>tournament.json</code>.</p>

<div class="note warn">
  <p><b>We learned that the hard way.</b> A free hosting tier ran out of
  bandwidth credits mid-tournament and refused every deploy for eighteen hours,
  freezing the live page on a stale build right through a break-round draw going
  out. Worse, the same provider's own quota endpoint reported plenty of credit
  remaining while refusing every deploy — so do not trust a quota reading, and do
  pick a host that does not meter bandwidth.</p>
</div>

<hr>
<p><a href="../feedback/">Next: consolidated judge feedback &rarr;</a></p>
""",
}
