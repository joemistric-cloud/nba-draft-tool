#!/usr/bin/env python3
"""
Scrapes college stats from individual Basketball Reference player pages.
Stores results as college_stats (final college season) and college_stats_all
(every college season) in data/prospects/{year}.json.

Source: all_college_stats table on each player's BRef page.

Phase 1 — extract BRef player page links from draft pages (13 requests, fast).
Phase 2 — hit each player page for college stats (1 request per player, slow).

Stats captured per season:
  Box (per game): pts, trb, ast, stl, blk, tov, pf, mp, g
  Shooting:       fg_pct, fg3_pct, ft_pct, fg3a_per_g, fta_per_g
  Totals:         fg, fga, fg3, fg3a, ft, fta, orb, trb (used for derived)

Derived stats (computed):
  fg2_pct     — 2-point FG% = (fg - fg3) / (fga - fg3a)
  fg2a_per_g  — 2PA per game
  fg3a_rate   — 3PA as share of FGA (3-point attempt rate)
  fta_rate    — FTA / FGA (measures drawing contact)
  efg_pct     — effective FG% = (fg + 0.5 * fg3) / fga
  ts_pct      — true shooting % = pts / (2 * (fga + 0.44 * fta))
  ato_ratio   — assist-to-turnover ratio (from season totals)
  drb         — defensive rebounds (trb - orb)
  drb_per_g   — DRB per game
  orb_per_g   — ORB per game

Usage:
  python3 scripts/scrape_college_stats.py           # all years 2013-2025
  python3 scripts/scrape_college_stats.py 2020      # single year
  python3 scripts/scrape_college_stats.py --resume  # skip players who already have college_stats
"""

import requests
import json
import os
import re
import sys
import time
from bs4 import BeautifulSoup, Comment

BASE_URL = "https://www.basketball-reference.com"
YEARS = range(2013, 2026)

# Phase 1 is fast (draft page per year). Phase 2 is slow (player page per player).
DELAY_DRAFT_PAGE = 5   # between draft page requests
DELAY_PLAYER_PAGE = 8  # between individual player page requests — be respectful

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "prospects")


# ── helpers ─────────────────────────────────────────────────────────────────

def normalize(name):
    return re.sub(r"[^a-z0-9 ]", "", name.lower()).strip()


def find_table(soup, table_id):
    """Find a table by ID, including inside HTML comments (BRef pattern)."""
    table = soup.find("table", id=table_id)
    if table:
        return table
    for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
        if f'id="{table_id}"' in comment:
            inner = BeautifulSoup(comment, "lxml")
            table = inner.find("table", id=table_id)
            if table:
                return table
    return None


def cell_text(row, stat):
    cell = row.find(["td", "th"], {"data-stat": stat})
    if not cell:
        return None
    return cell.get_text(strip=True) or None


def cell_float(row, stat):
    val = cell_text(row, stat)
    if val is None:
        return None
    try:
        return float(val)
    except ValueError:
        return None


def fetch(url, label=""):
    res = requests.get(url, headers=HEADERS, timeout=30)
    if res.status_code == 429:
        raise Exception(f"429 Too Many Requests — {url}")
    res.raise_for_status()
    return res


# ── Phase 1: extract BRef player links from draft pages ─────────────────────

def get_player_links_for_year(year):
    """Returns {normalized_name: bref_path} for all picks in a draft year."""
    url = f"{BASE_URL}/draft/NBA_{year}.html"
    res = fetch(url, str(year))
    soup = BeautifulSoup(res.text, "lxml")
    table = find_table(soup, "stats")
    if not table:
        print(f"  WARNING: no stats table for {year}")
        return {}

    links = {}
    for row in table.find("tbody").find_all("tr"):
        if "thead" in (row.get("class") or []):
            continue
        name_cell = row.find(["td", "th"], {"data-stat": "player"})
        if not name_cell:
            continue
        name = name_cell.get_text(strip=True)
        if not name or name == "Player":
            continue
        a = name_cell.find("a")
        if a and a.get("href"):
            links[normalize(name)] = a["href"]

    return links


