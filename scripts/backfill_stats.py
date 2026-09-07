#!/usr/bin/env python3
"""
Backfills career NBA stats from Basketball Reference draft pages.
Stats come from the same draft page used for history — no extra per-player requests.
Updates data/prospects/{year}.json in place — only touches the stats field.

Stats captured (career totals/averages as of BRef snapshot):
  seasons, g, mp, pts, trb, ast,
  fg_pct, fg3_pct, ft_pct,
  mp_per_g, pts_per_g, trb_per_g, ast_per_g,
  ws, ws_per_48, bpm, vorp

Usage: python3 scripts/backfill_stats.py
       python3 scripts/backfill_stats.py 2020   # single year
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
DELAY = 8  # conservative — we'll be hitting BRef again after positions

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "prospects")

STAT_FIELDS = [
    "seasons", "g", "mp",
    "pts", "trb", "ast",
    "fg_pct", "fg3_pct", "ft_pct",
    "mp_per_g", "pts_per_g", "trb_per_g", "ast_per_g",
    "ws", "ws_per_48", "bpm", "vorp",
]


def find_table(soup, table_id):
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
        return text  # keep strings like seasons count


def normalize(name):
    return re.sub(r"[^a-z0-9 ]", "", name.lower()).strip()


def scrape_year_stats(year):
    url = f"{BASE_URL}/draft/NBA_{year}.html"
    print(f"  Fetching {url}")

    res = requests.get(url, headers=HEADERS, timeout=30)
    if res.status_code == 429:
        raise Exception("429 Too Many Requests")
    res.raise_for_status()

    soup = BeautifulSoup(res.text, "lxml")
    table = find_table(soup, "stats")
    if not table:
        print(f"  WARNING: No stats table found")
        return {}

    stats_by_name = {}
    for row in table.find("tbody").find_all("tr"):
        if "thead" in (row.get("class") or []):
            continue
        name_cell = row.find(["td", "th"], {"data-stat": "player"})
        if not name_cell:
            continue
        name = name_cell.get_text(strip=True)
        if not name or name == "Player":
            continue

        stats = {}
        for field in STAT_FIELDS:
            val = cell_val(row, field)
            if val is not None:
                stats[field] = val

        if stats:
            stats_by_name[normalize(name)] = stats

    return stats_by_name


def main():
    years_arg = [int(sys.argv[1])] if len(sys.argv) > 1 else list(YEARS)

    total_updated = 0
    total_players = 0

    for i, year in enumerate(years_arg):
        print(f"\n[{year}]")
        out_path = os.path.join(OUT_DIR, f"{year}.json")

        if not os.path.exists(out_path):
            print(f"  No file found — skipping.")
            continue

        with open(out_path, encoding="utf-8") as f:
            prospects = json.load(f)

        try:
            stats_map = scrape_year_stats(year)
        except Exception as e:
            print(f"  ERROR: {e}")
            if i < len(years_arg) - 1:
                print(f"  Waiting {DELAY}s...")
                time.sleep(DELAY)
            continue

        print(f"  Got stats for {len(stats_map)} players from BRef")

        updated = 0
        for p in prospects:
            key = normalize(p["name"])
            if key in stats_map:
                p["stats"] = stats_map[key]
                updated += 1

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(prospects, f, indent=2, ensure_ascii=False)

        print(f"  Saved. Updated {updated}/{len(prospects)} players.")
        total_updated += updated
        total_players += len(prospects)

        if i < len(years_arg) - 1:
            print(f"  Waiting {DELAY}s...")
            time.sleep(DELAY)

    print(f"\nDone. Updated {total_updated}/{total_players} total players.")


if __name__ == "__main__":
    main()
