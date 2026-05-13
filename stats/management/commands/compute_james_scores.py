"""
Compute Bill James Hall of Fame scores for every player.

Three scores per role (batter / pitcher):

  * black_ink   — weighted points for league-leading finishes
  * gray_ink    — 1 pt for each top-10 finish across many categories
  * hof_monitor — calibrated composite predictor (100 = likely HOF)

All formulas use only data already in the DB (BattingSeason / PitchingSeason
/ PlayerAward / Player.primary_position). No new ingest required.

Constants below are based on Bill James's published methodology and the
Baseball Reference HOF Monitor implementation. Tweak in one place and
re-run the command — see SPOT_CHECK_JAMES_SCORES.md for instructions.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from django.core.management.base import BaseCommand
from django.db import transaction

from players.models import Player
from stats.models import BattingSeason, JamesScore, PitchingSeason, PlayerAward

# ---------------------------------------------------------------------------
# Black Ink / Gray Ink categories
# ---------------------------------------------------------------------------

# (key, weight) — weight = points awarded for leading the league
BAT_BLACK_INK_CATEGORIES = [
    ("hr", 4), ("rbi", 4), ("ba", 4),
    ("r", 3), ("h", 3), ("slg", 3),
    ("doubles", 2), ("bb", 2), ("sb", 2),
    ("g", 1), ("ab", 1), ("triples", 1),
]

# Categories ranked for Gray Ink (1 pt per top-10 finish)
BAT_GRAY_INK_CATEGORIES = [
    "hr", "rbi", "ba", "r", "h", "slg", "obp",
    "doubles", "triples", "bb", "sb", "g", "ab", "ops", "tb",
]

PIT_BLACK_INK_CATEGORIES = [
    ("w", 4), ("era", 4), ("so", 4),
    ("ip", 3), ("whip", 3),
    ("gs", 2), ("cg", 2), ("sho", 2),
    ("g", 1), ("sv", 1),
]

PIT_GRAY_INK_CATEGORIES = [
    "w", "era", "so", "ip", "whip", "gs", "cg", "sho", "g", "sv",
]

# Rate stats: only qualified players (≥502 PA / ≥162 IP) eligible
RATE_BAT_CATEGORIES = {"ba", "obp", "slg", "ops"}
RATE_PIT_CATEGORIES = {"era", "whip"}
LOWER_IS_BETTER     = {"era", "whip"}

QUAL_PA      = 502
QUAL_IP_OUTS = 162 * 3  # 486 outs ≈ 162 IP

# ---------------------------------------------------------------------------
# Aggregation: combine stints into one full-season row per (player, year)
# ---------------------------------------------------------------------------

def _aggregate_batting() -> dict[tuple[int, str | None], dict[str, dict]]:
    """Return {(year, league): {player_id: full-season totals}}."""
    by_year: dict = defaultdict(dict)

    raw_by_pyear: dict = defaultdict(lambda: {
        "pa": 0, "ab": 0, "r": 0, "h": 0, "doubles": 0, "triples": 0,
        "hr": 0, "rbi": 0, "sb": 0, "bb": 0, "tb": 0, "g": 0,
        "obp_x_pa": 0.0, "slg_x_ab": 0.0, "ops_x_pa": 0.0,
        "rate_pa": 0, "rate_ab": 0, "league": None,
    })

    for s in BattingSeason.objects.values(
        "player_id", "year", "league",
        "games", "plate_appearances", "at_bats", "runs", "hits",
        "doubles", "triples", "home_runs", "rbi", "stolen_bases",
        "walks", "total_bases", "on_base_pct", "slugging_pct", "ops",
    ):
        k = (s["player_id"], s["year"])
        a = raw_by_pyear[k]
        pa = s["plate_appearances"] or 0
        ab = s["at_bats"] or 0
        a["pa"]      += pa
        a["ab"]      += ab
        a["r"]       += s["runs"] or 0
        a["h"]       += s["hits"] or 0
        a["doubles"] += s["doubles"] or 0
        a["triples"] += s["triples"] or 0
        a["hr"]      += s["home_runs"] or 0
        a["rbi"]     += s["rbi"] or 0
        a["sb"]      += s["stolen_bases"] or 0
        a["bb"]      += s["walks"] or 0
        a["tb"]      += s["total_bases"] or 0
        a["g"]       += s["games"] or 0
        if s["on_base_pct"] is not None and pa:
            a["obp_x_pa"] += s["on_base_pct"] * pa
            a["rate_pa"]  += pa
        if s["ops"] is not None and pa:
            a["ops_x_pa"] += s["ops"] * pa
        if s["slugging_pct"] is not None and ab:
            a["slg_x_ab"] += s["slugging_pct"] * ab
            a["rate_ab"]  += ab
        # Take the player's primary league (first stint encountered)
        if a["league"] is None:
            a["league"] = s["league"]

    # Reshape into {(year, league): {pid: row}}
    for (pid, year), a in raw_by_pyear.items():
        league = a["league"]
        ab, pa = a["ab"], a["pa"]
        rate_pa, rate_ab = a["rate_pa"], a["rate_ab"]
        row = {
            "hr": a["hr"], "rbi": a["rbi"], "r": a["r"], "h": a["h"],
            "doubles": a["doubles"], "triples": a["triples"],
            "bb": a["bb"], "sb": a["sb"], "g": a["g"],
            "ab": ab, "tb": a["tb"], "pa": pa,
            "ba":  (a["h"] / ab) if ab > 0 else None,
            "obp": (a["obp_x_pa"] / rate_pa) if rate_pa > 0 else None,
            "slg": (a["slg_x_ab"] / rate_ab) if rate_ab > 0 else None,
            "ops": (a["ops_x_pa"] / rate_pa) if rate_pa > 0 else None,
        }
        by_year[(year, league)][pid] = row
    return by_year


def _aggregate_pitching() -> dict[tuple[int, str | None], dict[str, dict]]:
    by_year: dict = defaultdict(dict)
    raw: dict = defaultdict(lambda: {
        "w": 0, "g": 0, "gs": 0, "cg": 0, "sho": 0, "sv": 0,
        "ip_outs": 0, "h_allowed": 0, "er": 0, "bb": 0, "so": 0,
        "league": None,
    })
    for s in PitchingSeason.objects.values(
        "player_id", "year", "league",
        "wins", "games", "games_started", "complete_games", "sho", "saves",
        "ip_outs", "hits_allowed", "earned_runs", "walks", "strikeouts",
    ):
        k = (s["player_id"], s["year"])
        a = raw[k]
        a["w"]   += s["wins"] or 0
        a["g"]   += s["games"] or 0
        a["gs"]  += s["games_started"] or 0
        a["cg"]  += s["complete_games"] or 0
        a["sho"] += s["sho"] or 0
        a["sv"]  += s["saves"] or 0
        a["ip_outs"]   += s["ip_outs"] or 0
        a["h_allowed"] += s["hits_allowed"] or 0
        a["er"]        += s["earned_runs"] or 0
        a["bb"]        += s["walks"] or 0
        a["so"]        += s["strikeouts"] or 0
        if a["league"] is None:
            a["league"] = s["league"]

    for (pid, year), a in raw.items():
        league = a["league"]
        ip_outs = a["ip_outs"]
        ip = ip_outs / 3.0 if ip_outs > 0 else 0.0
        row = {
            "w": a["w"], "g": a["g"], "gs": a["gs"],
            "cg": a["cg"], "sho": a["sho"], "sv": a["sv"],
            "so": a["so"], "ip": ip_outs, "ip_outs": ip_outs,
            "era": (a["er"] * 9.0 / ip) if ip > 0 else None,
            "whip": ((a["bb"] + a["h_allowed"]) / ip) if ip > 0 else None,
        }
        by_year[(year, league)][pid] = row
    return by_year


# ---------------------------------------------------------------------------
# Black / Gray Ink scoring
# ---------------------------------------------------------------------------

def _ink_scores(
    annual: dict[tuple[int, str | None], dict[str, dict]],
    black_categories: list[tuple[str, int]],
    gray_categories: list[str],
    qual_field: str,
    qual_threshold: int,
    rate_categories: set[str],
) -> tuple[dict[str, int], dict[str, int]]:
    black: dict[str, int] = defaultdict(int)
    gray:  dict[str, int] = defaultdict(int)

    for (_year, _league), players in annual.items():
        if not players:
            continue
        for cat, weight in black_categories:
            ranked = _rank_for_category(players, cat, qual_field, qual_threshold, rate_categories)
            if ranked:
                black[ranked[0][0]] += weight
        for cat in gray_categories:
            ranked = _rank_for_category(players, cat, qual_field, qual_threshold, rate_categories)
            for pid, _ in ranked[:10]:
                gray[pid] += 1
    return black, gray


def _rank_for_category(
    players: dict[str, dict],
    cat: str,
    qual_field: str,
    qual_threshold: int,
    rate_categories: set[str],
) -> list[tuple[str, float]]:
    """Return [(pid, value)] sorted best→worst, qualifier-filtered for rate stats."""
    pairs: list[tuple[str, float]] = []
    is_rate = cat in rate_categories
    for pid, row in players.items():
        v = row.get(cat)
        if v is None:
            continue
        if is_rate and (row.get(qual_field) or 0) < qual_threshold:
            continue
        pairs.append((pid, v))
    if not pairs:
        return []
    reverse = cat not in LOWER_IS_BETTER
    pairs.sort(key=lambda x: x[1], reverse=reverse)
    return pairs


# ---------------------------------------------------------------------------
# HOF Monitor — Batters
# ---------------------------------------------------------------------------

def _hof_monitor_batter(
    career: dict,
    seasons: list[dict],
    awards: dict[str, int],
    primary_position: str | None,
) -> int:
    pts = 0

    # --- Batting average (career, requires meaningful career) ---
    if career["ab"] >= 4000:
        ba = career["h"] / career["ab"]
        if ba >= 0.330: pts += 50
        elif ba >= 0.315: pts += 25
        elif ba >= 0.300: pts += 10

    # --- Hits (career milestones) ---
    h = career["h"]
    if h >= 3500:    pts += 50
    elif h >= 3000:  pts += 30
    elif h >= 2500:  pts += 10

    # --- 200-hit seasons (cap at 4 = 12 pts) ---
    pts += 3 * min(4, sum(1 for s in seasons if s["h"] >= 200))

    # --- Doubles, triples ---
    if career["doubles"] >= 600: pts += 50
    if career["triples"] >= 175: pts += 40

    # --- Home runs ---
    hr = career["hr"]
    if hr >= 600:    pts += 100
    elif hr >= 500:  pts += 75
    elif hr >= 400:  pts += 50
    elif hr >= 300:  pts += 20
    elif hr >= 250:  pts += 10
    elif hr >= 200:  pts += 5

    # --- 50+ HR / 40+ HR seasons ---
    pts += 5 * sum(1 for s in seasons if s["hr"] >= 50)
    pts += 1 * sum(1 for s in seasons if s["hr"] >= 40 and s["hr"] < 50)

    # --- RBI ---
    rbi = career["rbi"]
    if rbi >= 1850:  pts += 70
    elif rbi >= 1500: pts += 40
    elif rbi >= 1250: pts += 20

    # --- 100 RBI seasons (cap at 8) ---
    pts += min(8, sum(1 for s in seasons if s["rbi"] >= 100))

    # --- Runs ---
    r = career["r"]
    if r >= 1750:    pts += 20
    elif r >= 1500:  pts += 10

    # --- 100 R seasons (cap at 8) ---
    pts += min(8, sum(1 for s in seasons if s["r"] >= 100))

    # --- Stolen bases ---
    sb = career["sb"]
    if sb >= 600:    pts += 25
    elif sb >= 300:  pts += 5

    # --- Awards ---
    pts += 8 * awards.get("mvp", 0)
    pts += min(20, 3 * awards.get("asg", 0))           # cap All-Star at 20
    pts += 2 * awards.get("gg", 0)                      # uncapped Gold Gloves
    pts += 6 * awards.get("bat_title", 0)               # batting titles
    pts += 6 if awards.get("ws", 0) > 0 else 0          # WS championship: flat 6

    # --- Position bonus (defensive difficulty) ---
    if primary_position == "C":
        pts += 60
    elif primary_position in {"2B", "SS", "3B"}:
        pts += 30
    elif primary_position == "CF":
        pts += 15

    return pts


# ---------------------------------------------------------------------------
# HOF Monitor — Pitchers
# ---------------------------------------------------------------------------

def _hof_monitor_pitcher(
    career: dict,
    seasons: list[dict],
    awards: dict[str, int],
) -> int:
    pts = 0

    # --- Wins ---
    w = career["w"]
    if w >= 300:    pts += 100
    elif w >= 275:  pts += 50
    elif w >= 250:  pts += 40
    elif w >= 200:  pts += 25

    # --- ERA (career, requires real workload) ---
    if career["ip_outs"] >= 1500 * 3:  # ≥1500 IP
        era = (career["er"] * 9.0 / (career["ip_outs"] / 3.0)) if career["ip_outs"] else None
        if era is not None:
            if era <= 2.50:    pts += 60
            elif era <= 2.75:  pts += 40
            elif era <= 3.00:  pts += 25
            elif era <= 3.25:  pts += 15

    # --- Strikeouts ---
    so = career["so"]
    if so >= 3000:    pts += 50
    elif so >= 2500:  pts += 30
    elif so >= 2000:  pts += 10

    # --- Saves (closers) ---
    sv = career["sv"]
    if sv >= 600:    pts += 40
    elif sv >= 400:  pts += 25
    elif sv >= 300:  pts += 10

    # --- 20-win seasons ---
    pts += 4 * sum(1 for s in seasons if s["w"] >= 20)

    # --- Career win pct (requires real workload) ---
    decisions = career["w"] + career["l"]
    if decisions >= 200:
        win_pct = career["w"] / decisions
        if win_pct >= 0.625: pts += 25
        elif win_pct >= 0.575: pts += 10

    # --- Awards ---
    pts += 8 * awards.get("cy", 0)
    pts += 25 * awards.get("mvp", 0)                  # pitcher MVPs are huge
    pts += min(15, 3 * awards.get("asg", 0))          # cap All-Star at 15
    pts += 6 if awards.get("ws", 0) > 0 else 0

    return pts


# ---------------------------------------------------------------------------
# Career totals + per-season list
# ---------------------------------------------------------------------------

def _batter_career_and_seasons(
    annual: dict[tuple[int, str | None], dict[str, dict]],
) -> tuple[dict[str, dict], dict[str, list[dict]]]:
    career: dict[str, dict] = defaultdict(lambda: {
        "h": 0, "ab": 0, "doubles": 0, "triples": 0, "hr": 0,
        "rbi": 0, "r": 0, "sb": 0, "bb": 0, "g": 0, "tb": 0, "pa": 0,
    })
    seasons: dict[str, list[dict]] = defaultdict(list)
    for (_y, _l), players in annual.items():
        for pid, row in players.items():
            c = career[pid]
            c["h"]       += row["h"]
            c["ab"]      += row["ab"]
            c["doubles"] += row["doubles"]
            c["triples"] += row["triples"]
            c["hr"]      += row["hr"]
            c["rbi"]     += row["rbi"]
            c["r"]       += row["r"]
            c["sb"]      += row["sb"]
            c["bb"]      += row["bb"]
            c["g"]       += row["g"]
            c["tb"]      += row["tb"]
            c["pa"]      += row["pa"]
            seasons[pid].append(row)
    return career, seasons


def _pitcher_career_and_seasons(
    annual: dict[tuple[int, str | None], dict[str, dict]],
) -> tuple[dict[str, dict], dict[str, list[dict]]]:
    career: dict[str, dict] = defaultdict(lambda: {
        "w": 0, "l": 0, "g": 0, "gs": 0, "cg": 0, "sho": 0, "sv": 0,
        "ip_outs": 0, "so": 0, "er": 0,
    })
    seasons: dict[str, list[dict]] = defaultdict(list)
    # We need wins AND losses + earned runs at the season level
    losses_er: dict[tuple[str, int], dict[str, int]] = defaultdict(lambda: {"l": 0, "er": 0})
    for s in PitchingSeason.objects.values("player_id", "year", "losses", "earned_runs"):
        k = (s["player_id"], s["year"])
        losses_er[k]["l"]  += s["losses"] or 0
        losses_er[k]["er"] += s["earned_runs"] or 0

    for (year, _l), players in annual.items():
        for pid, row in players.items():
            extra = losses_er.get((pid, year), {"l": 0, "er": 0})
            c = career[pid]
            c["w"]       += row["w"]
            c["l"]       += extra["l"]
            c["g"]       += row["g"]
            c["gs"]      += row["gs"]
            c["cg"]      += row["cg"]
            c["sho"]     += row["sho"]
            c["sv"]      += row["sv"]
            c["so"]      += row["so"]
            c["ip_outs"] += row["ip_outs"]
            c["er"]      += extra["er"]
            seasons[pid].append(row)
    return career, seasons


# ---------------------------------------------------------------------------
# Awards lookup
# ---------------------------------------------------------------------------

def _awards_per_player() -> dict[str, dict[str, int]]:
    """Return {player_id: {kind: count}}."""
    out: dict[str, dict[str, int]] = defaultdict(dict)
    for r in PlayerAward.objects.values("player_id", "kind"):
        d = out[r["player_id"]]
        d[r["kind"]] = d.get(r["kind"], 0) + 1
    return out


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------

class Command(BaseCommand):
    help = "Compute Bill James HOF Monitor + Black Ink + Gray Ink for every player."

    def handle(self, *args, **options) -> None:
        self.stdout.write("Aggregating batting seasons...")
        bat_annual = _aggregate_batting()
        self.stdout.write(f"  {sum(len(p) for p in bat_annual.values()):,} player-seasons")

        self.stdout.write("Aggregating pitching seasons...")
        pit_annual = _aggregate_pitching()
        self.stdout.write(f"  {sum(len(p) for p in pit_annual.values()):,} player-seasons")

        self.stdout.write("Computing batter Black/Gray Ink...")
        black_bat, gray_bat = _ink_scores(
            bat_annual, BAT_BLACK_INK_CATEGORIES, BAT_GRAY_INK_CATEGORIES,
            qual_field="pa", qual_threshold=QUAL_PA, rate_categories=RATE_BAT_CATEGORIES,
        )

        self.stdout.write("Computing pitcher Black/Gray Ink...")
        black_pit, gray_pit = _ink_scores(
            pit_annual, PIT_BLACK_INK_CATEGORIES, PIT_GRAY_INK_CATEGORIES,
            qual_field="ip_outs", qual_threshold=QUAL_IP_OUTS, rate_categories=RATE_PIT_CATEGORIES,
        )

        self.stdout.write("Computing HOF Monitor (batters)...")
        bat_career, bat_seasons = _batter_career_and_seasons(bat_annual)
        awards = _awards_per_player()
        positions = {p.bbref_id: p.primary_position for p in Player.objects.only("bbref_id", "primary_position")}
        hof_bat: dict[str, int] = {}
        for pid, c in bat_career.items():
            hof_bat[pid] = _hof_monitor_batter(c, bat_seasons[pid], awards.get(pid, {}), positions.get(pid))

        self.stdout.write("Computing HOF Monitor (pitchers)...")
        pit_career, pit_seasons = _pitcher_career_and_seasons(pit_annual)
        hof_pit: dict[str, int] = {}
        for pid, c in pit_career.items():
            hof_pit[pid] = _hof_monitor_pitcher(c, pit_seasons[pid], awards.get(pid, {}))

        # Combine all player ids that have any score
        all_pids = set(bat_career) | set(pit_career)

        self.stdout.write(f"Persisting scores for {len(all_pids):,} players...")
        with transaction.atomic():
            JamesScore.objects.all().delete()
            JamesScore.objects.bulk_create([
                JamesScore(
                    player_id=pid,
                    black_ink_bat=black_bat.get(pid, 0),
                    gray_ink_bat=gray_bat.get(pid, 0),
                    hof_monitor_bat=hof_bat.get(pid, 0),
                    black_ink_pit=black_pit.get(pid, 0),
                    gray_ink_pit=gray_pit.get(pid, 0),
                    hof_monitor_pit=hof_pit.get(pid, 0),
                )
                for pid in all_pids
            ], batch_size=1000)

        self.stdout.write(self.style.SUCCESS(f"Done. Computed {len(all_pids):,} JamesScore rows."))
