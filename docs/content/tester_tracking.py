import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from annotate import figure, Pin

PAGE = {
    "title": "Tester tracking",
    "lede": "Who in your judge pool has actually been watched, by whom, and in "
            "which position — worked out from the live draw rather than typed "
            "into a spreadsheet twice.",
    "body": f"""
<div class="btnrow">
  <a class="btn" href="../samples/tester-tracking/">Open the sample</a>
  <a class="btn ghost" href="../start/#manual">How to run it</a>
</div>

<h2>The problem it solves</h2>

<p>By the end of the prelims you have to decide who chairs a break round. To do
that honestly you need to know which judges somebody trusted has actually sat
with — and in what position, because watching someone panel tells you much less
than watching them chair.</p>

<p>Most adjudication cores track this in a spreadsheet, filled in from memory
between rounds. It goes wrong in the same three ways every time: it drifts out of
step with the draw, nobody updates it during the round when they are busy, and
it records “tested” without recording <em>as what</em>.</p>

<p>This tool takes the position that none of that should be typed at all. A judge
has been tested when one of your testers sat on their panel — and the tab already
knows who sat on which panel. So it is derived, every time it refreshes, and it
cannot disagree with the draw.</p>

<h2>What you look at</h2>

{figure("tt-testing.png",
        caption="The Testing tab. Everything on it is worked out from the draw; "
                "nothing here was entered by hand.",
        pins=[
    Pin(0.10, 0.165, "The four numbers that matter", "Never tested, seen but not chairing, seen chairing, and how many "
        "testers you have. This is the whole state of your pool in one line.", to=(0.11, 0.205)),
    Pin(0.28, 0.305, "Who to test next",
        "Not a list of everybody — the remaining gaps, ordered so the top of "
        "the list is where a tester is worth spending.",
        to=(0.13, 0.283)),
    Pin(0.60, 0.40, "Why each one is a gap", "“Chaired unwatched” means they have chaired real debates that nobody "
        "was in the room for. That is a different problem from never having "
        "been seen at all.", to=(0.60, 0.462)),
    Pin(0.42, 0.40, "Tested as what", "Chair, panellist or trainee — the position the tested judge held, not "
        "the tester's.", to=(0.42, 0.462)),
    Pin(0.945, 0.40, "A note against a name", "Free text, saved beside the tab and never written back to it.", to=(0.912, 0.462)),
])}

<p>The distinction the second and third pins are making is the point of the whole
thing. “We have seen them” is not a single fact. A judge a tester has watched
panel is a candidate for another panel; a judge who has been chairing all
tournament with nobody in the room is an unanswered question, and quite a
different one from a judge nobody has sat with at all.</p>

{figure("tt-coverage.png",
        caption="Coverage, round by round. One row per judge, one column per "
                "round, and the letter is the position they were seen in.",
        pins=[
    Pin(0.30, 0.105, "Seen chairing", "A tester was on this panel and this judge was the chair.", to=(0.30, 0.152)),
    Pin(0.897, 0.126, "Trainee counts",
        "An early version only recognised chair and panellist, and so told "
        "judges nobody had sat with them when somebody had. Trainee is a real "
        "tested-as state.",
        to=(0.90, 0.16)),
    Pin(0.045, 0.355, "A dot is not a dash", "A dot means they judged and no tester was there. A dash means they "
        "were not allocated. Collapsing those two loses the thing you are "
        "looking for.", to=(0.275, 0.393)),
    Pin(0.545, 0.548, "Testers come from the tab", "Anyone flagged as adjudication core is a tester automatically, so this "
        "is right before you touch it.", to=(0.487, 0.585)),
    Pin(0.33, 0.808, "…and you can add more", "If your testers are not all on the core. Stored beside the tab, never "
        "written into it.", to=(0.255, 0.84)),
])}

<h2>How “tested” is decided</h2>

<p>One sentence: <b>a judge counts as tested in a round when at least one tester
was on their panel in that round, and the recorded position is the one the tested
judge held.</b></p>

<p>Two consequences worth knowing, because both have surprised people:</p>

<ul>
  <li><b>Testers sitting with each other does not count.</b> Two adjudication
  core members on a panel are not testing one another, so neither gets a mark.</li>
  <li><b>It is per round, not per tournament.</b> A judge can be seen chairing in
  one round and panelling in another, and both are recorded; the summary uses the
  strongest position anybody has actually watched.</li>
</ul>

<div class="tech">
  <h3>The derivation <span class="techflag">Technical</span></h3>
  <p>In <code>tester-tracking/pull.py</code>, after the draws are read, every
  judge's panel for every round is known as a list of judge ids. For each
  judge-in-a-round, the testers on that panel are
  <code>[x for x in sit["with"] if x in testers and x != aid]</code>; if that is
  non-empty and the judge is not themselves a tester, a test event is recorded
  carrying the round, the position, and who witnessed it.</p>
  <p>The tester set is <code>{{a["id"] for a in adjs if a["adj_core"]}}</code>
  unioned with anyone added in the dashboard. The additions live in
  <code>adjcore_state.json</code> beside the tab — deliberately outside
  Tabbycat, because the toolkit does not write to a tab, and because “who we are
  using as a tester this weekend” is not a fact about the tournament.</p>
  <p>Panel size is read per round from the draw rather than configured, which
  matters more than it sounds: a tournament that runs panels of two in round one
  and three thereafter is completely normal, and the demo reproduces it.</p>
</div>

<h2>What else is in there</h2>

<p>Four other tabs, all supporting material for the same decision:</p>

<table>
  <thead><tr><th>Tab</th><th>What it is for</th></tr></thead>
  <tbody>
    <tr><td><b>Right now</b></td><td>The round in play, its draw status, who has
        checked in, what is outstanding. A glance before a briefing.</td></tr>
    <tr><td><b>Judges</b></td><td>The whole pool as a table — rating, rounds
        judged, chaired, feedback received, conflicts. Sortable, for when you
        want to answer a question this tool did not anticipate.</td></tr>
    <tr><td><b>Outrounds</b></td><td>How many break-round rooms each category
        needs and therefore how many chairs you have to be confident about.
        Derived from break size and teams per debate.</td></tr>
    <tr><td><b>Feedback</b></td><td>What has been written about each judge, and
        who still owes feedback. Needs a username and password as well as a
        token — see <a href="../access/#both">why</a>.</td></tr>
  </tbody>
</table>

<h2>Where it runs</h2>

<p>On your laptop. <code>./start</code> and open the address it prints. Nothing
is published, nothing is shared, and it works on a hotel wifi that cannot reach
much.</p>

<p>There is also a hosted version in <code>tester-tracking/cloud/</code>, for an
adjudication core who want one shared view rather than one per laptop. It runs on
Netlify functions and needs its own setup; start with the local one.</p>

<div class="note warn">
  <p><b>An honest note about the hosted version.</b> It works, but it is the
  least exercised part of this toolkit — it has not been run against a live
  tournament as recently as the rest. If you want a shared view, budget an hour
  and try it before your tournament rather than during it.</p>
</div>

<hr>
<p><a href="../fold/">Next: the fold and the simulator &rarr;</a></p>
""",
}