# ── Phase 2: scrape college stats from individual player pages ───────────────

def parse_college_season(row):
    """
    Parse one row of the all_college_stats table.
    Returns a dict of raw and derived stats, or None if the row is unusable.
    """
    season = cell_text(row, "season")
    school = cell_text(row, "college_id")
    if not season:
        return None

    # Totals — used for derived stats
    g   = cell_float(row, "g")
    mp  = cell_float(row, "mp")
    fg  = cell_float(row, "fg")
    fga = cell_float(row, "fga")
    fg3 = cell_float(row, "fg3")
    fg3a = cell_float(row, "fg3a")
    ft  = cell_float(row, "ft")
    fta = cell_float(row, "fta")
    orb = cell_float(row, "orb")
    trb = cell_float(row, "trb")
    ast = cell_float(row, "ast")
    stl = cell_float(row, "stl")
    blk = cell_float(row, "blk")
    tov = cell_float(row, "tov")
    pf  = cell_float(row, "pf")
    pts = cell_float(row, "pts")

    # Skip rows with no meaningful data
    if g is None or g == 0:
        return None

    # Per-game (from BRef's own computed columns)
    mp_per_g  = cell_float(row, "mp_per_g")
    pts_per_g = cell_float(row, "pts_per_g")
    trb_per_g = cell_float(row, "trb_per_g")
    ast_per_g = cell_float(row, "ast_per_g")

    # Shooting percentages
    fg_pct  = cell_float(row, "fg_pct")
    fg3_pct = cell_float(row, "fg3_pct")
    ft_pct  = cell_float(row, "ft_pct")

    s = {
        "season": season,
        "school": school,
        "g":         g,
        "mp_per_g":  mp_per_g,
        "pts_per_g": pts_per_g,
        "trb_per_g": trb_per_g,
        "ast_per_g": ast_per_g,
        "fg_pct":    fg_pct,
        "fg3_pct":   fg3_pct,
        "ft_pct":    ft_pct,
    }

    # Per-game for counting stats not in BRef's pre-computed columns
    def pg(total):
        if total is not None and g:
            return round(total / g, 2)
        return None

    s["stl_per_g"] = pg(stl)
    s["blk_per_g"] = pg(blk)
    s["tov_per_g"] = pg(tov)
    s["pf_per_g"]  = pg(pf)
    s["orb_per_g"] = pg(orb)

    drb = (trb - orb) if (trb is not None and orb is not None) else None
    s["drb_per_g"] = pg(drb)

    # 3-point attempt rate (share of FGA that are 3s)
    if fga and fga > 0 and fg3a is not None:
        s["fg3a_per_g"] = round(fg3a / g, 2) if g else None
        s["fg3a_rate"]  = round(fg3a / fga, 3)

    # FTA rate (FTA per FGA — measures aggression / drawing contact)
    if fga and fga > 0 and fta is not None:
        s["fta_per_g"] = round(fta / g, 2) if g else None
        s["fta_rate"]  = round(fta / fga, 3)

    # 2-point shooting
    fg2a = (fga - fg3a) if (fga is not None and fg3a is not None) else None
    fg2  = (fg  - fg3)  if (fg  is not None and fg3  is not None) else None
    if fg2a and fg2a > 0 and fg2 is not None:
        s["fg2_pct"]    = round(fg2 / fg2a, 3)
        s["fg2a_per_g"] = round(fg2a / g, 2) if g else None

    # eFG%
    if fga and fga > 0 and fg is not None and fg3 is not None:
        s["efg_pct"] = round((fg + 0.5 * fg3) / fga, 3)

    # TS%
    if pts is not None and fga is not None and fta is not None and (fga + 0.44 * fta) > 0:
        s["ts_pct"] = round(pts / (2 * (fga + 0.44 * fta)), 3)

    # A/TO ratio (from season totals)
    if ast is not None and tov and tov > 0:
        s["ato_ratio"] = round(ast / tov, 2)

    # Strip None values for cleaner JSON
    return {k: v for k, v in s.items() if v is not None}


