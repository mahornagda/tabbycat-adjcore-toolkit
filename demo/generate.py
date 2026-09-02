#!/usr/bin/env python3
"""
generate.py — invent a whole tournament, deterministically.

The demo does not ship fixture files for each tool. It ships a fake Tabbycat,
and the tools run against it completely unmodified. That buys three things at
once:

  · sample sites built from data that never existed, so there is nothing to
    scrub and nothing to leak;
  · a test suite anybody can run with no tournament and no credentials;
  · proof that nothing about tournament shape is hardcoded — the same three
    tools are pointed at a 4-team, 9-round, two-category tournament and at a
    2-team, 5-round, one-category one, and neither needs a line changed.

Everything comes from a shape file in shapes/. Nothing here is random at run
time: the same shape and seed always produce the same tournament, so a
screenshot in the docs can be regenerated years later and still match.

WHAT IT DELIBERATELY MAKES AWKWARD
----------------------------------
A happy-path fixture proves nothing. This generator builds, on purpose:

  · a sub-category break whose line does NOT fall at the top N of the points
    stack, because some of its teams broke the main category instead;
  · a break round that is half decided — some rooms have ballots in, some do
    not, which is the state that used to lock a simulator up;
  · judges with nineteen comments and judges with two, so the thin-summary
    path is exercised;
  · panels of mixed size, since a tournament can change panel size mid-event;
  · comments containing scores, team names, round names, motion words and
    quotable phrases, so the feedback mask and gate have real work to do.
"""
import argparse, hashlib, json, os, random, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
CORPUS = os.path.join(HERE, "corpus")

SIDES_BY_COUNT = {4: ["og", "oo", "cg", "co"], 2: ["aff", "neg"], 3: ["og", "oo", "cg"]}
BP_POINTS = [3, 2, 1, 0]


# --------------------------------------------------------------- the corpus ---
def _corpus(name):
    with open(os.path.join(CORPUS, name), encoding="utf-8") as fh:
        return [l.rstrip("\n") for l in fh
                if l.strip() and not l.lstrip().startswith("#")]


def _people():
    text = open(os.path.join(CORPUS, "people.txt"), encoding="utf-8").read()
    given = text.split("[given]")[1].split("[family]")[0].split()
    family = text.split("[family]")[1].split()
    return given, family


def _institutions():
    out = []
    for line in _corpus("institutions.txt"):
        parts = line.split("|")
        if len(parts) >= 3:
            out.append({"name": parts[0].strip(), "code": parts[1].strip(),
                        "region": parts[2].strip()})
    return out


def _comments():
    out = []
    for line in _corpus("comments.txt"):
        if "|" not in line:
            continue
        tag, text = line.split("|", 1)
        out.append((tag.strip(), text.strip()))
    return out


# ------------------------------------------------------------------- shapes ---
DEFAULT_SHAPE = {
    "name": "Demo Open 2027",
    "short": "Demo",
    "slug": "demo",
    "seed": 7,
    "teams_in_debate": 4,
    "speakers_per_team": 2,
    "side_names": "gov-opp",
    "prelims": 9,
    "teams": 48,
    "judges": 40,
    "adjcore": 6,
    "institutions": 24,
    "panel_size": 3,
    "panel_size_from_round": {},        # {"1": 2} — a tournament that changed mid-event
    "break_categories": [
        {"name": "Open", "slug": "open", "size": 16, "general": True},
    ],
    "rounds_completed": 9,
    "silent_rounds": [],
    "break_announced": True,
    # How far the elimination rounds have got, per category. 0 = no draw,
    # 1 = first elim drawn and fully decided, 1.5 = second drawn, half decided.
    "elim_progress": {},
    "feedback_per_debate": 0.30,
    "public": {},
}

PUBLIC_DEFAULTS = {
    "public_features__public_draw": "all-released",
    "public_features__public_results": True,
    "public_features__public_motions": True,
    "public_features__public_breaking_teams": True,
    "public_features__public_breaking_adjs": True,
    "public_features__public_team_standings": True,
    "public_features__public_participants": True,
    "tab_release__team_tab_released": False,
    "tab_release__speaker_tab_released": False,
    "tab_release__ballots_released": False,
}


