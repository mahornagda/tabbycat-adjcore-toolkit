PAGE = {
    "title": "What it will not do",
    "lede": "Written before you need it rather than after. Some of these are "
            "gaps we chose, some are gaps we have not closed, and the "
            "difference is marked.",
    "body": """
<h2>Real gaps</h2>

<div class="note warn">
  <p><b>The fold needs a complete break that divides evenly into rooms.</b>
  Partial breaks, byes, and partial double-octofinals produce no projection at
  all — the page shows the announced break and the bracket stays empty rather
  than guessing.</p>
  <p>This is the biggest limitation here. If your tournament breaks 24 teams
  into a partial double-octofinal, the fold view works and the bracket
  projection does not. Everything else on the page is unaffected.</p>
</div>

<div class="note warn">
  <p><b>The hosted version of tester tracking is the least exercised part of
  this toolkit.</b> It works, and it is the right answer if a whole adjudication
  core want one shared view instead of one per laptop. But it has not been run
  against a live tournament as recently as the rest, and it runs on Netlify
  functions, which is a heavier setup than anything else here.</p>
  <p>Start with the local version. If you want the shared one, try it a week
  before your tournament, not during it.</p>
</div>

<div class="note warn">
  <p><b>A category called “Novice” costs you the word “novice”.</b> Break
  category names are banned from feedback summaries, because “the novice semis”
  places a debate as surely as “round five”. Names that are everyday English —
  Open, Main — get an exemption; distinctive ones do not. So at a tournament with
  a Novice category, a summary cannot say “a novice judge”.</p>
  <p>That is the anonymity trade being made deliberately, and it is the kind of
  thing worth knowing before it puzzles you.</p>
</div>

<h2>Things that need something installed</h2>

<ul>
  <li><b>Judge feedback needs the <code>claude</code> command-line tool</b>, because
  that is what writes the summaries. Nothing else in the toolkit uses it.</li>
  <li><b>Publishing needs a hosting account</b> — Cloudflare by default, free.
  You can skip publishing entirely and open the built pages locally.</li>
  <li><b>Windows needs WSL.</b> The scripts are shell scripts and the paths are
  POSIX. This is fixable and nobody has needed it yet.</li>
</ul>

<h2>Things it deliberately does not do</h2>

<ul>
  <li><b>It does not generate draws, allocate judges, or touch a ballot.</b>
  Tabbycat does all of that well. Anything that writes to a tab is out of scope
  by construction, not by omission.</li>
  <li><b>The feedback tool does not report an agreement rate</b>, or how many
  people wrote in. Both are scores by another name, and the whole point is that
  there are no scores.</li>
  <li><b>There is no way to look up another judge's feedback.</b> No index, no
  search, no listing.</li>
  <li><b>The feedback tool is not automated and should not be.</b> A person
  reading the summaries before they go out is a feature.</li>
  <li><b>Tester tracking does not write your tester list back to Tabbycat.</b>
  Partly because nothing here writes to a tab, and partly because “who we are
  using as a tester this weekend” is not a fact about the tournament.</li>
</ul>

<h2>Scale</h2>

<p>Tested to roughly a hundred judges, fifty teams and a couple of thousand
feedback submissions — a large intervarsity. A pull takes well under a minute.</p>

<p>Something much larger would probably work and has not been tried. The one part
that scales with judges rather than with data is writing the feedback summaries:
one model call each, several at a time, so a hundred judges is minutes rather than
seconds. If you run something on that scale and it struggles,
<a href="https://github.com/REPLACE_ME/adjcore-toolkit/issues">say so</a>.</p>

<h2>Next year</h2>

<p>Tabbycat changes, and a version bump could move a field this toolkit reads.
The demo cannot catch that, because the demo is a fake Tabbycat that will not
have changed.</p>

<p>What will happen is a clear failure rather than a quiet wrong answer: the
allowlist rejects an undeclared field, the gates refuse to publish, and pulls
raise instead of returning empty. That is by design — see
<a href="../how-it-works/#failures">failures are made loud on purpose</a>. But
budget an hour to run the demo and one dry build before your tournament rather
than on the morning of it.</p>

<hr>
<p><a href="../start/">Set it up &rarr;</a> ·
   <a href="../">Back to the start &rarr;</a></p>
""",
}