def get_college_stats(bref_path):
    """
    Fetches a player's BRef page and returns:
      final_season  — dict of stats for their last college season
      all_seasons   — list of dicts, one per college season (chronological)
    Returns (None, []) if no college stats found.
    """
    url = BASE_URL + bref_path
    res = fetch(url)
    soup = BeautifulSoup(res.text, "lxml")

    table = find_table(soup, "all_college_stats")
    if not table:
        return None, []

    seasons = []
    for row in table.find("tbody").find_all("tr"):
        if "thead" in (row.get("class") or []):
            continue
        parsed = parse_college_season(row)
        if parsed:
            seasons.append(parsed)

    if not seasons:
        return None, []

    return seasons[-1], seasons  # last season = final college year


# ── Main ─────────────────────────────────────────────────────────────────────

def load_prospects(year):
    path = os.path.join(OUT_DIR, f"{year}.json")
    if not os.path.exists(path):
        return None, path
    with open(path, encoding="utf-8") as f:
        return json.load(f), path


def save_prospects(prospects, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(prospects, f, indent=2, ensure_ascii=False)


def main():
    resume = "--resume" in sys.argv
    year_args = [a for a in sys.argv[1:] if not a.startswith("--")]
    years_to_run = [int(year_args[0])] if year_args else list(YEARS)

    # ── Phase 1: collect BRef player links for all target years ──────────────
    print("Phase 1: collecting player page links from draft pages...")
    all_links = {}  # normalized_name -> bref_path
    for i, year in enumerate(years_to_run):
        print(f"  {year}...", end=" ", flush=True)
        try:
            links = get_player_links_for_year(year)
            all_links.update(links)
            print(f"{len(links)} players")
        except Exception as e:
            print(f"ERROR: {e}")
        if i < len(years_to_run) - 1:
            time.sleep(DELAY_DRAFT_PAGE)

    print(f"\nTotal player links collected: {len(all_links)}")

    # ── Phase 2: scrape college stats per player ──────────────────────────────
    print("\nPhase 2: scraping individual player pages for college stats...")

    total_updated = 0
    total_skipped = 0
    total_no_college = 0
    request_count = 0

    for year in years_to_run:
        prospects, path = load_prospects(year)
        if prospects is None:
            print(f"\n[{year}] No file — skipping.")
            continue

        print(f"\n[{year}] {len(prospects)} players")
        year_updated = 0

        for p in prospects:
            name_key = normalize(p["name"])

            # Resume mode: skip players who already have college stats
            if resume and p.get("college_stats"):
                total_skipped += 1
                continue

            bref_path = all_links.get(name_key)
            if not bref_path:
                print(f"    NO LINK: {p['name']}")
                continue

            if request_count > 0:
                time.sleep(DELAY_PLAYER_PAGE)

            try:
                final_season, all_seasons = get_college_stats(bref_path)
                request_count += 1

                if final_season:
                    p["college_stats"] = final_season
                    if len(all_seasons) > 1:
                        p["college_stats_all"] = all_seasons
                    year_updated += 1
                    total_updated += 1
                    print(f"    OK: {p['name']} ({final_season.get('season','?')} @ {final_season.get('school','?')})"
                          f" — {final_season.get('pts_per_g','?')} pts, {final_season.get('trb_per_g','?')} reb, {final_season.get('ast_per_g','?')} ast")
                else:
                    print(f"    NO COLLEGE STATS: {p['name']} (international?)")
                    total_no_college += 1

            except Exception as e:
                print(f"    ERROR {p['name']}: {e}")

        save_prospects(prospects, path)
        print(f"  Saved {year}. Updated {year_updated}/{len(prospects)} players.")

    print(f"\n=== Done ===")
    print(f"  Updated:       {total_updated}")
    print(f"  No college:    {total_no_college} (international players expected)")
    print(f"  Skipped:       {total_skipped} (already had stats, resume mode)")
    print(f"  Total requests: {request_count}")


if __name__ == "__main__":
    main()
