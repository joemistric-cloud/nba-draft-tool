#!/usr/bin/env /usr/bin/python3
"""
Scrapes 2025-26 college stats for 2026 draft prospects from Sports Reference CBB.
Updates college_stats field in data/prospects/2026.json.

Source: sports-reference.com/cbb — per game + advanced tables.
Stats captured (more complete than historical BRef scrape):
  Per game:  g, mp_per_g, pts_per_g, trb_per_g, orb_per_g, drb_per_g,
             ast_per_g, stl_per_g, blk_per_g, tov_per_g, pf_per_g,
             fg_pct, fg2_pct, fg2a_per_g, fg3_pct, fg3a_per_g,
             ft_pct, fta_per_g, efg_pct
  Advanced:  per, ts_pct, fg3a_per_fga_pct (3PAr), fta_per_fga_pct (FTr),
             usg_pct, ast_pct, stl_pct, blk_pct, tov_pct, orb_pct, drb_pct,
             obpm, dbpm, bpm, ws, ws_per_40
  Derived:   ato_ratio, fg3a_rate (alias), fta_rate (alias)

Usage:
  python3 scripts/scrape_2026_college_stats.py           # all unscraped prospects
  python3 scripts/scrape_2026_college_stats.py --resume  # skip already-populated
"""

import requests
import json
import os
import re
import sys
import time
from bs4 import BeautifulSoup, Comment

CBB_BASE = "https://www.sports-reference.com"
SEARCH_URL = CBB_BASE + "/cbb/search/search.fcgi?search={}"
DELAY = 6  # seconds between requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "prospects", "2026.json")


def find_table(soup, tid):
    t = soup.find("table", id=tid)
    if t:
        return t
    for comment in soup.find_all(string=lambda x: isinstance(x, Comment)):
        if f'id="{tid}"' in comment:
            inner = BeautifulSoup(comment, "lxml")
            t = inner.find("table", id=tid)
            if t:
                return t
    return None


def cell_val(row, stat):
    cell = row.find(["td", "th"], {"data-stat": stat})
    if not cell:
        return None
    text = cell.get_text(strip=True)
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return text


def normalize(name):
    return re.sub(r"[^a-z0-9 ]", "", name.lower()).strip()


def search_cbb(name, school):
    """Search SR CBB for a player. Returns player page URL or None."""
    query = name.replace(" ", "+")
    url = SEARCH_URL.format(query)
    res = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)

    # Direct redirect to player page
    if "/cbb/players/" in res.url:
        return res.url

    # Search results page — look for matching player
    soup = BeautifulSoup(res.text, "lxml")
    results = soup.select("div.search-item")
    if not results:
        return None

    school_norm = normalize(school or "")

    for item in results:
        name_el = item.select_one("div.search-item-name a")
        if not name_el:
            continue
        desc = item.get_text(" ", strip=True).lower()
        href = name_el.get("href", "")
        if "/cbb/players/" not in href:
            continue
        # Prefer result that mentions the school
        if school_norm and any(w in desc for w in school_norm.split() if len(w) > 3):
            return CBB_BASE + href
        # Fall back to first player result
    # If no school match, return first player result
    for item in results:
        name_el = item.select_one("div.search-item-name a")
        if name_el and "/cbb/players/" in name_el.get("href", ""):
            return CBB_BASE + name_el["href"]

    return None


