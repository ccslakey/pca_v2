"""
pipeline/ingest_bref_awards.py

Scrapes Baseball Reference award pages and loads into the PlayerAward model.
Also updates Player.asg_games / asg_first / asg_last from the All-Star registers.

Sources and kind values
-----------------------
Single-page scrapes (~6 requests total, excluding WS):
  mvp       /awards/mvp.shtml
  cy        /awards/cya.shtml
  roty      /awards/roy.shtml
  hof       /awards/hof.shtml         (induction year stored as year)
  tc_b      /awards/triple_crowns.shtml  table: triple_crowns_b
  tc_p      /awards/triple_crowns.shtml  table: triple_crowns_p
  postmvp   /awards/postmvp.shtml     notes = WS | ALCS | NLCS
  bat_title /awards/batting-titles.shtml
  era_title /awards/pitching-era-titles.shtml

Grid pages (2 pages each):
  gg        /awards/gold_glove_{al,nl}.shtml
  ss        /awards/silver_slugger_{al,nl}.shtml
  all_mlb   /awards/all_mlb.shtml          (single page, 1st/2nd team in league col)

All-Star career totals (2 pages, updates Player fields — no PlayerAward rows):
  asg       /allstar/bat-register.shtml + /allstar/pitch-register.shtml

World Series rosters (~120 pages — longest scrape):
  ws        /postseason/ index → winning team page per year

Usage:
  python pipeline/ingest_bref_awards.py
  python pipeline/ingest_bref_awards.py --dry-run
  python pipeline/ingest_bref_awards.py --force
  python pipeline/ingest_bref_awards.py --kinds mvp cy hof ws
  python pipeline/ingest_bref_awards.py --verbose
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from typing import Any

import django
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pca_backend.settings")
django.setup()

from bs4 import BeautifulSoup, Comment
from pybaseball.datasources.bref import BRefSession

from players.models import Player
from stats.models import IngestionLog, PlayerAward

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BREF = "https://www.baseball-reference.com"

TRANSIENT_ERRORS = (
    requests.exceptions.ConnectionError,
    requests.exceptions.Timeout,
    requests.exceptions.ChunkedEncodingError,
)

# One source key per scraper for idempotency
SOURCE_KEYS: dict[str, str] = {
    "mvp":       "bref_awards_mvp",
    "cy":        "bref_awards_cy",
    "roty":      "bref_awards_roty",
    "hof":       "bref_awards_hof",
    "tc_b":      "bref_awards_tc_b",
    "tc_p":      "bref_awards_tc_p",
    "postmvp":   "bref_awards_postmvp",
    "bat_title": "bref_awards_bat_title",
    "era_title": "bref_awards_era_title",
    "gg":        "bref_awards_gg",
    "ss":        "bref_awards_ss",
    "all_mlb":   "bref_awards_all_mlb",
    "asg":       "bref_awards_asg",
    "ws":        "bref_awards_ws",
}

ALL_KINDS = list(SOURCE_KEYS.keys())


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def fetch_with_retry(
    session: BRefSession,
    url: str,
    retries: int = 3,
    backoff: int = 20,
) -> requests.Response:
    for attempt in range(1, retries + 1):
        try:
            return session.get(url)
        except TRANSIENT_ERRORS as exc:
            if attempt == retries:
                raise
            wait = backoff * attempt
            print(f"    network error ({exc}), retrying in {wait}s ({attempt}/{retries})")
            time.sleep(wait)
    raise RuntimeError("fetch_with_retry: exhausted retries")


def find_table(soup: BeautifulSoup, table_id: str) -> BeautifulSoup | None:
    """Find a table by id, checking both visible HTML and comment-embedded tables."""
    t = soup.find("table", {"id": table_id})
    if t:
        return t
    for comment in soup.find_all(string=lambda x: isinstance(x, Comment)):
        csoup = BeautifulSoup(comment, "lxml")
        t = csoup.find("table", {"id": table_id})
        if t:
            return t
    return None


def already_ingested(source_key: str) -> bool:
    return IngestionLog.objects.filter(source=source_key, status="success").exists()


def log_success(source_key: str, rows: int) -> None:
    IngestionLog.objects.create(source=source_key, rows_loaded=rows, status="success")


def log_error(source_key: str, exc: Exception) -> None:
    IngestionLog.objects.create(
        source=source_key, rows_loaded=0, status="error", error_msg=str(exc)
    )


def known_player_ids() -> set[str]:
    """Pre-load all bbref_ids from the Player table to avoid per-row FK checks."""
    return set(Player.objects.values_list("bbref_id", flat=True))


def bbref_from_href(href: str) -> str | None:
    """Extract bbref_id from a player page href like /players/r/ruthba01.shtml."""
    m = re.search(r"/players/[a-z]/([a-z0-9]+)\.shtml$", href)
    return m.group(1) if m else None


def upsert_award(
    bbref_id: str,
    year: int,
    kind: str,
    known_ids: set[str],
    league: str | None = None,
    notes: str | None = None,
    dry_run: bool = False,
    verbose: bool = False,
) -> bool:
    """Write one PlayerAward row. Returns True if a row was created/found."""
    if bbref_id not in known_ids:
        if verbose:
            print(f"    skip {bbref_id} {year} {kind} — not in player DB")
        return False
    if dry_run:
        if verbose:
            print(f"    [dry-run] {bbref_id} {year} {kind} league={league} notes={notes}")
        return True
    PlayerAward.objects.get_or_create(
        player_id=bbref_id,
        year=year,
        kind=kind,
        league=league,
        defaults={"notes": notes},
    )
    return True


# ---------------------------------------------------------------------------
# Scraper: simple award tables (MVP, Cy Young, ROTY, HOF)
#
# These all share the same page structure:
#   <th data-stat="year_ID">2025</th>    ← year (may carry across rows)
#   <td data-append-csv="judgeaa01" ...> ← player
#   <td data-stat="lg_ID">AL</td>        ← league (absent on HOF)
# ---------------------------------------------------------------------------


def scrape_simple(
    session: BRefSession,
    url: str,
    table_id: str,
    kind: str,
    known_ids: set[str],
    has_league: bool = True,
    dry_run: bool = False,
    verbose: bool = False,
) -> int:
    print(f"  {kind}: {url}")
    resp = fetch_with_retry(session, url)
    soup = BeautifulSoup(resp.content, "lxml")
    table = find_table(soup, table_id)
    if table is None:
        print(f"  WARNING: table #{table_id} not found")
        return 0

    count = 0
    year: int | None = None

    for tr in table.select("tbody tr"):
        if "thead" in tr.get("class", []):
            continue

        # Year may reset each row (it does for MVP/CY/ROTY/HOF)
        th = tr.find("th")
        if th:
            txt = re.sub(r"\D", "", th.get_text(strip=True))
            if txt:
                year = int(txt)

        player_cell = tr.find(attrs={"data-append-csv": True})
        if not player_cell:
            continue
        bbref_id = player_cell.get("data-append-csv", "").strip()
        if not bbref_id or not year:
            continue

        league: str | None = None
        if has_league:
            lg = tr.find(attrs={"data-stat": "lg_ID"})
            if lg:
                league = lg.get_text(strip=True) or None

        if upsert_award(bbref_id, year, kind, known_ids, league=league,
                        dry_run=dry_run, verbose=verbose):
            count += 1

    return count


# ---------------------------------------------------------------------------
# Scraper: Triple Crown (batting + pitching)
#
# Table structure differs from simple awards — year and league are packed
# into the first cell text, e.g. "2012 AL".
# ---------------------------------------------------------------------------


def scrape_triple_crown(
    session: BRefSession,
    known_ids: set[str],
    dry_run: bool = False,
    verbose: bool = False,
) -> int:
    url = f"{BREF}/awards/triple_crowns.shtml"
    print(f"  tc_b/tc_p: {url}")
    resp = fetch_with_retry(session, url)
    soup = BeautifulSoup(resp.content, "lxml")

    count = 0
    for table_id, kind in [("triple_crowns_b", "tc_b"), ("triple_crowns_p", "tc_p")]:
        table = find_table(soup, table_id)
        if table is None:
            print(f"  WARNING: table #{table_id} not found")
            continue

        for tr in table.select("tr")[1:]:  # skip header row
            cells = tr.find_all(["td", "th"])
            if len(cells) < 2:
                continue

            # First cell: "2012 AL" or "1877 NL"
            first_text = cells[0].get_text(strip=True)
            m = re.match(r"(\d{4})\s+([A-Z]+)", first_text)
            if not m:
                continue
            year, league = int(m.group(1)), m.group(2)

            link = tr.find("a", href=lambda h: h and "/players/" in h)
            if not link:
                continue
            bbref_id = bbref_from_href(link["href"])
            if not bbref_id:
                continue

            if upsert_award(bbref_id, year, kind, known_ids, league=league,
                            dry_run=dry_run, verbose=verbose):
                count += 1

    return count


# ---------------------------------------------------------------------------
# Scraper: Batting Title / ERA Title
#
# Table id "titleist". No data-stat or data-append-csv — parse by position.
# Two rows per year (AL then NL). Year cell is blank on the NL row; carry
# it forward. Column order: [Year, League, Player, Team+stats].
# ---------------------------------------------------------------------------


def scrape_title_table(
    session: BRefSession,
    url: str,
    kind: str,
    known_ids: set[str],
    dry_run: bool = False,
    verbose: bool = False,
) -> int:
    print(f"  {kind}: {url}")
    resp = fetch_with_retry(session, url)
    soup = BeautifulSoup(resp.content, "lxml")
    table = find_table(soup, "titleist")
    if table is None:
        print("  WARNING: table #titleist not found")
        return 0

    count = 0
    year: int | None = None

    for tr in table.select("tr"):
        cells = tr.find_all(["td", "th"])
        if len(cells) < 3:
            continue

        # Cell 0 = year (blank on NL row — carry forward)
        year_txt = re.sub(r"\D", "", cells[0].get_text(strip=True))
        if year_txt:
            year = int(year_txt)

        if not year:
            continue

        # Cell 1 = league (AL / NL)
        league = cells[1].get_text(strip=True) or None

        # Cell 2 = player (contains the player link)
        link = cells[2].find("a", href=lambda h: h and "/players/" in h)
        if not link:
            continue
        bbref_id = bbref_from_href(link["href"])
        if not bbref_id:
            continue

        if upsert_award(bbref_id, year, kind, known_ids, league=league,
                        dry_run=dry_run, verbose=verbose):
            count += 1

    return count


# ---------------------------------------------------------------------------
# Scraper: award_grid pages (Gold Glove, Silver Slugger)
#
# No data-stat on any cell — parse positions from the header row by index.
# Header: [Year, P, C, 1B, 2B, 3B, SS, OF, OF, OF, Utility, Team]
# Data rows: first cell = "YYYY AL" year+league label, rest = position winners.
# ---------------------------------------------------------------------------


def scrape_award_grid(
    session: BRefSession,
    url: str,
    kind: str,
    known_ids: set[str],
    dry_run: bool = False,
    verbose: bool = False,
) -> int:
    print(f"  {kind}: {url}")
    resp = fetch_with_retry(session, url)
    soup = BeautifulSoup(resp.content, "lxml")
    table = find_table(soup, "award_grid")
    if table is None:
        print("  WARNING: table #award_grid not found")
        return 0

    # Build position label list from header row (skip first "Year" col)
    header_row = table.find("tr")
    header_cells = header_row.find_all(["th", "td"]) if header_row else []
    positions = [c.get_text(strip=True) for c in header_cells[1:]]  # ["P","C","1B",...]

    count = 0
    for tr in table.select("tr")[1:]:  # skip header
        cells = tr.find_all(["td", "th"])
        if not cells:
            continue

        # First cell: link text "2025 AL"
        first_link = cells[0].find("a")
        if not first_link:
            continue
        label = first_link.get_text(strip=True)
        m = re.match(r"(\d{4})\s+([A-Z]+)", label)
        if not m:
            continue
        year, league = int(m.group(1)), m.group(2)

        for i, cell in enumerate(cells[1:]):
            pos = positions[i] if i < len(positions) else None
            if pos in (None, "Team", ""):
                continue
            player_link = cell.find("a", href=lambda h: h and "/players/" in h)
            if not player_link:
                continue
            bbref_id = bbref_from_href(player_link["href"])
            if not bbref_id:
                continue
            if upsert_award(bbref_id, year, kind, known_ids, league=league,
                            notes=pos, dry_run=dry_run, verbose=verbose):
                count += 1

    return count


# ---------------------------------------------------------------------------
# Scraper: All-MLB (single page, two rows per year: 1st team and 2nd team)
#
# Table id "all_mlb". Headers: Year, Team (1st/2nd), then position columns.
# league column stores "1st" or "2nd". notes stores the position slot.
# ---------------------------------------------------------------------------


def scrape_all_mlb(
    session: BRefSession,
    known_ids: set[str],
    dry_run: bool = False,
    verbose: bool = False,
) -> int:
    url = f"{BREF}/awards/all_mlb.shtml"
    print(f"  all_mlb: {url}")
    resp = fetch_with_retry(session, url)
    soup = BeautifulSoup(resp.content, "lxml")
    table = find_table(soup, "all_mlb")
    if table is None:
        print("  WARNING: table #all_mlb not found")
        return 0

    count = 0
    year: int | None = None

    for tr in table.select("tbody tr"):
        if "thead" in tr.get("class", []):
            continue

        th = tr.find("th", attrs={"data-stat": "year"})
        if th:
            txt = re.sub(r"\D", "", th.get_text(strip=True))
            if txt:
                year = int(txt)

        team_td = tr.find("td", attrs={"data-stat": "team"})
        team_rank = team_td.get_text(strip=True) if team_td else None  # "1st" or "2nd"

        if not year or not team_rank:
            continue

        for td in tr.find_all("td"):
            pos = td.get("data-stat", "")
            if pos in ("team",):
                continue
            link = td.find("a", href=lambda h: h and "/players/" in h)
            if not link:
                continue
            bbref_id = bbref_from_href(link["href"])
            if not bbref_id:
                continue
            # Normalise position slot: "SP_1" → "SP", "OF_3" → "OF"
            pos_label = re.sub(r"_\d+$", "", pos).upper() if pos else None
            if upsert_award(bbref_id, year, "all_mlb", known_ids, league=team_rank,
                            notes=pos_label, dry_run=dry_run, verbose=verbose):
                count += 1

    return count


# ---------------------------------------------------------------------------
# Scraper: Postseason MVP
#
# Table id "postmvp". No data-stat on cells — parse by column position.
# Header: [Year, NLCS MVP, ALCS MVP, Willie Mays World Series MVP]
# → column indices: 1=NLCS, 2=ALCS, 3=WS
# ---------------------------------------------------------------------------

POSTMVP_COL_NOTES = {1: "NLCS", 2: "ALCS", 3: "WS"}


def scrape_postseason_mvp(
    session: BRefSession,
    known_ids: set[str],
    dry_run: bool = False,
    verbose: bool = False,
) -> int:
    url = f"{BREF}/awards/postmvp.shtml"
    print(f"  postmvp: {url}")
    resp = fetch_with_retry(session, url)
    soup = BeautifulSoup(resp.content, "lxml")
    table = find_table(soup, "postmvp")
    if table is None:
        print("  WARNING: table #postmvp not found")
        return 0

    count = 0
    for tr in table.select("tr")[1:]:  # skip header row
        cells = tr.find_all(["td", "th"])
        if not cells:
            continue

        year_txt = re.sub(r"\D", "", cells[0].get_text(strip=True))
        if not year_txt:
            continue
        year = int(year_txt)

        for col_idx, notes in POSTMVP_COL_NOTES.items():
            if col_idx >= len(cells):
                continue
            link = cells[col_idx].find("a", href=lambda h: h and "/players/" in h)
            if not link:
                continue
            bbref_id = bbref_from_href(link["href"])
            if not bbref_id:
                continue
            if upsert_award(bbref_id, year, "postmvp", known_ids, notes=notes,
                            dry_run=dry_run, verbose=verbose):
                count += 1

    return count


# ---------------------------------------------------------------------------
# Scraper: All-Star career totals
#
# Updates Player.asg_games / asg_first / asg_last directly.
# Processes batting and pitching registers; for two-way players, takes max.
# ---------------------------------------------------------------------------


def scrape_allstar(
    session: BRefSession,
    dry_run: bool = False,
    verbose: bool = False,
) -> int:
    urls = [
        f"{BREF}/allstar/bat-register.shtml",
        f"{BREF}/allstar/pitch-register.shtml",
    ]
    # bbref_id → (games, first, last)
    asg_data: dict[str, tuple[int, int, int]] = {}

    for url in urls:
        print(f"  asg: {url}")
        resp = fetch_with_retry(session, url)
        soup = BeautifulSoup(resp.content, "lxml")
        # Table id varies: "batting_register" or "pitching_register"
        table = soup.find("table") or find_table(soup, "batting_register") or find_table(soup, "pitching_register")
        if table is None:
            print("  WARNING: All-Star register table not found")
            continue

        for tr in table.select("tbody tr"):
            if "thead" in tr.get("class", []):
                continue
            player_cell = tr.find(attrs={"data-append-csv": True})
            if not player_cell:
                continue
            bbref_id = player_cell.get("data-append-csv", "").strip()
            if not bbref_id:
                continue

            from_td = tr.find("td", attrs={"data-stat": "year_min"})
            to_td   = tr.find("td", attrs={"data-stat": "year_max"})
            g_td    = tr.find("td", attrs={"data-stat": "G"})

            if not (from_td and to_td and g_td):
                continue

            try:
                first = int(from_td.get_text(strip=True))
                last  = int(to_td.get_text(strip=True))
                games = int(g_td.get_text(strip=True))
            except (ValueError, TypeError):
                continue

            # Merge: take most games for two-way players
            existing = asg_data.get(bbref_id)
            if existing is None or games > existing[0]:
                asg_data[bbref_id] = (games, first, last)

    if not asg_data:
        return 0

    if dry_run:
        if verbose:
            for pid, (g, f, l) in list(asg_data.items())[:5]:
                print(f"    [dry-run] {pid} asg_games={g} {f}–{l}")
        return len(asg_data)

    updated = 0
    for bbref_id, (games, first, last) in asg_data.items():
        rows = Player.objects.filter(bbref_id=bbref_id).update(
            asg_games=games, asg_first=first, asg_last=last
        )
        if rows:
            updated += 1
    return updated


# ---------------------------------------------------------------------------
# Scraper: World Series champions (roster-level)
#
# Strategy:
#   1. Fetch /postseason/ index → extract (year, winning_team_page_url)
#      for every World Series row.
#   2. For each winner, fetch /teams/{ABBREV}/{YEAR}.shtml and collect all
#      bbref_ids from the standard batting + pitching tables.
#   3. Bulk-create PlayerAward(kind='ws') for each player found.
#
# Idempotency: one IngestionLog key per WS year so --force can re-run
# individual years without re-scraping the full set.
# ---------------------------------------------------------------------------


def parse_ws_winners(session: BRefSession) -> list[tuple[int, str]]:
    """
    Returns [(year, team_page_url)] for every World Series in BRef history.
    BRef always lists the winning team first in WS rows.
    """
    url = f"{BREF}/postseason/"
    print(f"  ws index: {url}")
    resp = fetch_with_retry(session, url)
    soup = BeautifulSoup(resp.content, "lxml")
    table = find_table(soup, "postseason_series")
    if table is None:
        print("  WARNING: postseason_series table not found")
        return []

    winners: list[tuple[int, str]] = []
    for tr in table.select("tr"):
        text = tr.get_text()
        if "World Series" not in text:
            continue
        year_m = re.search(r"(\d{4}) World Series", text)
        if not year_m:
            continue
        year = int(year_m.group(1))
        # First /teams/ link = winning team season page
        team_link = tr.find("a", href=lambda h: h and "/teams/" in h)
        if not team_link:
            continue
        team_url = BREF + team_link["href"]
        winners.append((year, team_url))

    return winners


def scrape_team_roster(soup: BeautifulSoup) -> set[str]:
    """Return all bbref_ids from the batting + pitching tables on a team season page."""
    bbref_ids: set[str] = set()
    for table_id in (
        "players_standard_batting",
        "players_standard_pitching",
    ):
        table = find_table(soup, table_id)
        if table is None:
            continue
        for link in table.find_all("a", href=lambda h: h and "/players/" in h):
            bid = bbref_from_href(link["href"])
            if bid:
                bbref_ids.add(bid)
    return bbref_ids


def scrape_world_series(
    session: BRefSession,
    known_ids: set[str],
    force: bool = False,
    dry_run: bool = False,
    verbose: bool = False,
) -> int:
    winners = parse_ws_winners(session)
    print(f"  ws: {len(winners)} World Series found")

    total = 0
    for year, team_url in sorted(winners):
        source_key = f"bref_awards_ws_{year}"
        if not force and not dry_run and already_ingested(source_key):
            if verbose:
                print(f"    [{year}] already ingested, skipping")
            continue

        print(f"    [{year}] {team_url}")
        try:
            resp = fetch_with_retry(session, team_url)
            soup = BeautifulSoup(resp.content, "lxml")
            roster = scrape_team_roster(soup)
            roster &= known_ids  # only players in our DB

            if not dry_run:
                awards = [
                    PlayerAward(player_id=bid, year=year, kind="ws", league=None, notes=None)
                    for bid in roster
                ]
                PlayerAward.objects.bulk_create(awards, ignore_conflicts=True)
                log_success(source_key, len(awards))

            total += len(roster)
            if verbose:
                print(f"      {len(roster)} players")
        except Exception as exc:
            print(f"    ERROR [{year}]: {exc}")
            if not dry_run:
                log_error(source_key, exc)

    return total


# ---------------------------------------------------------------------------
# Dispatch table
# ---------------------------------------------------------------------------


def run_kind(
    kind: str,
    session: BRefSession,
    known_ids: set[str],
    force: bool,
    dry_run: bool,
    verbose: bool,
) -> int:
    if kind == "mvp":
        return scrape_simple(session, f"{BREF}/awards/mvp.shtml", "mvp", "mvp",
                             known_ids, dry_run=dry_run, verbose=verbose)
    if kind == "cy":
        return scrape_simple(session, f"{BREF}/awards/cya.shtml", "cya", "cy",
                             known_ids, dry_run=dry_run, verbose=verbose)
    if kind == "roty":
        return scrape_simple(session, f"{BREF}/awards/roy.shtml", "roy", "roty",
                             known_ids, dry_run=dry_run, verbose=verbose)
    if kind == "hof":
        return scrape_simple(session, f"{BREF}/awards/hof.shtml", "hof", "hof",
                             known_ids, has_league=False, dry_run=dry_run, verbose=verbose)
    if kind == "tc_b":
        return scrape_triple_crown(session, known_ids, dry_run=dry_run, verbose=verbose)
    if kind == "tc_p":
        # tc_b and tc_p are scraped together from the same page
        return 0
    if kind == "postmvp":
        return scrape_postseason_mvp(session, known_ids, dry_run=dry_run, verbose=verbose)
    if kind == "bat_title":
        return scrape_title_table(session, f"{BREF}/awards/batting-titles.shtml",
                                  "bat_title", known_ids, dry_run=dry_run, verbose=verbose)
    if kind == "era_title":
        return scrape_title_table(session, f"{BREF}/awards/pitching-era-titles.shtml",
                                  "era_title", known_ids, dry_run=dry_run, verbose=verbose)
    if kind == "gg":
        n = scrape_award_grid(session, f"{BREF}/awards/gold_glove_al.shtml",
                              "gg", known_ids, dry_run=dry_run, verbose=verbose)
        n += scrape_award_grid(session, f"{BREF}/awards/gold_glove_nl.shtml",
                               "gg", known_ids, dry_run=dry_run, verbose=verbose)
        return n
    if kind == "ss":
        n = scrape_award_grid(session, f"{BREF}/awards/silver_slugger_al.shtml",
                              "ss", known_ids, dry_run=dry_run, verbose=verbose)
        n += scrape_award_grid(session, f"{BREF}/awards/silver_slugger_nl.shtml",
                               "ss", known_ids, dry_run=dry_run, verbose=verbose)
        return n
    if kind == "all_mlb":
        return scrape_all_mlb(session, known_ids, dry_run=dry_run, verbose=verbose)
    if kind == "asg":
        return scrape_allstar(session, dry_run=dry_run, verbose=verbose)
    if kind == "ws":
        return scrape_world_series(session, known_ids, force=force,
                                   dry_run=dry_run, verbose=verbose)
    raise ValueError(f"Unknown kind: {kind!r}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest BRef award data")
    parser.add_argument("--dry-run", action="store_true",
                        help="Parse and print without writing to DB")
    parser.add_argument("--force", action="store_true",
                        help="Re-ingest even if already logged as successful")
    parser.add_argument("--verbose", action="store_true",
                        help="Print every award row")
    parser.add_argument("--kinds", nargs="+", choices=ALL_KINDS, default=ALL_KINDS,
                        metavar="KIND", help=f"Award kinds to ingest (default: all). "
                                             f"Choices: {', '.join(ALL_KINDS)}")
    args = parser.parse_args()

    session = BRefSession()
    known_ids = known_player_ids()
    print(f"Player DB: {len(known_ids):,} known bbref_ids")

    # tc_b and tc_p share one page; normalise to avoid double-scraping
    kinds_to_run: list[str] = []
    tc_added = False
    for k in args.kinds:
        if k in ("tc_b", "tc_p"):
            if not tc_added:
                kinds_to_run.append("tc_b")  # scraper handles both internally
                tc_added = True
        else:
            kinds_to_run.append(k)

    total = 0
    for kind in kinds_to_run:
        source_key = SOURCE_KEYS.get(kind)
        if kind == "ws":
            # WS uses per-year keys; handled inside scrape_world_series
            n = run_kind(kind, session, known_ids, args.force, args.dry_run, args.verbose)
            total += n
            continue

        if not args.force and not args.dry_run and source_key and already_ingested(source_key):
            print(f"  {kind}: already ingested — use --force to re-run")
            continue

        print(f"\n{'─' * 50}")
        try:
            n = run_kind(kind, session, known_ids, args.force, args.dry_run, args.verbose)
            total += n
            if not args.dry_run and source_key:
                log_success(source_key, n)
            print(f"  → {n} rows")
        except Exception as exc:
            print(f"  ERROR ({kind}): {exc}")
            if not args.dry_run and source_key:
                log_error(source_key, exc)

    print(f"\nDone. Total records processed: {total:,}")


if __name__ == "__main__":
    main()
