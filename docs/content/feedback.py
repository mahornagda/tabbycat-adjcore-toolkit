import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from annotate import figure, Pin

PAGE = {
    "title": "Consolidated judge feedback",
    "lede": "Every written comment about a judge, turned into one coherent read "
            "they can act on, on a page only they can reach. No scores, no "
            "round names, no teams, no quoted phrases — and a person reads it "
            "all before it goes anywhere.",
    "body": f"""
<div class="btnrow">
  <a class="btn" href="../samples/feedback/">Open the sample</a>
  <a class="btn ghost" href="../start/#manual">How to run it</a>
</div>

<h2>The problem it solves</h2>

<p>At the end of a tournament, a judge has a dozen comments written about them
and no way to read them. Handing over the raw comments is not an option — a
distinctive turn of phrase identifies its author inside a panel of three, and
half the comments are arguing with a decision rather than describing the
judging. So in practice the comments sit in the tab, and the judge learns
nothing.</p>

<p>What a judge actually wants is what a good adjudication core member would tell
them over coffee: here is the pattern across everything people said, here is what
came through strongly, here is the thing to work on. That is a summarising job,
and it is the kind of summarising a language model is genuinely good at.</p>

<p>The whole design is about making it safe to do that.</p>

<h2>What a judge sees</h2>

{figure("fb-summary.png",
        caption="One judge's page. Reached only by their own private URL — "
                "there is no index, no search, and no way to get to anybody "
                "else's.",
        pins=[
    Pin(0.20, 0.09, "Their name, and nothing else's", "Names live inside the file, never in its address.", to=(0.265, 0.128)),
    Pin(0.60, 0.09, "The promise, stated on the page", "Consolidated, anonymous, no scores. A judge should know what they are "
        "reading before they read it.", to=(0.51, 0.128)),
    Pin(0.19, 0.225, "One read, not a list of comments", "The pattern across everything written, with the weight of repetition "
        "behind it — “several people”, “one person”, never a count.", to=(0.265, 0.26)),
    Pin(0.74, 0.44, "Honest about disagreement",
        "Where comments genuinely pulled in opposite directions it says so, "
        "rather than averaging a real split into mush.",
        to=(0.66, 0.435)),
    Pin(0.20, 0.588, "What came through strongly", "Specific enough to be worth reading. Vague praise helps nobody.", to=(0.265, 0.588)),
    Pin(0.20, 0.948, "What to work on", "Phrased as something to do differently, not just something that was "
        "wrong.", to=(0.265, 0.948)),
])}

<h2>The rules, and where they came from</h2>

<p>These are not stylistic preferences. Each one traces to a specific thing that
would go wrong without it, and a draft that breaks one is thrown away rather than
softened.</p>

<table>
  <thead><tr><th>Rule</th><th>Why</th></tr></thead>
  <tbody>
    <tr><td><b>No scores. No digits at all.</b></td>
        <td>Not a feedback score, not an average, not a rank, and not a count of
        how many people wrote in — because “three people said” is a score with
        the numerals taken out. Banning every digit kills scores, round numbers
        and counts in one stroke.</td></tr>
    <tr><td><b>Nothing that says which debate it came from.</b></td>
        <td>Comments argue with a call and quote the motion to do it. Repeat any
        of that and the judge can identify the round, and from the round the
        panel, and from the panel the author. No round or stage names, no motion,
        no topic, no argument content, no country.</td></tr>
    <tr><td><b>Nothing from or about the teams and panels.</b></td>
        <td>No team, school or person named. And no attribution at all — not “a
        team felt”, not “your chair said”. Saying whether a comment came from a
        team or a co-panellist narrows it to one of three people.</td></tr>
    <tr><td><b>Never quote. Always paraphrase.</b></td>
        <td>A distinctive phrase names its author more reliably than a signature.
        No run of words is reused from any source comment.</td></tr>
    <tr><td><b>A person reads it before it is sent.</b></td>
        <td>This goes out under your adjudication core's name. See
        <a href="#review">the review step</a>.</td></tr>
  </tbody>
</table>

<p>What is deliberately <em>allowed</em> matters just as much. Generic craft
vocabulary stays legal — the comparative, the bench, deliberation, the opening
half — because banning it strips out the feedback worth reading and leaves
platitudes. And that vocabulary is chosen from your format: British
Parliamentary words would be nonsense at a two-team tournament, so which set is
in play is read from your tab.</p>

<h2>How those rules are kept</h2>

<p>Two separate things, because relying on either alone would be a bad idea.</p>

<ol class="steps">
  <li><b>Names are taken out before the AI ever sees a comment</b>
  <p>Every person, team, school and round in the comments is swapped for
  <code>[a person]</code>, <code>[a team]</code>, <code>[a round]</code> first.
  It cannot repeat a name it was never given.</p></li>

  <li><b>Every draft is checked, and rewritten if it fails</b>
  <p>Each summary is read against every rule above. If something slips through,
  the exact problem is handed back and it writes it again — up to four times. So
  a leak is not something you have to spot by eye.</p>
  <p>On the demo tournament, 18 of 37 summaries needed at least one correction.
  That is not carelessness; the rules are tighter than ordinary writing, which
  is the point.</p></li>

  <li><b>And checked once more before anything is published</b>
  <p>Because you are allowed to edit the summaries by hand, and a hand-edit can
  break a rule just as easily. If anything fails, nothing publishes.</p></li>
</ol>

<div class="tech">
  <h3>The checks <span class="techflag">Technical</span></h3>
  <p>In <code>feedback/gate.py</code>. The sharpest is <b>no digit anywhere</b>.
  Then: no score, rank or average vocabulary; no counted people — but <em>“one
  person” is allowed</em>, because that is how you honestly report a single
  view, so the ban starts at two, where a count starts behaving like a score;
  no round or stage name; no side label; no attribution verb attached to a team
  or a panellist; no participant, team, school or code; no country or city; and
  <b>no seven-word run shared with any source comment</b>.</p>
  <p>The vocabulary is built from your tab, not typed in — every name, team,
  school, code, round name and motion is pulled and turned into a ban list. Two
  things that list needs care with, both of which cost real time to learn:</p>
  <ul>
    <li><b>A short upper-case round abbreviation must match
    case-sensitively.</b> A grand final abbreviated <code>OF</code>, matched
    case-insensitively, turns every “of” in every comment into
    <code>[a round]</code>.</li>
    <li><b>A name that is also an ordinary English word must stay legal on its
    own.</b> Someone surnamed Long is why “long-winded” must not become “[a
    person] winded”. Full names and adjacent name pairs always match; the lone
    token gets an escape hatch.</li>
  </ul>
  <p>Motion words get the same treatment, and this is the part that had to be
  rebuilt to make the tool portable. Banning every word that appeared in a
  motion is safe and useless: motions are made almost entirely of ordinary
  English, so it bans “work”, “land”, “large” and “individual”, and you cannot
  write about judging without those. The test is therefore whether the word is
  <em>distinctive</em> — checked against a frequency list of common English, which
  is a property of the language rather than of one tournament. On the demo's
  motions that leaves eleven banned terms, all of them the kind of word that
  would identify a round.</p>
  <p>Break-category names get an escape hatch for the same reason. A category
  called <b>Open</b> must not ban the word “open”, or no summary can say “open
  to persuasion”. A category called <b>Novice</b> or <b>ESL</b> is distinctive
  and stays banned.</p>
</div>

<h2 id="access">Who can read whose</h2>

<p>A judge reaches their page with the private link Tabbycat already gave them —
the same one they use to submit ballots and feedback. Nothing else opens it.</p>

<ul>
  <li>There is <b>no list, no search and no index</b>. Having the site tells you
  nothing about who is on it.</li>
  <li>The site holds <b>no private links</b> of its own, so a copy of it is not
  a set of keys.</li>
  <li>Names are <b>inside</b> the pages, never in their web addresses.</li>
  <li>You send each judge one link. That is the only way in.</li>
</ul>

<div class="tech">
  <p><span class="techflag">Technical</span> The file is
  <code>sha256(url_key).json</code>, hashed in the reader's browser, and the
  content security policy is <code>connect-src 'self'</code>. The check that
  earned its keep fastest: the build refuses to publish if any private URL key
  appears anywhere in the output — and it caught one immediately, because the
  first version of a code comment explaining the URL format used a real judge's
  key as the example.</p>
</div>

<h2 id="review">The step you should not skip</h2>

<div class="note stop">
  <p><b><code>./review</code> exists because a person has to read this.</b> The
  summaries are ordinary files in <code>feedback/summaries/</code>. Open some.
  Edit any of them by hand — the build never regenerates what you have edited.
  Then publish.</p>
  <p>Everything else here is machinery for making the output safe to read. It
  cannot make the output <em>right</em>, and this is judge feedback going out
  under your adjudication core's name.</p>
</div>

<h2>When almost nothing was written</h2>

<p>A judge with two comments does not get a paragraph of pattern-finding invented
out of two lines. They get a short, plainly-worded note saying little was
written. On the demo tournament that is 7 judges of 37; the threshold is in
<code>tournament.json</code> and three is a sensible floor.</p>

<p>Inflating thin feedback is worse than admitting it is thin, because a judge
who is told a confident story about themselves from two comments will believe
it.</p>

<h2>What is deliberately absent</h2>

<ul>
  <li><b>The “did you agree with the decision?” answers.</b> An agreement rate is
  a score by another name.</li>
  <li><b>Any count of how many people wrote in.</b> Also a score.</li>
  <li><b>Any way to look up somebody else.</b> No index, no search, by design.</li>
  <li><b>Any automation.</b> This is written once, read by a person, then sent.
  There is no scheduled job and there should not be.</li>
</ul>

<div class="tech">
  <h3>How the model is called <span class="techflag">Technical</span></h3>
  <p><code>summarise.py</code> shells out to the <code>claude</code> CLI with
  tools disabled, slash commands disabled, dynamic system-prompt sections
  excluded, and its working directory in a temporary folder — a pure text
  transform with no tools, no skills and no project context, because anything
  else is a route for something unrelated to end up in a judge's feedback.</p>
  <p><code>prompt.md</code> is the whole instruction set and is meant to be
  edited. Three values in it are filled in from your tournament at run time: the
  format, the craft vocabulary that format uses, and the side labels to avoid.
  Everything else is prose you can rewrite to suit your own adjudication core's
  voice.</p>
</div>

<hr>
<p><a href="../how-it-works/">Next: how it all works underneath &rarr;</a></p>
""",
}
