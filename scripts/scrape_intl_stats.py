#!/usr/bin/env python3
"""
Scrapes international pre-draft stats from Basketball Reference international player pages.

URL pattern: https://www.basketball-reference.com/international/players/{slug}-1.html
Table used:  player-stats-per_game-league- (regular season per-game)
             Falls back to player-stats-per_game-all- if no league table.

Picks the most recent regular-season before or in the player's draft year.

Usage:
  python3 scripts/scrape_intl_stats.py                 # all years 2013-2025
  python3 scripts/scrape_intl_stats.py --year 2018     # specific year
  python3 scripts/scrape_intl_stats.py --resume        # skip already-populated
"""

import requests
import json
import os
import re
import sys
import time
import unicodedata
from bs4 import BeautifulSoup

BASE_URL = "https://www.basketball-reference.com/international/players"
DELAY = 8  # seconds between requests — BRef asks for respectful scraping

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}

PROSPECTS_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "prospects")


# ── name helpers ────────────────────────────────────────────────────────────

def strip_diacritics(s):
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def name_to_slug(name):
    """'Luka Dončić' -> 'luka-doncic'"""
    name = strip_diacritics(name).lower().strip()
    name = re.sub(r"[^a-z ]", "", name)
    return name.replace(" ", "-")


def name_matches(search_name, page_name):
    """Fuzzy: all significant tokens of search_name appear in page_name."""
    def tokens(s):
        s = strip_diacritics(s).lower()
        s = re.sub(r"[^a-z ]", "", s)
        t = set(s.split())
        for suffix in {"jr", "sr", "ii", "iii", "iv"}:
            t.discard(suffix)
        return t
    s_t = tokens(search_name)
    p_t = tokens(page_name)
    if not s_t:
        return False
    return len(s_t & p_t) >= max(1, len(s_t) - 1)


# ── season helpers ───────────────────────────────────────────────────────────

def season_end_year(season_str):
    """
    '2017-18' -> 2018
    '14-15'   -> 2015
    '2013'    -> 2013  (single-year format used by some leagues)
    Returns None if unparseable or looks like a summary row.
    """
    s = season_str.strip()
    if not s or re.match(r"^\d+ Seasons?$", s) or s.lower() == "career":
        return None
    # "YYYY-YY" or "YY-YY"
    m = re.match(r"^\d{2,4}-(\d{2})$", s)
    if m:
        return int("20" + m.group(1))
    # Plain 4-digit year
    m = re.match(r"^(\d{4})$", s)
    if m:
        return int(m.group(1))
    return None


# ── data helpers ─────────────────────────────────────────────────────────────

def safe_float(text):
    try:
        return float((text or "").strip().replace("%", ""))
    except (ValueError, AttributeError):
        return None


# ── BRef fetch ───────────────────────────────────────────────────────────────

def fetch_bref_intl_page(name, request_counter):
    """
    Try BRef international URL slugs -{1..3} until a name match is found.
    Returns (soup, request_counter) or (None, request_counter).
    """
    slug = name_to_slug(name)

    for suffix in range(1, 4):
        if request_counter > 0:
            time.sleep(DELAY)
        request_counter += 1

        url = f"{BASE_URL}/{slug}-{suffix}.html"
        try:
            res = requests.get(url, headers=HEADERS, timeout=15)
        except Exception as e:
            print(f"    fetch error: {e}")
            continue

        if res.status_code == 404:
            break  # no more suffixes will match
        if res.status_code != 200:
            continue

        res.encoding = "utf-8"
        soup = BeautifulSoup(res.text, "lxml")
        h1 = soup.find("h1")
        page_name = h1.get_text(strip=True) if h1 else ""

        if name_matches(name, page_name):
            return soup, request_counter

    return None, request_counter


# ── stats parsing ─────────────────────────────────────────────────────────────

def parse_intl_stats(soup, draft_year):
    """
    Pull the most-recent regular season before draft_year from the per-game table.
    Returns (best_season_dict, all_seasons_list) — both in college_stats format.
    """
    table = (
        soup.find("table", id="player-stats-per_game-league-") or
        soup.find("table", id="player-stats-per_game-all-")
    )
    if not table:
        return None, []

    # Parse header
    header_row = table.find("tr")
    if not header_row:
        return None, []
    headers = [th.get_text(strip=True) for th in header_row.find_all(["th", "td"])]

    # Parse data rows
    pre_draft = []
    for row in table.find_all("tr")[1:]:
        cells = [td.get_text(strip=True) for td in row.find_all(["td", "th"])]
        if not cells or len(cells) < 5:
            continue
        season_str = cells[0]
        end_yr = season_end_year(season_str)
        if end_yr is None or end_yr > draft_year:
            continue
        row_dict = dict(zip(headers, cells))
        row_dict["_end_year"] = end_yr
        pre_draft.append(row_dict)

    if not pre_draft:
        return None, []

    pre_draft.sort(key=lambda r: r["_end_year"], reverse=True)
    best = pre_draft[0]

    all_seasons = [_build_stats(r) for r in pre_draft]
    return _build_stats(best), all_seasons


