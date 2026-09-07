#!/usr/bin/env python3
"""
Scrapes NBA draft history from Basketball Reference for years 2013-2025.
Creates data/prospects/{year}.json for each historical class.

Usage: python3 scripts/scrape_draft_history.py
       python3 scripts/scrape_draft_history.py 2020  # single year
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
DELAY = 4  # seconds between requests — be respectful

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "prospects")


def slugify(name: str, year: int) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return f"{slug}-{year}"


def find_table(soup: BeautifulSoup, table_id: str):
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


def cell_text(row, stat: str) -> str:
    cell = row.find(["td", "th"], {"data-stat": stat})
    if not cell:
        return None
    text = cell.get_text(strip=True)
    return text if text else None


def scrape_year(year: int) -> list:
    url = f"{BASE_URL}/draft/NBA_{year}.html"
    print(f"  Fetching {url}")

    res = requests.get(url, headers=HEADERS, timeout=30)
    res.raise_for_status()

    soup = BeautifulSoup(res.text, "lxml")
    table = find_table(soup, "stats")

    if not table:
        print(f"  WARNING: No draft table found for {year}")
        return []

    prospects = []

    for row in table.find("tbody").find_all("tr"):
        # Skip repeated header rows inside tbody
        if "thead" in (row.get("class") or []):
            continue

        name = cell_text(row, "player")
        pick_raw = cell_text(row, "pick_overall")

        if not name or not pick_raw or name == "Player":
            continue

        try:
            pick_num = int(pick_raw)
        except ValueError:
            continue

        team    = cell_text(row, "team_id")
        pos     = cell_text(row, "pos")
        school  = cell_text(row, "college_name")
        rnd_raw = cell_text(row, "round_num")

        try:
            rnd = int(rnd_raw) if rnd_raw else None
        except ValueError:
            rnd = None

        prospect = {
            "id":                   slugify(name, year),
            "name":                 name,
            "draft_class":          year,
            "rank":                 pick_num,  # actual draft order for historical classes
            "position":             pos,
            "role":                 None,
            "school":               school,
            "nationality":          None,
            "age":                  None,
            "bust_risk":            None,
            "description":          None,
            "perceived_draft_range": None,
            "comparisons":          None,
            "measurements": {
                "height_no_shoes":   None,
                "height_with_shoes": None,
                "wingspan":          None,
                "weight":            None,
                "hand_length":       None,
                "hand_width":        None,
                "standing_reach":    None,
                "vertical_no_step":  None,
                "vertical_max":      None,
            },
            "stats":   {},
            "notes":   "",
            "drafted": {
                "pick":  pick_num,
                "round": rnd,
                "team":  team,
            },
        }
        prospects.append(prospect)

    return prospects


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    years = [int(sys.argv[1])] if len(sys.argv) > 1 else list(YEARS)

    for i, year in enumerate(years):
        print(f"\n[{year}]")

        out_path = os.path.join(OUT_DIR, f"{year}.json")
        if os.path.exists(out_path):
            print(f"  Already exists — skipping. Delete the file to re-scrape.")
            continue

        try:
            prospects = scrape_year(year)
            if prospects:
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(prospects, f, indent=2, ensure_ascii=False)
                print(f"  Saved {len(prospects)} players → {out_path}")
            else:
                print(f"  No data — skipping.")
        except Exception as e:
            print(f"  ERROR: {e}")

        if i < len(years) - 1:
            print(f"  Waiting {DELAY}s...")
            time.sleep(DELAY)

    print("\nDone.")


if __name__ == "__main__":
    main()
