#!/usr/bin/env python3
"""
Backfills position data from Basketball Reference for all historical draft classes.
- Fetches each year's draft page to get player profile URLs (13 requests)
- Fetches each player's profile page to extract position (one per player)
- Updates data/prospects/{year}.json in place — only touches the position field

Usage: python3 scripts/backfill_positions.py
"""

import requests
import json
import os
import re
import time
from bs4 import BeautifulSoup, Comment

BASE_URL = "https://www.basketball-reference.com"
YEARS = range(2013, 2026)
DRAFT_DELAY = 6    # between draft page fetches
PROFILE_DELAY = 3  # between individual player profile fetches
RATE_LIMIT_BACKOFF = 90  # seconds to wait after a 429

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "prospects")


def get(url, retries=2):
    for attempt in range(retries + 1):
        res = requests.get(url, headers=HEADERS, timeout=30)
        if res.status_code == 429:
            if attempt < retries:
                print(f"    429 rate limited — waiting {RATE_LIMIT_BACKOFF}s...")
                time.sleep(RATE_LIMIT_BACKOFF)
                continue
        res.raise_for_status()
        return res
    res.raise_for_status()
    return res


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


def get_profile_urls(year):
    """Fetch draft page, return {name: profile_url} for all players."""
    url = f"{BASE_URL}/draft/NBA_{year}.html"
    print(f"  Fetching draft page: {url}")
    soup = BeautifulSoup(get(url).text, "lxml")
    table = find_table(soup, "stats")
    if not table:
        print(f"  WARNING: No stats table found for {year}")
        return {}

    mapping = {}
    for row in table.find("tbody").find_all("tr"):
        if "thead" in (row.get("class") or []):
            continue
        player_cell = row.find(["td", "th"], {"data-stat": "player"})
        if not player_cell:
            continue
        name = player_cell.get_text(strip=True)
        link = player_cell.find("a")
        if name and link and link.get("href"):
            mapping[name] = BASE_URL + link["href"]

    return mapping


def get_position(profile_url):
    """Fetch player profile page, return position string or None."""
    soup = BeautifulSoup(get(profile_url).text, "lxml")
    meta = soup.find("div", id="meta")
    if not meta:
        return None
    # Position is in a <p> containing "Position:" text
    for p in meta.find_all("p"):
        text = p.get_text()
        if "Position:" in text:
            # Extract just the position value (e.g. "Point Guard", "Small Forward")
            # BRef uses full names; map to conventional abbreviations
            pos_text = text.split("Position:")[-1].split("▪")[0].split("Shoots:")[0].strip()
            return abbreviate(pos_text)
    return None


def abbreviate(pos_text):
    """Convert BRef full position name to conventional abbreviation."""
    mapping = {
        "point guard": "PG",
        "shooting guard": "SG",
        "small forward": "SF",
        "power forward": "PF",
        "center": "C",
        "guard": "G",
        "forward": "F",
        "guard-forward": "SG",
        "forward-guard": "SF",
        "forward-center": "PF",
        "center-forward": "C",
    }
    # BRef sometimes lists "Point Guard and Shooting Guard" — take primary (first)
    primary = pos_text.split(" and ")[0].strip().lower()
    if primary in mapping:
        return mapping[primary]
    for k, v in mapping.items():
        if k in primary:
            return v
    return pos_text if pos_text else None


def normalize(name):
    return re.sub(r"[^a-z0-9 ]", "", name.lower()).strip()


def main():
    total_updated = 0
    total_players = 0

    for i, year in enumerate(YEARS):
        print(f"\n[{year}]")
        out_path = os.path.join(OUT_DIR, f"{year}.json")

        if not os.path.exists(out_path):
            print(f"  No file found — skipping.")
            continue

        with open(out_path, encoding="utf-8") as f:
            prospects = json.load(f)

        # Get profile URLs from draft page
        try:
            profile_urls = get_profile_urls(year)
        except Exception as e:
            print(f"  ERROR fetching draft page: {e}")
            if i < len(list(YEARS)) - 1:
                time.sleep(DRAFT_DELAY)
            continue

        print(f"  Found {len(profile_urls)} profile URLs, {len(prospects)} players in file")

        # Build normalized name → url lookup
        norm_urls = {normalize(name): url for name, url in profile_urls.items()}

        updated = 0
        unmatched = []

        for j, p in enumerate(prospects):
            # Skip if already has a position
            if p.get("position"):
                continue

            key = normalize(p["name"])
            profile_url = norm_urls.get(key)

            if not profile_url:
                unmatched.append(p["name"])
                continue

            try:
                pos = get_position(profile_url)
                if pos:
                    p["position"] = pos
                    updated += 1
                    print(f"    [{j+1}/{len(prospects)}] {p['name']} → {pos}")
                else:
                    print(f"    [{j+1}/{len(prospects)}] {p['name']} → no position found")
            except Exception as e:
                print(f"    [{j+1}/{len(prospects)}] {p['name']} → ERROR: {e}")

            time.sleep(PROFILE_DELAY)

        # Save updated file
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(prospects, f, indent=2, ensure_ascii=False)

        print(f"  Saved. Updated {updated}/{len(prospects)} players.")
        if unmatched:
            print(f"  Unmatched names: {', '.join(unmatched[:5])}" +
                  (" ..." if len(unmatched) > 5 else ""))

        total_updated += updated
        total_players += len(prospects)

        if i < len(list(YEARS)) - 1:
            print(f"  Waiting {DRAFT_DELAY}s before next year...")
            time.sleep(DRAFT_DELAY)

    print(f"\nDone. Updated {total_updated}/{total_players} total players.")


if __name__ == "__main__":
    main()