def scrape_player(url):
    """Fetch a CBB player page and return combined college_stats dict."""
    res = requests.get(url, headers=HEADERS, timeout=15)
    if res.status_code != 200:
        return None

    soup = BeautifulSoup(res.text, "lxml")

    pg_table  = find_table(soup, "players_per_game")
    adv_table = find_table(soup, "players_advanced")

    if not pg_table:
        return None

    # Get the most recent season row from per-game table
    def last_data_row(table):
        rows = [r for r in table.find("tbody").find_all("tr")
                if "thead" not in (r.get("class") or []) and "tfoot" not in (r.get("class") or [])]
        return rows[-1] if rows else None

    pg_row  = last_data_row(pg_table)
    adv_row = last_data_row(adv_table) if adv_table else None

    if not pg_row:
        return None

    def pg(stat):  return cell_val(pg_row,  stat)
    def adv(stat): return cell_val(adv_row, stat) if adv_row else None

    # Season + school label
    season_cell = pg_row.find(["td", "th"], {"data-stat": "year_id"})
    school_cell = pg_row.find(["td", "th"], {"data-stat": "team_name_abbr"})
    season = season_cell.get_text(strip=True) if season_cell else None
    school = school_cell.get_text(strip=True) if school_cell else None

    s = {
        "season":     season,
        "school":     school,
        # Per game
        "g":          pg("games"),
        "mp_per_g":   pg("mp_per_g"),
        "pts_per_g":  pg("pts_per_g"),
        "trb_per_g":  pg("trb_per_g"),
        "orb_per_g":  pg("orb_per_g"),
        "drb_per_g":  pg("drb_per_g"),
        "ast_per_g":  pg("ast_per_g"),
        "stl_per_g":  pg("stl_per_g"),
        "blk_per_g":  pg("blk_per_g"),
        "tov_per_g":  pg("tov_per_g"),
        "pf_per_g":   pg("pf_per_g"),
        # Shooting (per game provides 2P% and 2PA directly — better than derivation)
        "fg_pct":     pg("fg_pct"),
        "fg2_pct":    pg("fg2_pct"),
        "fg2a_per_g": pg("fg2a_per_g"),
        "fg3_pct":    pg("fg3_pct"),
        "fg3a_per_g": pg("fg3a_per_g"),
        "ft_pct":     pg("ft_pct"),
        "fta_per_g":  pg("fta_per_g"),
        "efg_pct":    pg("efg_pct"),
        # Advanced
        "per":        adv("per"),
        "ts_pct":     adv("ts_pct"),
        "fg3a_rate":  adv("fg3a_per_fga_pct"),   # 3PAr
        "fta_rate":   adv("fta_per_fga_pct"),     # FTr
        "usg_pct":    adv("usg_pct"),
        "ast_pct":    adv("ast_pct"),
        "stl_pct":    adv("stl_pct"),
        "blk_pct":    adv("blk_pct"),
        "tov_pct":    adv("tov_pct"),
        "orb_pct":    adv("orb_pct"),
        "drb_pct":    adv("drb_pct"),
        "obpm":       adv("obpm"),
        "dbpm":       adv("dbpm"),
        "bpm":        adv("bpm"),
        "ws":         adv("ws"),
        "ws_per_40":  adv("ws_per_40"),
    }

    # Derived: A/TO ratio
    ast = s.get("ast_per_g")
    tov = s.get("tov_per_g")
    if ast is not None and tov and tov > 0:
        s["ato_ratio"] = round(ast / tov, 2)

    # Strip nulls
    return {k: v for k, v in s.items() if v is not None}


def main():
    resume = "--resume" in sys.argv

    with open(DATA_PATH, encoding="utf-8") as f:
        prospects = json.load(f)

    updated = 0
    skipped = 0
    not_found = []

    for i, p in enumerate(prospects):
        if resume and p.get("college_stats"):
            skipped += 1
            continue

        name = p["name"]
        school = p.get("school", "")

        print(f"[{i+1}/{len(prospects)}] {name} ({school})", end=" ... ", flush=True)

        if i > 0:
            time.sleep(DELAY)

        try:
            player_url = search_cbb(name, school)
            if not player_url:
                print("NOT FOUND")
                not_found.append(name)
                continue

            stats = scrape_player(player_url)
            if not stats:
                print("NO STATS")
                not_found.append(name)
                continue

            p["college_stats"] = stats
            updated += 1
            print(f"OK — {stats.get('pts_per_g','?')} pts, {stats.get('trb_per_g','?')} reb, {stats.get('ast_per_g','?')} ast")

        except Exception as e:
            print(f"ERROR: {e}")
            not_found.append(name)

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(prospects, f, indent=2, ensure_ascii=False)

    print(f"\n=== Done ===")
    print(f"  Updated:   {updated}")
    print(f"  Skipped:   {skipped} (already had stats)")
    print(f"  Not found: {len(not_found)}")
    if not_found:
        print(f"  Missing:   {', '.join(not_found[:20])}" + (" ..." if len(not_found) > 20 else ""))


if __name__ == "__main__":
    main()
