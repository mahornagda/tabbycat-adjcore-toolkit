PAGE = {
    "title": "Getting access to your tab",
    "lede": "There is a key, and it is easier to find than most people expect — "
            "it is on your tab's home page. This page covers where it is, what "
            "these tools do and do not read with it, and what to say to whoever "
            "controls your tournament's tab.",
    "body": """
<div class="note">
  <p><b>The short version.</b> Sign in to your tab in a browser. Go to
  <b>Change Password</b> on the home page. Your API token is there. Copy it into
  <code>.env</code> as <code>TABBY_TOKEN</code> and you are done.</p>
</div>

<h2 id="key">Where the key is</h2>

<p>Tabbycat generates an API token for every user account automatically. From
Tabbycat's own documentation:</p>

<blockquote><p>“To grant administrator access to an application, you can give it
your token, which can be found under <em>Tokens</em> in the database or under
<em>Change Password</em> on the site home page. Each user has a token
automatically generated when registered.”</p></blockquote>

<p>The second of those is the one to use. <em>Change Password</em> is an ordinary
page that any signed-in user can open, so it works whether your tournament is
self-hosted or on a managed host — and it does not need the Edit Database area,
which managed hosts often close off to tournament accounts.</p>

<p>Prefer the token over your password, for the same reason you would prefer a
key to a lock: you can revoke a token on its own, from that same page, without
changing anything else you sign in to.</p>

<pre><code># .env
export TABBY_TOKEN=938fab3...</code></pre>

<h2 id="both">When you need your password as well</h2>

<p>Two things the toolkit reads are not part of the API. Tabbycat's
feedback-progress table and its check-in status are ordinary admin pages, and a
token authenticates the API rather than a page — so those two need your ordinary
sign-in too.</p>

<table>
  <thead><tr><th>Tool</th><th>Token alone</th><th>What you gain by adding a password</th></tr></thead>
  <tbody>
    <tr><td>The fold and simulator</td><td>Everything works</td><td>Nothing</td></tr>
    <tr><td>Judge feedback</td><td>Everything works</td><td>Nothing</td></tr>
    <tr><td>Tester tracking</td><td>Everything except two columns</td>
        <td>“Owes feedback” and “checked in”</td></tr>
  </tbody>
</table>

<p>So: start with the token. Add <code>TABBY_USER</code> and
<code>TABBY_PASS</code> only if you want those two columns.</p>

<div class="tech">
  <h3>Why those two pages are different <span class="techflag">Technical</span></h3>
  <p>Tabbycat's REST API does not expose feedback progress or check-in status.
  Both exist only as admin pages — but every Tabbycat admin page hydrates its
  tables from a <code>window.vueData</code> global, so parsing that global out
  of the HTML gives you the same structured rows the page itself renders. It is
  still a GET of a page you are allowed to open in a browser; it is just not an
  API call, which is why a bearer token does not authenticate it.</p>
  <p><code>TabRead.needs_admin_pages()</code> reports whether the client has a
  session, and <code>tester-tracking/pull.py</code> skips those two reads with a
  message rather than letting a 403 look like a fault. The fake Tabbycat in
  <code>demo/</code> enforces the same distinction — its admin routes refuse a
  token-only client — so the behaviour is exercised by the demo rather than
  discovered at a tournament.</p>
</div>

<h2 id="why">Why this is for adjudication cores only</h2>

<p>Whichever way you sign in, it has to be a <b>tab-side account</b> —
adjudication core or tabulation. This is not a licensing decision; it is what
the data requires. A public or participant account cannot see:</p>

<ul>
  <li>written feedback about judges, which is the entire input to the feedback tool;</li>
  <li>who is on which panel, which is how tester tracking knows a judge has been watched;</li>
  <li>a draw before it is released, which is most of what makes any of this useful in the moment.</li>
</ul>

<p>If you are not on the adjudication core or the tab team at your tournament,
the person who is will need to run these, or give you an account. There is no
version of this that works from the public tab alone.</p>

<h2 id="ask">What to send your tab director</h2>

<p>You will probably have to ask for an account, and “can I have tab access so I
can run some scripts” is a reasonable thing to be cautious about. So here is the
case, in a form you can forward:</p>

<div class="note">
  <p><b>What it reads.</b> Rounds, the draw, panels, break categories and the
  break, teams, judges, institutions, motions and written feedback — through
  Tabbycat's own API, plus two admin pages for feedback progress and check-in
  status.</p>
  <p><b>What it writes.</b> Nothing. It cannot. The single piece of code that
  talks to Tabbycat refuses any request that is not a GET, HEAD or OPTIONS
  before it leaves the machine — there is no write function in the toolkit to
  call, and no setting that enables one. The only exception is the sign-in form
  itself, if you use a password rather than a token.</p>
  <p><b>Where the credentials live.</b> In a file on the laptop running it,
  which is excluded from version control. They are never sent anywhere except
  to your own tab.</p>
  <p><b>How to check any of that.</b> <code>python3 tests/test_release.py</code>
  in the repository. Among other things it parses every Python file and asserts
  that nothing outside the sign-in form can write to a tab.</p>
</div>

<div class="tech">
  <h3>The line that enforces it <span class="techflag">Technical</span></h3>
  <p>If your TD would rather read the code than the claim, it is short. In
  <code>core/tabread.py</code>:</p>
  <pre><code>SAFE = {"GET", "HEAD", "OPTIONS"}

class _GetOnlySession(requests.Session):
    def request(self, method, url, *a, **kw):
        if str(method).upper() not in SAFE:
            raise ReadOnlyViolation(...)
        return super().request(method, url, *a, **kw)</code></pre>
  <p>Every call in <code>requests</code> funnels through
  <code>Session.request</code>, including the convenience methods, so
  overriding it is sufficient rather than merely discouraging. A grep is enough
  to check nothing else is going on:</p>
  <pre><code>grep -rn "\\.post\\|\\.patch\\|\\.put\\|\\.delete" --include=*.py .</code></pre>
</div>

<h2 id="urlkeys">One warning that matters more than the rest</h2>

<div class="note stop">
  <p><b>Tabbycat's API returns each participant's <code>url_key</code>, and that
  value <em>is</em> their private URL.</b> Anyone holding it can submit ballots
  and feedback as that person.</p>
  <p>So any file you save from a pull is credential material, not just data. The
  feedback tool needs those keys — that is how it addresses a page to a judge —
  and it keeps them in <code>feedback/data/</code>, which is excluded from
  version control and written owner-readable only. <b>Delete that directory when
  your tournament is over.</b></p>
  <p>Do not put a raw pull in a shared drive, a git repository, or a chat.</p>
</div>

<div class="tech">
  <p><span class="techflag">Technical</span> This is why the published feedback
  site is addressed by <code>sha256(url_key)</code> rather than by the key
  itself. The site never contains a key, so a copy of the published directory is
  not a set of credentials the way a raw pull is; and there is no index, listing
  or search, so holding the site tells you nothing about who is in it. The
  hashing happens in the reader's browser.</p>
</div>

<h2 id="gotchas">Things that will waste your afternoon</h2>

<table>
  <thead><tr><th>What you see</th><th>What it is</th></tr></thead>
  <tbody>
    <tr><td><code>404</code> on an API path</td>
        <td>Nearly always the slug. It is the tournament's own bit of the web
        address, the part straight after the host name.</td></tr>
    <tr><td><code>/api/v1/</code> returns 404 but <code>/api/v1</code> works</td>
        <td>Not a mistake — Tabbycat really does 404 on the trailing slash. The
        toolkit already gets this right; it matters if you are writing your
        own requests.</td></tr>
    <tr><td>A list comes back short</td>
        <td>Tabbycat pages long lists and puts the next page in a
        <code>Link: …; rel="next"</code> header rather than in the body. Ignore
        the header and you silently get the first page only.</td></tr>
    <tr><td><code>403 Forbidden</code> after a successful sign-in</td>
        <td>The account is not tab-side. See above — this is the one that cannot
        be worked around.</td></tr>
    <tr><td>“did not look like a Tabbycat login page”</td>
        <td>The url points at a tournament path or a front page instead of the
        site root. No trailing slash, no <code>/admin</code>.</td></tr>
  </tbody>
</table>

<p>Full API documentation is Tabbycat's, not ours:
<a href="https://tabbycat.readthedocs.io/en/stable/features/api.html">the API
guide</a>, and your own tab serves its live schema at <code>/api/schema.yml</code>.</p>

<hr>
<p><a href="../start/">Next: set it up &rarr;</a></p>
""",
}
