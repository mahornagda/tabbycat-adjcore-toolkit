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
  <a class="btn" href="../samples/fold/">See it on a real tournament</a>
  <a class="btn ghost" href="../samples/fold/#sim">Go straight to the simulator</a>
</div>

<div class="note">
  <p><b>That sample is a real tournament</b> — a 110-team intervarsity, with its
  real teams, real break and real speaker tab. Not because we were careless with
  somebody's data: because <em>everything this page can show was already public
  on that tournament's own Tabbycat</em>, so the honest demo is the real thing.
  If that claim is wrong the whole tool is wrong, and you can check it — open the
  <b>What's shown</b> tab on the sample and it lists, switch by switch, what the
  tab has released and what it has not.</p>
  <p>The other two tools' samples are invented, because those two publish things
  no tab makes public.</p>
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

<h2 id="judges">The judges</h2>

<p>Names, and what each of them actually did: how many rooms, how many as chair,
as panellist, as trainee. Click any judge and you get their round-by-round — the
position they held, the teams in the room, and who sat alongside them.</p>

{figure("fold-judges.png",
        caption="Every judge, and what they did. All of it from the tab's own "
                "results pages.",
        pins=[
    Pin(0.72, 0.375, "What each of them actually did",
        "Rooms, chairs, panels and trainee sits — counted from the results, "
        "not typed in anywhere.", to=(0.74, 0.432)),
    Pin(0.33, 0.395, "Who broke",
        "Shown only where your tab has published the adjudicator break.",
        to=(0.22, 0.472)),
    Pin(0.06, 0.60, "Click any judge",
        "Their round by round: the position they held, the teams in the room, "
        "and who sat alongside them.", to=(0.14, 0.545)),
])}

<div class="note">
  <p><b>This appears as soon as your results are public, even if your draw is
  switched off.</b> Those are two different settings in Tabbycat: the draw page
  shows who is <em>about</em> to judge whom, and the results pages show who
  <em>did</em> — with the chair and any trainee marked. Most tournaments switch
  the draw off when they finish and leave results up forever, so who judged
  stays public.</p>
  <p>Room names are the exception and follow the draw setting, because your
  tab's results pages do not carry a room column. On the sample you will see a
  dash where the room would be — that tournament's draw is off.</p>
</div>

<h2 id="speaks">The speaker tab</h2>

<p>Once a tournament releases its speaker tab, the fold shows it — and only
then. The tab appears in the navigation when Tabbycat's own
<code>speaker_tab_released</code> switch is on, and disappears again if it is
turned off.</p>

{figure("fold-speaks.png",
        caption="The speaker tab, on a tournament that has released it. Every "
                "number comes from the tab's own speaker tab; nothing is "
                "recomputed.",
        pins=[
    Pin(0.10, 0.20, "It says how far the tab goes",
        "Tabbycat lets a tournament publish only the top N. Where that is set, "
        "the list stops there and the page says so rather than looking "
        "truncated by accident.", to=(0.14, 0.245)),
    Pin(0.60, 0.20, "Anonymous speakers keep their scores",
        "A speaker the tab marks anonymous is shown without a name. The ranks "
        "stay continuous and nothing is invented.", to=(0.62, 0.245)),
    Pin(0.87, 0.20, "Iron-person speeches are counted out",
        "Tabbycat excludes them from the average, so this does too — and marks "
        "them, so a short speech count has a visible reason.", to=(0.83, 0.245)),
    Pin(0.20, 0.47, "Round by round, per speaker",
        "Each speech, in round order, with an asterisk on the ones that do not "
        "count toward the average.", to=(0.72, 0.47)),
])}

<div class="note warn">
  <p><b>Three of Tabbycat's rules here are obeyed, not reimplemented</b>, because
  each is a decision the tournament made and not ours to second-guess: the
  <code>anonymous</code> flag on a speaker, the tab limit, and the exclusion of
  iron-person speeches from an average.</p>
  <p>And three things are <em>not</em> published even when the speaker tab is:
  <b>reply speeches</b>, the <b>adjudicator tab</b>, and any <b>ballot or
  margin</b>. The first two have their own release switches in Tabbycat, and
  releasing the speaker tab does not release them — conflating those would
  publish something a tournament deliberately held back.</p>
</div>