def load_shape(path):
    shape = dict(DEFAULT_SHAPE)
    if path:
        with open(path, encoding="utf-8") as fh:
            shape.update(json.load(fh))
    pub = dict(PUBLIC_DEFAULTS)
    pub.update(shape.get("public") or {})
    shape["public"] = pub
    return shape


# ------------------------------------------------------------- the generator --
class Tournament:
    def __init__(self, shape, base="http://127.0.0.1:8799"):
        self.sh = shape
        self.base = base.rstrip("/")
        self.slug = shape["slug"]
        self.rng = random.Random(shape.get("seed", 7))
        self.tpd = int(shape["teams_in_debate"])
        self.sides = SIDES_BY_COUNT.get(self.tpd) or [f"s{i}" for i in range(self.tpd)]
        self._build()

    # ---- url helpers, matching Tabbycat's shapes exactly ----
    def t_url(self, *parts):
        return "/".join([f"{self.base}/api/v1/tournaments/{self.slug}", *map(str, parts)])

    def g_url(self, *parts):
        return "/".join([f"{self.base}/api/v1", *map(str, parts)])

    # ------------------------------------------------------------------ build --
    def _build(self):
        self._institutions()
        self._teams()
        self._adjudicators()
        self._rounds()
        self._draws()
        self._results()
        self._breaks()
        self._elims()
        self._feedback()

    def _institutions(self):
        pool = _institutions()
        n = min(int(self.sh["institutions"]), len(pool))
        self.insts = []
        for i, rec in enumerate(pool[:n], 1):
            self.insts.append({
                "id": i, "url": self.g_url("institutions", i),
                "name": rec["name"], "code": rec["code"], "region": rec["region"],
            })

    def _teams(self):
        letters = "ABCDEFGH"
        self.teams, tid = [], 0
        per = max(1, -(-int(self.sh["teams"]) // len(self.insts)))
        for inst in self.insts:
            for k in range(per):
                if len(self.teams) >= int(self.sh["teams"]):
                    break
                tid += 1
                ref = letters[k % len(letters)]
                self.teams.append({
                    "id": tid, "url": self.t_url("teams", tid),
                    "reference": ref,
                    "short_name": f"{inst['code']} {ref}",
                    "long_name": f"{inst['name']} {ref}",
                    "code_name": None,
                    "institution": inst["url"],
                    "institution_conflicts": [],
                    "break_categories": [],
                    "speakers": [],
                })
        # A latent strength per team. Without it every result is a coin flip,
        # totals bunch up, and thirteen teams end up tied across the break line —
        # which no real nine-round tournament looks like, and which makes the
        # sample pages look broken rather than realistic.
        for i, tm in enumerate(self.teams):
            tm["_strength"] = self.rng.gauss(0, 1) + (len(self.teams) / 2 - i) * 0.01

        given, family = _people()
        sid = 0
        for tm in self.teams:
            for _ in range(int(self.sh["speakers_per_team"])):
                sid += 1
                tm["speakers"].append({
                    "id": sid, "name": f"{self.rng.choice(given)} {self.rng.choice(family)}",
                    "url": self.t_url("teams", tm["id"], "speakers", sid),
                })

    def _adjudicators(self):
        given, family = _people()
        n, core = int(self.sh["judges"]), int(self.sh["adjcore"])
        used, self.adjs = set(), []
        for i in range(1, n + 1):
            while True:
                name = f"{self.rng.choice(given)} {self.rng.choice(family)}"
                if name not in used:
                    used.add(name)
                    break
            inst = self.insts[(i - 1) % len(self.insts)]
            # A private URL key. Tabbycat's are random; these are derived from the
            # name so the demo is reproducible — and they are keys to a tournament
            # that does not exist.
            key = hashlib.sha1(f"{self.slug}:{name}".encode()).hexdigest()[:8]
            self.adjs.append({
                "id": i, "url": self.t_url("adjudicators", i), "name": name,
                "institution": inst["url"],
                "base_score": round(self.rng.uniform(2.0, 5.0), 1),
                "gender": self.rng.choice(["M", "F", "F", "M", "O", None]),
                "pronoun": None,
                "adj_core": i <= core,
                "independent": bool(i <= core + 4 and i > core),
                "trainee": bool(i > n - 5),
                "breaking": False,
                "team_conflicts": [], "adjudicator_conflicts": [],
                "institution_conflicts": [inst["url"]],
                "email": f"judge{i}@example.invalid",
                "url_key": key,
            })
        # a few real conflicts, so the checks have something to find
        for a in self.adjs[: max(3, n // 8)]:
            a["team_conflicts"] = [self.rng.choice(self.teams)["url"]]
        for a in self.adjs[1:4]:
            other = self.rng.choice(self.adjs)
            if other["id"] != a["id"]:
                a["adjudicator_conflicts"] = [other["url"]]

    def _rounds(self):
        """Prelims, then one elimination sequence per break category."""
        self.bcats, self.rounds = [], []
        for i, bc in enumerate(self.sh["break_categories"], 1):
            self.bcats.append({
                "id": i, "url": self.t_url("break-categories", i),
                "name": bc["name"], "slug": bc["slug"], "seq": i,
                "break_size": int(bc["size"]), "is_general": bool(bc.get("general")),
            })
        seq, prelims = 0, int(self.sh["prelims"])
        completed = int(self.sh["rounds_completed"])
        silent = set(self.sh.get("silent_rounds") or [])
        for r in range(1, prelims + 1):
            seq += 1
            done = r <= completed
            self.rounds.append(self._round(
                seq, f"Round {r}", f"R{r}", stage="P", bc=None,
                completed=done, silent=r in silent,
                draw_status="R" if done or r == completed + 1 else "N"))
        # Elimination rounds: room count halves from break_size / teams_per_debate.
        for bc in self.bcats:
            rooms, k = bc["break_size"] // self.tpd, 0
            names = self._elim_names(rooms)
            prog = float((self.sh.get("elim_progress") or {}).get(bc["slug"], 0))
            while rooms >= 1:
                seq += 1
                k += 1
                drawn = k <= prog + 0.999 and prog > 0
                decided = k <= prog
                # With more than one break category the elimination rounds
                # collide ("SF" twice), so tab prefixes them — and so does this,
                # because a tool that keys anything off the abbreviation needs to
                # meet that case in the demo rather than in the field.
                full, abbr = names[k - 1]
                if len(self.bcats) > 1:
                    full = f"{bc['name']} {full}"
                    abbr = f"{bc['name'][0].upper()}{abbr}"
                self.rounds.append(self._round(
                    seq, full, abbr, stage="E", bc=bc,
                    completed=decided, silent=not decided,
                    draw_status="R" if drawn else "N", rooms=rooms))
                if rooms == 1:
                    break
                rooms //= 2

    def _elim_names(self, rooms):
        """Names an elimination sequence the way tab does, from the room count."""
        ladder = [(1, "Grand Final", "GF"), (2, "Semifinals", "SF"),
                  (4, "Quarterfinals", "QF"), (8, "Octofinals", "OF"),
                  (16, "Double Octofinals", "DOF"), (32, "Triple Octofinals", "TOF")]
        by_rooms = {n: (full, abbr) for n, full, abbr in ladder}
        out, n = [], rooms
        while n >= 1:
            out.append(by_rooms.get(n, (f"Elim {n} rooms", f"E{n}")))
            if n == 1:
                break
            n //= 2
        return out

    def _round(self, seq, name, abbr, stage, bc, completed, silent, draw_status, rooms=None):
        return {
            "id": seq, "url": self.t_url("rounds", seq), "seq": seq,
            "name": name, "abbreviation": abbr, "stage": stage,
            "break_category": bc["url"] if bc else None,
            "completed": completed, "silent": silent,
            "draw_status": draw_status,
            "motions_released": stage == "P" and completed,
            "feedback_weight": 0.75,
            "starts_at": None, "_rooms": rooms,
        }

    def _panel_size(self, seq):
        override = (self.sh.get("panel_size_from_round") or {})
        size = int(self.sh["panel_size"])
        for start, val in sorted(((int(k), int(v)) for k, v in override.items())):
            if seq >= start:
                size = val
        return size

    def _draws(self):
        """A draw for every round whose status says it has one.

        Testers are seeded onto panels on purpose: tester tracking derives "this
        judge has been watched" from a tester sitting on their panel, so a demo
        where no adjcore member ever judged would show an empty dashboard.
        """
        self.venues = [{"id": i, "url": self.t_url("venues", i),
                        "name": f"Room {100 + i}", "display_name": f"Room {100 + i}"}
                       for i in range(1, (len(self.teams) // self.tpd) + 4)]
        self.pairings, pid = {}, 0
        testers = [a for a in self.adjs if a["adj_core"]]
        others = [a for a in self.adjs if not a["adj_core"]]
        for r in self["prelim_rounds"]:
            if r["draw_status"] == "N":
                continue
            teams = list(self.teams)
            self.rng.shuffle(teams)
            rooms = len(teams) // self.tpd
            size = self._panel_size(r["seq"])
            rows = []
            for i in range(rooms):
                pid += 1
                block = teams[i * self.tpd:(i + 1) * self.tpd]
                panel = self._panel(size, testers, others, i, r["seq"])
                rows.append({
                    "id": pid, "url": self.t_url("rounds", r["seq"], "pairings", pid),
                    "venue": self.venues[i % len(self.venues)]["url"],
                    "bracket": float(self.rng.randint(0, 6)),
                    "importance": self.rng.choice([0, 0, 1, 2]),
                    "result_status": "C" if r["completed"] else "N",
                    "sides_confirmed": True,
                    "teams": [{"side": self.sides[j], "team": tm["url"]}
                              for j, tm in enumerate(block)],
                    "adjudicators": panel,
                })
            self.pairings[r["seq"]] = rows

    def _panel(self, size, testers, others, room_index, seq):
        """One panel. A tester chairs roughly every third room, and sits as a
        panellist or a trainee-watcher in others, so the demo shows all three
        tested-as positions — trainee included, which an early version of the
        real thing wrongly ignored."""
        pool = list(others)
        self.rng.shuffle(pool)
        tester = testers[(room_index + seq) % len(testers)] if testers else None
        with_tester = tester is not None and room_index % 3 != 2
        panel = {"chair": None, "panellists": [], "trainees": []}
        picked = []
        if with_tester and room_index % 3 == 0:
            panel["chair"] = tester["url"]
            picked.append(tester["id"])
        for a in pool:
            if len(picked) >= size:
                break
            if a["id"] in picked:
                continue
            picked.append(a["id"])
            if panel["chair"] is None:
                panel["chair"] = a["url"]
            elif a["trainee"]:
                panel["trainees"].append(a["url"])
            else:
                panel["panellists"].append(a["url"])
        if with_tester and tester["id"] not in picked and len(picked) >= 1:
            panel["panellists"].append(tester["url"])
        return panel

    def _results(self):
        """Prelim points. BP gives 3/2/1/0 by position in the room; a two-team
        format gives 1/0. Either way the shape of the payload is the same, which
        is why nothing downstream needs to know which it is."""
        self.points = {}          # (seq, team_id) -> int
        self.sides_of = {}        # (seq, team_id) -> side
        for r in self["prelim_rounds"]:
            if not r["completed"]:
                continue
            for d in self.pairings.get(r["seq"], []):
                # Ranked by strength plus a round's worth of noise, so the better
                # teams tend to win without the result being a foregone conclusion.
                by_url = {tm["url"]: tm for tm in self.teams}
                order = sorted(
                    range(self.tpd),
                    key=lambda slot: -(by_url[d["teams"][slot]["team"]]["_strength"]
                                       + self.rng.gauss(0, 0.7)))
                scale = BP_POINTS[: self.tpd] if self.tpd == 4 else list(
                    range(self.tpd - 1, -1, -1))
                for rank, slot in enumerate(order):
                    dt = d["teams"][slot]
                    tid = int(dt["team"].rstrip("/").rsplit("/", 1)[1])
                    self.points[(r["seq"], tid)] = scale[rank]
                    self.sides_of[(r["seq"], tid)] = dt["side"]

    def total(self, tid):
        return sum(v for (s, t), v in self.points.items() if t == tid)

    def _breaks(self):
        """The break, per category — and the awkward case on purpose.

        A sub-category's break line is NOT the top N of its own points stack.
        Teams eligible for it that broke the general category are marked with a
        remark and sit ABOVE their own category's line, so cutting after the
        first N positions strands the last teams that genuinely broke. Getting
        this wrong is a real bug that shipped once; the demo reproduces the
        condition so the fix stays tested.
        """
        # eligibility: general = everyone, others = a deterministic slice
        for bc in self.bcats:
            if bc["is_general"]:
                elig = [tm for tm in self.teams]
            else:
                frac = 0.4
                elig = [tm for i, tm in enumerate(self.teams)
                        if (i * 7919) % 100 < frac * 100]
            bc["_eligible"] = [tm["url"] for tm in elig]
            for tm in elig:
                tm["break_categories"].append(bc["url"])

        self.breaks = {}
        if not self.sh.get("break_announced"):
            for bc in self.bcats:
                self.breaks[bc["slug"]] = []
            return

        general = next((b for b in self.bcats if b["is_general"]), None)
        general_ids = set()
        for bc in self.bcats:
            elig_ids = [int(u.rstrip("/").rsplit("/", 1)[1]) for u in bc["_eligible"]]
            ranked = sorted(elig_ids, key=lambda t: (-self.total(t), t))
            rows, rank, taken = [], 0, 0
            for tid in ranked:
                rank += 1
                # already through on the general break: recorded, but not counted
                # against this category's size
                if bc is not general and tid in general_ids:
                    rows.append({"team": self.t_url("teams", tid), "rank": rank,
                                 "break_rank": None, "remark": "D"})
                    continue
                if taken < bc["break_size"]:
                    taken += 1
                    rows.append({"team": self.t_url("teams", tid), "rank": rank,
                                 "break_rank": taken, "remark": None})
                    if bc is general:
                        general_ids.add(tid)
                else:
                    rows.append({"team": self.t_url("teams", tid), "rank": rank,
                                 "break_rank": None, "remark": None})
            self.breaks[bc["slug"]] = rows
        # adjudicator break: the core plus the strongest others
        for a in sorted(self.adjs, key=lambda x: -x["base_score"])[: max(6, len(self.adjs) // 3)]:
            a["breaking"] = True

    def _elims(self):
        """Elimination draws and ballots, folded the way a real break folds, and
        deliberately left HALF DECIDED where the shape asks for it."""
        pid = 10_000
        for bc in self.bcats:
            elims = [r for r in self.rounds
                     if r["stage"] == "E" and r["break_category"] == bc["url"]]
            broke = [int(e["team"].rstrip("/").rsplit("/", 1)[1])
                     for e in sorted((e for e in self.breaks.get(bc["slug"], [])
                                      if e["break_rank"]),
                                     key=lambda e: e["break_rank"])]
            if not broke:
                continue
            alive = list(broke)
            for r in elims:
                if r["draw_status"] == "N":
                    break
                rooms = max(1, len(alive) // self.tpd)
                rows = []
                for i in range(1, rooms + 1):
                    pid += 1
                    if r is elims[0]:
                        # first elim: fold inward off the break seeds
                        seats = []
                        for k in range(self.tpd):
                            pos = (i + k * rooms) if k % 2 == 0 else ((k + 1) * rooms + 1 - i)
                            seats.append(alive[pos - 1])
                    else:
                        seats = alive[(i - 1) * self.tpd: i * self.tpd]
                    rows.append({
                        "id": pid, "url": self.t_url("rounds", r["seq"], "pairings", pid),
                        "venue": self.venues[(i - 1) % len(self.venues)]["url"],
                        "bracket": None, "importance": 2,
                        "result_status": "C" if r["completed"] else "N",
                        "sides_confirmed": False,
                        "teams": [{"side": None, "team": self.t_url("teams", t)}
                                  for t in seats],
                        "adjudicators": self._panel(
                            max(3, self._panel_size(r["seq"])),
                            [a for a in self.adjs if a["adj_core"]],
                            [a for a in self.adjs if a["breaking"] and not a["adj_core"]],
                            i, r["seq"]),
                        "_seats": seats,
                    })
                self.pairings[r["seq"]] = rows

                # Ballots. A round in progress has some rooms in and some not —
                # which is the state that must not lock a bracket up.
                decided_rooms = len(rows) if r["completed"] else len(rows) // 2
                survivors = []
                self.ballots = getattr(self, "ballots", {})
                for idx, row in enumerate(rows):
                    if idx >= decided_rooms:
                        self.ballots[row["id"]] = []
                        continue
                    seats = row["_seats"]
                    through = sorted(seats, key=lambda t: (-self.total(t), t))[: self.tpd // 2]
                    survivors.extend(through)
                    self.ballots[row["id"]] = [{
                        "id": row["id"], "confirmed": True, "version": 1,
                        "result": {"sheets": [{
                            "adjudicator": row["adjudicators"]["chair"],
                            "teams": [{"team": self.t_url("teams", t),
                                       "win": t in through,
                                       "points": None, "score": None}
                                      for t in seats]}]},
                    }]
                # fold the survivors for the next round: room i meets room P+1-i
                nxt, P = [], len(rows)
                if r["completed"]:
                    for i in range(1, P // 2 + 1):
                        a = [t for t in self.ballots[rows[i - 1]["id"]][0]["result"]["sheets"][0]["teams"]
                             if t["win"]]
                        b = [t for t in self.ballots[rows[P - i]["id"]][0]["result"]["sheets"][0]["teams"]
                             if t["win"]]
                        for x in a + b:
                            nxt.append(int(x["team"].rstrip("/").rsplit("/", 1)[1]))
                alive = nxt
                if not alive:
                    break
        for rows in self.pairings.values():
            for row in rows:
                row.pop("_seats", None)

    def _feedback(self):
        """Written feedback, from teams and from co-panellists.

        Volume is uneven on purpose: some judges collect nineteen comments and
        some collect two, because the thin case needs to be visible in the
        sample rather than described in a footnote.
        """
        comments = _comments()
        by_tag = {}
        for tag, text in comments:
            by_tag.setdefault(tag, []).append(text)
        self.fq = [
            {"id": 1, "url": self.t_url("feedback-questions", 1),
             "name": "comments", "text": "Comments for the adjudicator",
             "answer_type": "tl", "required": False, "from_team": True,
             "from_adj": True, "seq": 1},
            {"id": 2, "url": self.t_url("feedback-questions", 2),
             "name": "agree", "text": "Did you agree with the decision?",
             "answer_type": "bc", "required": False, "from_team": True,
             "from_adj": False, "seq": 2},
        ]
        self.feedback, fid = [], 0
        # how chatty each judge's rooms were: a long tail, not a flat rate
        chatty = {a["id"]: self.rng.choice([0.2, 0.4, 0.6, 0.8, 0.95, 1.0, 1.0])
                  for a in self.adjs}
        for seq, rows in sorted(self.pairings.items()):
            r = self["round"](seq)
            if not r or not r["completed"]:
                continue
            for d in rows:
                panel = [d["adjudicators"]["chair"]] + list(d["adjudicators"]["panellists"]) \
                        + list(d["adjudicators"]["trainees"])
                panel = [p for p in panel if p]
                sources = [dt["team"] for dt in d["teams"]] + panel
                for target in panel:
                    aid = int(target.rstrip("/").rsplit("/", 1)[1])
                    for src in sources:
                        if src == target:
                            continue
                        if self.rng.random() > float(self.sh["feedback_per_debate"]) * chatty[aid]:
                            continue
                        fid += 1
                        tag = self.rng.choices(
                            ["praise", "growth", "split", "thin", "bait"],
                            weights=[34, 30, 12, 14, 10])[0]
                        # Roughly a third of real submissions carry only the
                        # scale answers and no prose. pull.py drops those, so the
                        # demo has to contain them or that path is never taken.
                        text = ("" if self.rng.random() < 0.34
                                else self._fill(self.rng.choice(by_tag[tag]), d, seq))
                        self.feedback.append({
                            "id": fid, "url": self.t_url("feedback", fid),
                            "adjudicator": target, "source": src,
                            "debate": self.t_url("rounds", seq, "pairings", d["id"]),
                            "score": round(self.rng.uniform(5.0, 9.5), 1),
                            "confirmed": True, "ignored": False,
                            "timestamp": f"2027-03-0{min(9, 1 + seq // 3)}T1{seq % 9}:00:00+00:00",
                            "answers": [
                                {"question": self.fq[0]["url"], "answer": text},
                                {"question": self.fq[1]["url"],
                                 "answer": self.rng.choice([True, False])},
                            ],
                        })

    def _fill(self, text, debate, seq):
        """Put real entities into the bait comments, so the mask and the gate
        have something genuine to catch."""
        tid = int(debate["teams"][0]["team"].rstrip("/").rsplit("/", 1)[1])
        team = next(t for t in self.teams if t["id"] == tid)
        inst = next(i for i in self.insts if i["url"] == team["institution"])
        r = self["round"](seq)
        judge = self.rng.choice(self.adjs)
        motions = _corpus("motions.txt")
        words = [w for w in re.findall(r"[a-z]{7,}", self.rng.choice(motions).lower())]
        return (text.replace("{TEAM}", team["short_name"])
                    .replace("{SCHOOL}", inst["name"])
                    .replace("{PLACE}", inst["region"])
                    .replace("{ROUND}", r["abbreviation"] if r else "R1")
                    .replace("{JUDGE}", judge["name"])
                    .replace("{SCORE}", str(self.rng.randint(68, 79)))
                    .replace("{MOTIONWORD}", words[0] if words else "mechanism"))

    # -------------------------------------------------------------- accessors --
    def __getitem__(self, key):
        if key == "prelim_rounds":
            return [r for r in self.rounds if r["stage"] == "P"]
        if key == "round":
            return lambda seq: next((r for r in self.rounds if r["seq"] == seq), None)
        raise KeyError(key)

    def _per_judge(self):
        import collections
        c = collections.Counter(
            f["adjudicator"] for f in self.feedback
            if str(f["answers"][0]["answer"] or "").strip())
        if not c:
            return {}
        v = sorted(c.values())
        return {"judges_with_comments": len(v), "min": v[0],
                "median": v[len(v) // 2], "max": v[-1],
                "under_three": sum(1 for x in v if x < 3)}

    def summary(self):
        elim = [r for r in self.rounds if r["stage"] == "E"]
        drawn = [r for r in elim if r["draw_status"] != "N"]
        return {
            "name": self.sh["name"],
            "teams_in_debate": self.tpd,
            "teams": len(self.teams), "judges": len(self.adjs),
            "institutions": len(self.insts),
            "prelims": len(self["prelim_rounds"]),
            "elims": len(elim), "elims_drawn": len(drawn),
            "categories": [(b["name"], b["break_size"]) for b in self.bcats],
            "broke": {s: sum(1 for e in rows if e["break_rank"])
                      for s, rows in self.breaks.items()},
            "feedback": len(self.feedback),
            "written_comments": sum(1 for f in self.feedback
                                    if str(f["answers"][0]["answer"] or "").strip()),
            "comments_per_judge": self._per_judge(),
        }


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="invent a tournament and describe it")
    ap.add_argument("shape", nargs="?", help="a file in shapes/")
    a = ap.parse_args()
    t = Tournament(load_shape(a.shape))
    print(json.dumps(t.summary(), indent=2))
