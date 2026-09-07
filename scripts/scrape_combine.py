#!/usr/bin/env python3
"""
Scrapes NBA combine measurements via nba_api for years 2013-2025.
Merges measurements into existing data/prospects/{year}.json files.
Run AFTER scrape_draft_history.py.

Usage: python3 scripts/scrape_combine.py
       python3 scripts/scrape_combine.py 2023  # single year
"""

import json
import os
import re
import sys
import time
import warnings

warnings.filterwarnings("ignore")

from nba_api.stats.endpoints import DraftCombinePlayerAnthro, DraftCombineDrillResults

YEARS = range(2013, 2026)
DELAY = 3  # seconds between API calls

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "prospects")

# NBA API season year format: "2022-23", "2013-14", etc.
def season_str(year: int) -> str:
    return f"{year}-{str(year + 1)[-2:]}"


def normalize_name(name: str) -> str:
    name = name.lower().strip()
    name = re.sub(r"\b(jr\.?|sr\.?|ii|iii|iv)\b", "", name)
    name = re.sub(r"[^a-z\s]", "", name)
    return re.sub(r"\s+", " ", name).strip()


def safe_float(val) -> float:
    try:
        f = float(val)
        return f if f == f else None  # NaN check
    except (TypeError, ValueError):
        return None


def fetch_combine_year(year: int) -> dict:
    """Returns dict keyed by normalized player name → measurements."""
    season = season_str(year)
    print(f"  Fetching anthro data ({season})...")

    try:
        anthro_df = DraftCombinePlayerAnthro(
            season_year=season, timeout=45
        ).get_data_frames()[0]
    except Exception as e:
        print(f"  Anthro fetch failed: {e}")
        anthro_df = None

    time.sleep(DELAY)

    print(f"  Fetching drill data ({season})...")
    try:
        drill_df = DraftCombineDrillResults(
            season_year=season, timeout=45
        ).get_data_frames()[0]
    except Exception as e:
        print(f"  Drill fetch failed: {e}")
        drill_df = None

    if anthro_df is None and drill_df is None:
        return {}

    # Build measurements dict keyed by normalized name
    results = {}

    if anthro_df is not None:
        for _, row in anthro_df.iterrows():
            name = normalize_name(row.get("PLAYER_NAME", ""))
            if not name:
                continue
            results[name] = {
                "height_no_shoes":   safe_float(row.get("HEIGHT_WO_SHOES")),
                "height_with_shoes": safe_float(row.get("HEIGHT_W_SHOES")),
                "wingspan":          safe_float(row.get("WINGSPAN")),
                "weight":            safe_float(row.get("WEIGHT")),
                "hand_length":       safe_float(row.get("HAND_LENGTH")),
                "hand_width":        safe_float(row.get("HAND_WIDTH")),
                "standing_reach":    safe_float(row.get("STANDING_REACH")),
                "vertical_no_step":  None,
                "vertical_max":      None,
            }

    if drill_df is not None:
        for _, row in drill_df.iterrows():
            name = normalize_name(row.get("PLAYER_NAME", ""))
            if not name:
                continue
            verticals = {
                "vertical_no_step": safe_float(row.get("STANDING_VERTICAL_LEAP")),
                "vertical_max":     safe_float(row.get("MAX_VERTICAL_LEAP")),
            }
            if name in results:
                results[name].update(verticals)
            else:
                # Player in drills but not anthro — store partials
                results[name] = {
                    "height_no_shoes": None, "height_with_shoes": None,
                    "wingspan": None, "weight": None,
                    "hand_length": None, "hand_width": None,
                    "standing_reach": None,
                    **verticals,
                }

    return results


def merge_into_class(year: int, combine_data: dict) -> int:
    json_path = os.path.join(OUT_DIR, f"{year}.json")
    if not os.path.exists(json_path):
        print(f"  No {year}.json found — run scrape_draft_history.py first")
        return 0

    with open(json_path, encoding="utf-8") as f:
        prospects = json.load(f)

    merged = 0
    for p in prospects:
        key = normalize_name(p["name"])
        if key in combine_data:
            measurements = combine_data[key]
            # Only update fields that have actual data
            if any(v is not None for v in measurements.values()):
                p["measurements"] = measurements
                merged += 1

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(prospects, f, indent=2, ensure_ascii=False)

    return merged


def main():
    years = [int(sys.argv[1])] if len(sys.argv) > 1 else list(YEARS)

    for i, year in enumerate(years):
        print(f"\n[{year}]")
        try:
            combine_data = fetch_combine_year(year)
            if combine_data:
                merged = merge_into_class(year, combine_data)
                print(f"  Merged {merged}/{len(combine_data)} players with measurements")
            else:
                print(f"  No combine data returned")
        except Exception as e:
            print(f"  ERROR: {e}")

        if i < len(years) - 1:
            print(f"  Waiting {DELAY}s before next year...")
            time.sleep(DELAY)

    print("\nDone.")


if __name__ == "__main__":
    main()