<div class="tech">
  <h3>What this cost, and what replaced it</h3>
  <p>The gate's sharpest check used to be <b>no float anywhere in the
  payload</b>. Speaks and feedback averages are floats in Tabbycat while points
  and counts are integers, so any float at all was evidence that something
  score-shaped had got in — whatever it was named, and wherever it came from.
  That is a much stronger check than trying to enumerate the fields you do not
  want.</p>
  <p>Publishing a released speaker tab means floats are now legitimate. So the
  check was narrowed rather than deleted: no float outside
  <code>speaker_scores[].total|avg|stdev</code>,
  <code>speaker_scores[].by_round[][].score</code> and
  <code>standings[].speaks</code>. Everywhere else the tell still works.</p>
  <p>Two more checks were added alongside it, because a switch that is off has
  to be provable: when <code>speaker_tab_released</code> is off there must be no
  <code>speaker_scores</code> key at all — not an empty one, absent — and when
  it is on, no row marked anonymous may carry a name, and no rank may exceed the
  published limit. The demo tournaments cover both states, and the one whose tab
  is closed exists specifically so the off-path is tested rather than
  assumed.</p>
  <p>The pull is careful in one more way. A Tabbycat speaker record carries an
  email, a phone number, a barcode and a <code>url_key</code> — which <em>is</em>
  that person's private ballot URL. So the pull takes the name, the team and the
  anonymous flag, and leaves the rest in the response object it never stores.</p>
</div>

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

<h2 id="gate">How it decides what to show</h2>

<p>It reads your tab's own settings, every time it builds. Not a copy of them
made once — the live values.</p>

<ul>
  <li><b>Rankings</b> need results public, the round finished, and the round not
  silent.</li>
  <li><b>Who judged</b> travels with the rankings, because your tab's own
  results pages carry the panel.</li>
  <li><b>Room names</b> and unreleased draws need the public draw switched
  on.</li>
  <li><b>The break</b> needs breaking teams public.</li>
  <li><b>A motion</b> needs public motions, and that round's motions
  released.</li>
  <li><b>The speaker tab</b> needs the speaker tab released. Team speaks need
  the team tab. Replies and the adjudicator tab have their own switches and are
  never shown.</li>
</ul>

<p>So the page follows your tab. Switch something off in Tabbycat and it comes
off the page at the next refresh — and if something is on the page you did not
expect to be public, the fix is in Tabbycat, not here.</p>

<p>You do not have to take that on trust. Open <b>What's shown</b> on any page
this builds and it lists, setting by setting, what your tab has released and
what it has not.</p>

<div class="note">
  <p><b>And it refuses to publish if a check fails.</b> Not a warning — it
  stops. So a mistake in the page cannot quietly reach the internet.</p>
</div>

<div class="tech">
  <h3>The two mechanisms, and why one would not do</h3>
  <p>The rules above stop the wrong <em>values</em>. They cannot stop a wrong
  <em>field</em> — one extra key added in a hurry, carrying something private.
  So every key that may appear in the published data is declared in
  <code>fold/gate.py</code>, and the build walks what it is about to publish and
  raises on anything undeclared. A new field cannot leak by accident; somebody
  has to declare it, which means somebody has to think about it.</p>
  <p>That allowlist also enforces shape, which it did not originally: a field
  declared as holding a scalar is checked to be one. A declaration of "a list of
  names" once waved through a list of whole participant records — emails and
  private URL keys included — and reported the payload clean.</p>
  <p><code>fold/tests/test_gate.py</code> is the deploy gate, and its sharpest
  check is about floats: speaks are floats in Tabbycat while points and counts
  are integers, so a float outside the four declared speaker fields is the tell
  that something score-shaped has got in, whatever it is named. The others:
  per-round points only for rounds whose rankings are public; every points value
  inside this format's scale, read from teams-per-debate rather than assumed to
  be 3/2/1/0; no room name outside the draw-public rounds and no panel outside
  the results-public ones; silent rounds silent; the script makes no network
  call; the only outside references are the font host and your own tab.</p>
</div>

<div class="tech">
<h3>Two failures, and the guards that came out of them</h3>

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

</div>

<div class="note">
  <p><b>On the sample, “Round by round” is empty, and that is the tool working.</b>
  That tournament has finished and has since switched its public draw off, so
  there are no rooms or panels to show. The fold does not cache what a tab used
  to allow.</p>
</div>

<h2>Publishing it</h2>

<p>The whole site is one static HTML file plus a headers file. That is a
deliberate constraint rather than an aesthetic one: a break announcement is the
one moment a tournament page gets hammered, and a single file on a static host
does not fall over.</p>

<p>Cloudflare Pages is the default because it is unmetered on bandwidth. Netlify
and surge are also supported — one word in <code>tournament.json</code>.</p>

<div class="note warn">
  <p><b>Use a host that does not charge for bandwidth.</b> Cloudflare Pages is
  the default here and is free for this. A break announcement is the one moment
  your page gets hammered, and a metered host can cut you off exactly then.</p>
</div>

<div class="tech">
  <h3>Why that warning is there</h3>
  <p>A free tier ran out of bandwidth credits mid-tournament and refused every
  deploy for eighteen hours, freezing the live page on a stale build right
  through a break-round draw going out. Worse, that provider's own quota endpoint
  reported plenty of credit remaining while refusing every deploy — so a quota
  reading is not evidence. Post a deploy and read the error.</p>
</div>

<hr>
<p><a href="../feedback/">Next: consolidated judge feedback &rarr;</a></p>
""",
}
