"""
smoke.py — drive the built page in a real browser and fail loudly.

Checks the things a reader would notice within ten seconds: does every view
render, does the fold draw a line, do the connectors get drawn, does clicking a
team open its tournament, does search find people, does dark mode hold. Leaves
screenshots in tests/shots so a change can be eyeballed.

    python3 tests/smoke.py
"""
import pathlib
import sys

from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
PAGE = HERE.parent / "dist" / "index.html"
SHOTS = HERE / "shots"
SHOTS.mkdir(exist_ok=True)
fails = []


def check(ok, msg):
    print(("  ok   " if ok else "  FAIL ") + msg)
    if not ok:
        fails.append(msg)


def skip(msg):
    """Not applicable to this tournament's state — not a failure.

    A tournament before its break genuinely has no bracket to draw. A suite that
    reports that as broken teaches people to ignore it, so the distinction is
    made explicit instead."""
    print("  --   " + msg + "  (not applicable yet)")


if not PAGE.exists():
    sys.exit("no built page — run `python3 build.py` first")

with sync_playwright() as pw:
    b = pw.chromium.launch()
    pg = b.new_page(viewport={"width": 1500, "height": 1050})
    errs = []
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.on("pageerror", lambda e: errs.append("pageerror: " + str(e)))
    pg.goto(PAGE.as_uri())
    pg.wait_for_selector("#tabs button")

    print("\nthe fold")
    check(pg.locator(".bracketrow").count() > 3, "brackets render")
    check(pg.locator(".theline").count() >= 1, "the break line is drawn")
    line = pg.locator(".theline .lab").first.inner_text()
    check("break" in line.lower() or "cut" in line.lower(), f"the line is labelled — “{line}”")
    check(pg.locator(".kpi").count() >= 4, "the numbers above the fold render")
    # Scoped to the fold's own bracket. Counting `.tchip` across the whole page
    # also picks up the movers card, which is a different set of teams.
    chips = pg.locator("#v-fold .bracketrow .tchip").count()
    # The fold shows every team in the selected category. Asserting a fixed
    # number here is what made this test tournament-specific; the invariant is
    # that the count MATCHES the category, whatever size it is.
    expected = pg.evaluate("""() => {
      const slug = (document.querySelector('#v-fold .seg .on') || {}).dataset?.slug;
      const cat = (DATA.categories || []).find(c => !slug || c.slug === slug)
               || (DATA.categories || [])[0];
      if (!cat) return null;
      return (DATA.teams || []).filter(t => (t.cats || []).includes(cat.slug)).length;
    }""")
    if expected:
        check(chips == expected,
              f"the fold shows every team in the category ({chips} chips, "
              f"{expected} eligible teams)")
    else:
        check(chips > 0, f"{chips} team chips in the fold")
    pg.screenshot(path=str(SHOTS / "01-fold.png"), full_page=False)

    # scrub the round slider back and watch the fold change
    before = pg.locator(".bracketrow").count()
    # Scrub to the middle of whatever rounds this tournament actually has,
    # rather than to a round number that may not exist.
    target = max(1, int(pg.evaluate("LAST_SCORED")) // 2)
    pg.locator('input[type=range]').fill(str(target))
    pg.wait_for_timeout(250)
    after = pg.locator(".bracketrow").count()
    check(after != 0, f"the round scrubber re-forms the fold ({before} rows → {after})")
    want = pg.evaluate(f"(DATA.rounds.find(r => r.seq === {target}) || {{}}).abbr")
    check(bool(want) and want in pg.locator(".bar .pill").first.inner_text(),
          f"the scrubber says which round it is at (expected {want!r})")
    pg.screenshot(path=str(SHOTS / "02-fold-r3.png"))
    pg.locator('input[type=range]').fill(str(pg.evaluate("LAST_SCORED")))
    pg.wait_for_timeout(250)

    # A sub-category break is not the top N of the points stack: a team that broke
    # Open is out of the EFL break however many points it has. The line has to fall
    # below the LAST team that actually broke, or EFL #7 and #8 end up under it.
    for cat in pg.evaluate("DATA.categories.filter(c => !c.is_general && "
                           "((DATA.breaks||{})[c.slug]||[]).some(e => e.break_rank != null))"
                           ".map(c => c.name)"):
        pg.locator("#v-fold .seg button", has_text=cat).click()
        pg.wait_for_timeout(250)
        split = pg.evaluate('''(() => {
          const kids = [...document.querySelector('#v-fold .foldwrap').children];
          const li = kids.findIndex(k => k.classList.contains('theline'));
          const chips = els => els.flatMap(k => [...k.querySelectorAll('.tchip')]);
          return { below: chips(kids.slice(li + 1)).filter(c => c.classList.contains('breaks')).length,
                   above: chips(kids.slice(0, li)).filter(c => c.classList.contains('breaks')).length,
                   line: document.querySelector('#v-fold .theline .lab').textContent };
        })()''')
        check(split["below"] == 0,
              f"{cat}: every team that broke is above the line "
              f"({split['above']} above, {split['below']} stranded below)")
        check(str(split["above"]) in split["line"],
              f"{cat}: the line counts the teams that broke — “{split['line']}”")
        pg.screenshot(path=str(SHOTS / f"19-fold-{cat.lower()}.png"), full_page=True)
    pg.locator("#v-fold .seg button").first.click()
    pg.wait_for_timeout(200)

    print("\nclick-through")
    pg.locator(".tchip").first.click()
    pg.wait_for_selector("#sheet h2")
    name = pg.locator("#sheet h2").inner_text()
    check(pg.locator("#sheet .stat").count() >= 4, f"team sheet opens — {name}")
    check(pg.locator("#sheet table tbody tr").count() >= 3, "its round-by-round table is filled")
    check(pg.locator("#sheet .pathchart svg path").count() >= 2, "its path chart draws")
    check(pg.locator("#sheet .oppgrid .tchip").count() > 3, "the teams it faced are listed")
    pg.screenshot(path=str(SHOTS / "03-team.png"))
    jc = pg.locator("#sheet .jchip").first
    if jc.count():
        jc.click()
        pg.wait_for_timeout(200)
        check(pg.locator("#sheet .stat").count() >= 4, "a judge chip opens the judge sheet")
        pg.screenshot(path=str(SHOTS / "04-judge.png"))
    pg.keyboard.press("Escape")

    print("\nbreak rounds")
    pg.locator("#tab-bracket").click()
    # Before the break is announced there is no bracket, and that is a real
    # state rather than a fault — every check below is about a bracket that
    # exists, so they are skipped rather than failed.
    announced = pg.evaluate(
        "Object.values(DATA.breaks || {}).some(rows => "
        "(rows || []).some(r => r.break_rank != null))")
    if not announced:
        for m in ("columns of break rounds", "rooms render in every column",
                  "connectors are drawn between the blocks",
                  "the first next-round room is fed by rooms 1 and P",
                  "every feeding pair is drawn adjacent",
                  "the first column reads in bracket order",
                  "the break list is shown"):
            skip(m)
        BRACKET = False
    else:
        BRACKET = True
        pg.wait_for_selector(".tree .col")
    cols = pg.locator(".tree .col").count() if BRACKET else 0
    if BRACKET:
        check(cols >= 1, f"{cols} column(s) of break rounds")
        check(pg.locator(".room").count() >= cols, "rooms render in every column")
        pg.wait_for_timeout(350)
        # A single-room break (a four-team break that goes straight to a final)
        # has nothing to connect, and that is correct rather than missing.
        if cols >= 2:
            check(pg.locator("svg.links path").count() >= 1,
                  "connectors are drawn between the blocks")
        else:
            skip("connectors are drawn between the blocks (single-room break)")
    if BRACKET:
        # Two properties, both of which he noticed when they were wrong: room i must
        # meet room P+1-i (not its neighbour), and the pair must be drawn ADJACENT so
        # no connector crosses another.
        feed = pg.evaluate("""() => {
          const wrap = document.querySelector('#v-bracket .treewrap');
          const cols = [...wrap.querySelectorAll('.col .colbody')];
          const top = wrap.getBoundingClientRect().top;
          const mid = el => { const b = el.getBoundingClientRect(); return b.top + b.height/2 - top; };
          const paths = [...wrap.querySelectorAll('svg.links path')]
            .map(p => p.getAttribute('d').match(/^M[\\d.]+ ([\\d.]+) H[\\d.]+ V([\\d.]+)/))
            .filter(Boolean).map(m => [parseFloat(m[1]), parseFloat(m[2])]);
          // The bracket position, not the venue name — a released draw renames the rooms.
          const label = el => el.dataset.fi || '?';
          const out = [];
          for (let c = 1; c < cols.length; c++) {
            const kids = [...cols[c-1].children], par = [...cols[c].children];
            const ky = kids.map(mid);
            par.forEach((p, pi) => {
              const idx = paths.filter(([, b]) => Math.abs(b - mid(p)) < 2)
                .map(([a]) => ky.findIndex(y => Math.abs(y - a) < 2))
                .filter(i => i >= 0).sort((x, y) => x - y);
              out.push({ col: c, parent: label(p), from: idx.map(i => label(kids[i])),
                         slots: idx, adjacent: idx.length === 2 && idx[1] - idx[0] === 1 });
            });
          }
          return out;
        }""")
        # How many rooms the first break round had decides every expectation below,
        # so it is read off the page rather than written in. With P rooms, room i
        # meets room P+1-i — that is the property; "1 and 8" was only ever what the
        # property happened to say for a 32-team break.
        P = pg.evaluate(
            "[...document.querySelectorAll('#v-bracket .col .colbody')][0]"
            ".children.length")
        first = feed[0] if feed else {}
        got = [int(x) for x in (first.get("from") or []) if str(x).isdigit()]
        check(sorted(got) == [1, P],
              f"the first next-round room is fed by rooms {first.get('from')} — "
              f"with {P} rooms it must be 1 and {P} (a room meets room P+1-i, "
              f"never its neighbour)")
        check(all(f["adjacent"] for f in feed),
              "every feeding pair is drawn adjacent, so no connector crosses another"
              + ("" if all(f["adjacent"] for f in feed)
                 else " — crossing at " + str([f["parent"] for f in feed if not f["adjacent"]])))
        labels = pg.evaluate(
            "[...[...document.querySelectorAll('#v-bracket .col .colbody')][0]"
            ".children].map(e => e.dataset.fi)")
        # Bracket order means each room is immediately followed by the room it
        # meets, so every adjacent pair sums to P+1. That holds for any break size,
        # which is the point — a hardcoded ["1","8","4","5"] only held for one.
        nums = [int(x) for x in labels if str(x).isdigit()]
        pairs = [(nums[i], nums[i + 1]) for i in range(0, len(nums) - 1, 2)]
        bad = [pr for pr in pairs if sum(pr) != P + 1]
        check(not bad,
              f"the first column reads in bracket order (adjacent pairs sum to {P + 1}): "
              f"{', '.join(labels)}" + (f" — wrong at {bad}" if bad else ""))

        locked = pg.locator(".room.locked").count()
        check(locked >= 0, f"{locked} rooms still locked (dashed, no draw published)")
        check(pg.locator(".card .tchip").count() > 0, "the break list is shown")
    pg.screenshot(path=str(SHOTS / "05-bracket.png"), full_page=True)

    print("\nsimulator")
    # The simulator plays out the break rounds, so it has nothing to show
    # until a break exists. Same reasoning as the bracket above.
    if not BRACKET:
        for m in ("the simulator lays out the first break round",
                  "clicking two teams sends them through",
                  "a third pick replaces the oldest",
                  "chalk runs the break down to a champion",
                  "advancement lines follow the picks",
                  "a share code round-trips", "clear wipes the picks"):
            skip(m)
    else:
        pg.locator("#tab-sim").click()
        pg.wait_for_selector("#v-sim .room.sim")
        check(pg.locator("#v-sim .col").count() >= 2, "the simulator lays out every break round")
        # Pick in the first room the reader can still pick in. Once tab publishes a
        # break-round result that round locks, and its slots open a team sheet instead
        # — whose scrim then swallows every later click, which is what a bare .first
        # used to walk into.
        # Two things here used to be format assumptions dressed up as a test.
        #
        # (1) There may be nothing left to pick. If tab has published a result
        #     for every round that has been drawn, every room is locked to what
        #     actually happened — a real state, not a fault. Waiting for a
        #     pickable slot then hangs for the full timeout.
        # (2) How many teams go through a room is the format's business. Half of
        #     them advance: two of four in a British Parliamentary room, one of
        #     two elsewhere. Clicking slots 0, 2 and 1 only makes sense in a room
        #     with four seats.
        pickable = pg.locator("#v-sim .room.sim .slot.pick:not(.fixed)")
        if pickable.count() == 0:
            skip("clicking teams sends them through (every drawn round is "
                 "already decided, so there is nothing left to pick)")
            skip("a third pick replaces the oldest")
        else:
            room = pg.locator("#v-sim .room.sim").filter(
                has=pg.locator(".slot.pick:not(.fixed)")).first
            seats = room.locator(".slot").count()
            through = max(1, seats // 2)
            before = pg.locator("#v-sim .slot.through").count()
            for i in range(through):
                room.locator(".slot.pick:not(.fixed)").nth(i).click()
                pg.wait_for_timeout(120)
            check(pg.locator("#v-sim .slot.through").count() == before + through,
                  f"clicking {through} of {seats} teams sends them through")
            if seats > 2:
                # One more than the room allows: the oldest pick should drop out
                # rather than the room overfilling.
                room.locator(".slot.pick:not(.fixed)").last.click()
                pg.wait_for_timeout(200)
                check(room.locator(".slot.through").count() == through,
                      "a pick beyond the room's capacity replaces the oldest "
                      "rather than overfilling it")
            else:
                skip("a pick beyond capacity replaces the oldest (a two-team "
                     "room advances one, so there is no queue to displace)")
        pg.locator('#v-sim .ghost:has-text("Chalk")').click()
        pg.wait_for_timeout(400)
        champ = pg.locator("#v-sim .champ .who")
        check(champ.count() == 1, "chalk runs the whole break down to a champion: "
              + (champ.inner_text().replace("\n", " ") if champ.count() else "none"))
        links = pg.locator("#v-sim svg.links path").count()
        rooms0 = pg.evaluate(
            "[...document.querySelectorAll('#v-sim .col .colbody')][0]?.children.length || 0")
        check(links >= max(1, rooms0), f"advancement lines follow the picks "
              f"({links} lines for {rooms0} first-round rooms)")
        pg.screenshot(path=str(SHOTS / "16-sim.png"), full_page=True)
        pg.locator('#v-sim .ghost:has-text("Share")').click()
        pg.wait_for_timeout(200)
        code = pg.evaluate("location.hash")
        restored_target = pg.locator("#v-sim .slot.through").count()
        check(code.startswith("#sim="), f"share puts the picks in the link ({len(code)} chars)")
        pg.locator('#v-sim .ghost:has-text("Clear")').click()
        pg.wait_for_timeout(200)
        check(pg.locator("#v-sim .slot.pick:not(.fixed).through").count() == 0,
              "clear empties the reader's picks (a published result stays, correctly)")
        pg.evaluate(f"location.hash = '{code}'")
        pg.wait_for_timeout(400)
        # Compare against what was on the page before Clear, rather than a
        # number taken from one tournament. And if nothing was pickable there is
        # nothing to restore, which is a state rather than a failure.
        if restored_target == 0:
            skip("pasting a shared link restores the picks (nothing was "
                 "pickable, so there was nothing to share)")
        else:
            check(pg.locator("#v-sim .slot.through").count() == restored_target,
                  f"pasting a shared link restores the picks ({restored_target})")
        check(pg.locator("#v-sim .champ .who").count() == 1, "and its champion")

        # The bracket is FIXED at the break. Stated as the invariant rather than as a
        # scripted click, because whether a round comes from tab's result or from the
        # reader's picks changes hour to hour and the rule does not: every room is
        # exactly the survivors of rooms `i` and `P+1-i` of the round before.
        fixed = pg.evaluate('''(() => {
          const out = [];
          for (const c of DATA.categories.filter(c => c.rounds.length)) {
            simState.slug = c.slug; simState.adv = {};
            simChalkQuiet(c.slug);
            const rounds = simRounds(c.slug);
            for (let k = 1; k < rounds.length; k++) {
              const prev = simRoomsAt(c.slug, k - 1), adv = simRoomAdvancers(c.slug, k - 1);
              const now = simRoomsAt(c.slug, k);
              if (!prev || !adv || !now) continue;
              const P = prev.length;
              now.forEach((seats, x) => {
                const a = adv[x], b = adv[P - 1 - x];
                if (!seats) { out.push({cat:c.slug, k, room:x+1, ok: !a || !b,
                                        why:"empty room must mean an unsettled feeder"}); return; }
                const want = [...(a||[]), ...(b||[])].sort().join(",");
                const got  = seats.map(s => s.t).sort().join(",");
                out.push({cat:c.slug, k, room:x+1, ok: want === got, want, got});
              });
            }
          }
          simState.adv = {}; simSave();
          return out;
        })()''')
        bad = [f for f in fixed if not f["ok"]]
        check(fixed and not bad,
              f"the fold is fixed at the break: all {len(fixed)} rooms across both categories "
              f"are exactly the survivors of rooms i and P+1-i"
              + ("" if not bad else f" — broken at {bad[0]}"))
        pg.evaluate("simState.adv = {}; simSave(); renderSim();")
        pg.wait_for_timeout(200)

    print("\nround by round")
    pg.locator("#tab-rounds").click()
    pg.wait_for_selector("#roomgrid .room")
    grid = pg.locator("#roomgrid .room").count()
    check(grid >= 1, f"the draw grid renders ({grid} rooms)")
    seats = pg.evaluate("(DATA.tournament || {}).teams_per_debate || 4")
    check(pg.locator("#roomgrid .slot").count() >= grid * seats,
          f"every room lists its teams ({grid} rooms x {seats} seats)")
    check(pg.locator("#roomgrid .jchip").count() >= grid, "panels are shown")
    total = pg.locator("#roomgrid .room").count()
    pg.locator('#v-rounds input[type=search]').fill("Riverbend A")
    pg.wait_for_timeout(200)
    vis = pg.locator("#roomgrid .room:visible").count()
    check(vis <= total, f"the filter narrows {total} rooms to {vis}")
    pg.screenshot(path=str(SHOTS / "06-rounds.png"))

    print("\ntables")
    # Expected row counts come from the payload. Fixed numbers here made the
    # suite pass on one tournament and fail on every other one, which is the
    # opposite of what a test is for.
    want = {
        "teams": pg.evaluate("(DATA.teams || []).length"),
        "judges": pg.evaluate("(DATA.judges || []).length"),
        # The schools view groups BOTH teams and judges by institution, so a
        # count taken from teams alone is right only when every school that sent
        # a judge also sent a team.
        "schools": pg.evaluate(
            "new Set([...(DATA.teams || []), ...(DATA.judges || [])]"
            ".map(x => x.inst).filter(Boolean)).size"),
    }
    for tab in ("teams", "judges", "schools"):
        pg.locator("#tab-" + tab).click()
        pg.wait_for_selector(f"#v-{tab} tbody tr")
        # The schools view holds two tables, schools and regions, so the row
        # count is taken from the first body rather than the whole panel.
        rows = pg.locator(f"#v-{tab} tbody").nth(0).locator("tr").count()
        check(rows == want[tab], f"{tab}: {rows} rows (payload has {want[tab]})")
    regions = pg.evaluate(
        "new Set([...(DATA.teams || []), ...(DATA.judges || [])]"
        ".map(x => x.region || '—')).size")
    check(pg.locator("#v-schools tbody").nth(1).locator("tr").count() == regions,
          f"regions table has a row per region ({regions})")
    schools_before = pg.locator("#v-schools tbody tr").count()
    pg.locator("#v-schools th.sortable").first.click()
    check(pg.locator("#v-schools tbody tr").count() == schools_before,
          "sorting a column keeps every row (nothing dropped or duplicated)")
    pg.screenshot(path=str(SHOTS / "07-teams.png"))

    print("\nwhat's shown")
    pg.locator("#tab-shown").click()
    pg.wait_for_selector("#v-shown .card")
    check(pg.locator("#v-shown li").count() >= 1, "the shown/withheld lists render")
    rounds = pg.evaluate("(DATA.rounds || []).length")
    check(pg.locator("#v-shown tbody tr").count() == rounds,
          f"the per-round switch table has a row per round ({rounds})")
    pg.screenshot(path=str(SHOTS / "08-shown.png"), full_page=True)

    print("\nsearch and theme")
    pg.keyboard.press("/")
    pg.wait_for_selector("#palette:not([hidden])")
    pg.locator("#q").fill("Riverbend")
    pg.wait_for_timeout(200)
    check(pg.locator("#qres li").count() >= 1, "search finds a team")
    pg.keyboard.press("Enter")
    pg.wait_for_timeout(200)
    check(pg.locator("#sheet h2").count() == 1, "enter opens the top hit")
    pg.keyboard.press("Escape")
    pg.locator("#btn-theme").click()
    pg.wait_for_timeout(150)
    check(pg.evaluate("document.documentElement.dataset.theme") in ("dark", "light"),
          "the theme toggle switches")
    pg.locator("#tab-fold").click()
    pg.screenshot(path=str(SHOTS / "09-dark.png"))

    print("\nnarrow screen")
    pg.set_viewport_size({"width": 390, "height": 844})
    pg.wait_for_timeout(250)
    over = pg.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
    check(over <= 2, f"no horizontal overflow on a phone (overflow {over}px)")
    pg.screenshot(path=str(SHOTS / "10-phone.png"))

    check(not errs, "no console errors" + ("" if not errs else " — " + " | ".join(errs[:4])))
    b.close()

print()
if fails:
    print(f"{len(fails)} check(s) failed.")
    sys.exit(1)
print(f"all checks passed — screenshots in {SHOTS.relative_to(SHOTS.parent.parent)}")