def _build_stats(row):
    """Map a BRef row dict to our college_stats field format."""
    def f(key):
        return safe_float(row.get(key))

    season = row.get("Season", "")
    team   = row.get("Team", "")
    league = row.get("League", "")

    g   = f("G")
    mp  = f("MP")
    pts = f("PTS")

    fg3m = f("3P");  fg3a = f("3PA"); fg3_pct = f("3P%")
    fg2m = f("2P");  fg2a = f("2PA"); fg2_pct = f("2P%")
    fgm  = f("FG");  fga  = f("FGA"); fg_pct  = f("FG%")
    ftm  = f("FT");  fta  = f("FTA"); ft_pct  = f("FT%")

    orb = f("ORB"); drb = f("DRB"); trb = f("TRB")
    ast = f("AST"); stl = f("STL"); blk = f("BLK")
    tov = f("TOV"); pf  = f("PF")

    s = {
        "season":     season,
        "team":       team,
        "league":     league,
        "g":          int(g) if g is not None else None,
        "mp_per_g":   mp,
        "pts_per_g":  pts,
        "fg3m_per_g": fg3m,
        "fg3a_per_g": fg3a,
        "fg3_pct":    fg3_pct,
        "fg2m_per_g": fg2m,
        "fg2a_per_g": fg2a,
        "fg2_pct":    fg2_pct,
        "ftm_per_g":  ftm,
        "fta_per_g":  fta,
        "ft_pct":     ft_pct,
        "fg_pct":     fg_pct,
        "orb_per_g":  orb,
        "drb_per_g":  drb,
        "trb_per_g":  trb,
        "ast_per_g":  ast,
        "stl_per_g":  stl,
        "blk_per_g":  blk,
        "tov_per_g":  tov,
        "pf_per_g":   pf,
    }

    # Derived stats BRef doesn't provide directly
    if fgm is not None and fg3m is not None and fga and fga > 0:
        s["efg_pct"] = round((fgm + 0.5 * fg3m) / fga, 3)
    if fg3a is not None and fga and fga > 0:
        s["fg3a_rate"] = round(fg3a / fga, 3)
    if fta is not None and fga and fga > 0:
        s["fta_rate"] = round(fta / fga, 3)
    if pts and fga and fta:
        denom = 2 * (fga + 0.44 * fta)
        if denom > 0:
            s["ts_pct"] = round(pts / denom, 3)
    if ast and tov and tov > 0:
        s["ato_ratio"] = round(ast / tov, 2)

    return {k: v for k, v in s.items() if v is not None}


# ── per-year scrape ──────────────────────────────────────────────────────────

def scrape_year(data_path, resume, request_counter):
    with open(data_path, encoding="utf-8") as f:
        prospects = json.load(f)

    if resume:
        targets = [p for p in prospects if not p.get("college_stats")]
    else:
        targets = [p for p in prospects if not p.get("college_stats")]

    if not targets:
        return 0, [], request_counter

    year = int(os.path.basename(data_path).replace(".json", ""))
    print(f"\n--- {year}: {len(targets)} missing ---")

    updated   = 0
    not_found = []

    for i, p in enumerate(targets):
        name = p["name"]
        print(f"  [{i+1}/{len(targets)}] {name}", end=" ... ", flush=True)

        soup, request_counter = fetch_bref_intl_page(name, request_counter)
        if not soup:
            print("NOT FOUND")
            not_found.append(name)
            continue

        stats, stats_all = parse_intl_stats(soup, year)
        if not stats:
            print("NO PRE-DRAFT STATS")
            not_found.append(name)
            continue

        p["college_stats"] = stats
        if stats_all:
            p["college_stats_all"] = stats_all
        updated += 1
        print(
            f"OK [{stats.get('league', '?')}] {stats.get('season', '?')} — "
            f"{stats.get('pts_per_g', '?')} pts, "
            f"{stats.get('trb_per_g', '?')} reb, "
            f"{stats.get('ast_per_g', '?')} ast"
        )

    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(prospects, f, indent=2, ensure_ascii=False)

    return updated, not_found, request_counter


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    resume = "--resume" in sys.argv

    years = [str(y) for y in range(2013, 2026)]
    for arg in sys.argv[1:]:
        if re.match(r"^\d{4}$", arg):
            years = [arg]
            break

    total_updated   = 0
    total_not_found = []
    request_counter = 0

    for year in years:
        data_path = os.path.join(PROSPECTS_DIR, f"{year}.json")
        if not os.path.exists(data_path):
            print(f"File not found: {data_path}")
            continue

        updated, not_found, request_counter = scrape_year(
            data_path, resume, request_counter
        )
        total_updated   += updated
        total_not_found += not_found

    print(f"\n=== Done ===")
    print(f"  Updated:   {total_updated}")
    print(f"  Not found: {len(total_not_found)}")
    if total_not_found:
        suffix = " ..." if len(total_not_found) > 30 else ""
        print(f"  Missing:   {', '.join(total_not_found[:30])}{suffix}")


if __name__ == "__main__":
    main()
