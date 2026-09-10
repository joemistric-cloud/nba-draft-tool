"""
Scrape Bart Torvik's "Adjusted PORPAGATU!" (PRPG!) metric for every player in the
current draft class who played NCAA basketball in their draft year, and match them
to data/prospects/{year}.json entries by name (with a small manual override table
for known spelling/nickname mismatches between our board and Bart Torvik's data).

Source: https://barttorvik.com/getadvstats.php (the JSON endpoint behind the
T-Rank Player Finder at https://barttorvik.com/playerstat.php). Column index 28
in each player row is confirmed (via barttorvik's own playerstat*.js) to be
"Adjusted PORPAGATU!", labeled "PRPG!" in their UI.

Usage:
    python3 scripts/scrape_porpagatu.py 2026

Output:
    data/porpagatu_{year}.json — {"matched": [...], "unmatched": [...]}
    Each matched entry: {id, name, school, bt_name, bt_team, bt_conf, gp, adj_porpagatu}

Does NOT modify data/prospects/{year}.json — this is a standalone collection step.
"""
import json
import re
import sys
import time
import unicodedata
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
HEADERS = {"User-Agent": "Mozilla/5.0 (nba-draft-tool personal research script)"}

# Manual overrides for name/spelling mismatches between our board and Bart Torvik.
# Keyed by our prospect id -> (bart torvik player name, bart torvik team name).
MANUAL_OVERRIDES = {
    2026: {
        "cam-boozer-2026": ("Cameron Boozer", "Duke"),
        "yaxel-lendoborg-2026": ("Yaxel Lendeborg", "Michigan"),
        "ruben-chinleyu-2026": ("Rueben Chinyelu", "Florida"),
        "malique-brown-2026": ("Maliq Brown", "Duke"),
        "anthony-robinson-ii-2026": ("Anthony Robinson II", "Missouri"),
        "xavian-lee-2026": ("Xaivian Lee", "Florida"),
        "taylor-bol-bowen-2026": ("Taylor Bol Bowen", "Alabama"),
        "paul-mcneil-jr-2026": ("Paul McNeil, Jr.", "N.C. State"),
        "emmanuel-sharp-2026": ("Emanuel Sharp", "Houston"),
        "jojo-tugler-2026": ("Joseph Tugler", "Houston"),
        "cole-rosario-2026": ("Kohl Rosario", "Kansas"),
    }
}


def norm(s):
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = s.lower()
    s = s.replace("-", " ")
    s = re.sub(r"[.'']", "", s)
    s = re.sub(r"\b(jr|sr|ii|iii|iv)\b", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def fetch_advstats(year: int):
    url = "https://barttorvik.com/getadvstats.php"
    params = {
        "year": year,
        "specialSource": 0,
        "conyes": 0,
        "start": f"{year - 1}1101",
        "end": f"{year}0501",
        "top": 365,
        "xvalue": "All",
        "page": "playerstat",
        "team": "",
    }
    resp = requests.get(url, params=params, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()


def load_prospects(year: int):
    prospects = []
    main_path = ROOT / "data" / "prospects" / f"{year}.json"
    if main_path.exists():
        prospects += json.loads(main_path.read_text(encoding="utf-8"))
    extras_path = ROOT / "data" / "prospects" / f"{year}-draft-extras.json"
    if extras_path.exists():
        prospects += json.loads(extras_path.read_text(encoding="utf-8"))
    return prospects


def match(prospects, bt_rows, year: int):
    by_name = {}
    by_last = {}
    for row in bt_rows:
        by_name.setdefault(norm(row[0]), []).append(row)
        parts = norm(row[0]).split()
        if parts:
            by_last.setdefault(parts[-1], []).append(row)

    overrides = MANUAL_OVERRIDES.get(year, {})
    matched, unmatched = [], []

    for p in prospects:
        row = None

        if p["id"] in overrides:
            bt_name, bt_team = overrides[p["id"]]
            row = next((r for r in bt_rows if r[0] == bt_name and r[1] == bt_team), None)

        if row is None:
            candidates = by_name.get(norm(p["name"]), [])
            school_norm = norm(p.get("school") or "")
            if len(candidates) == 1:
                row = candidates[0]
            elif len(candidates) > 1 and school_norm:
                exact = [r for r in candidates if norm(r[1]) == school_norm]
                if len(exact) == 1:
                    row = exact[0]

        if row is None and p.get("school"):
            parts = norm(p["name"]).split()
            if parts:
                candidates = by_last.get(parts[-1], [])
                school_norm = norm(p["school"])
                exact = [r for r in candidates if norm(r[1]) == school_norm]
                if len(exact) == 1:
                    row = exact[0]

        if row is not None:
            matched.append({
                "id": p["id"],
                "name": p["name"],
                "school": p.get("school"),
                "bt_name": row[0],
                "bt_team": row[1],
                "bt_conf": row[2],
                "gp": row[3],
                "adj_porpagatu": row[28],
            })
        else:
            unmatched.append({"id": p["id"], "name": p["name"], "school": p.get("school")})

    return matched, unmatched


def main():
    year = int(sys.argv[1]) if len(sys.argv) > 1 else 2026
    print(f"Fetching Bart Torvik advanced stats for {year}...")
    bt_rows = fetch_advstats(year)
    time.sleep(1)  # be polite
    print(f"  {len(bt_rows)} NCAA player-seasons returned")

    prospects = load_prospects(year)
    print(f"Loaded {len(prospects)} prospects from data/prospects/{year}(.json / -draft-extras.json)")

    matched, unmatched = match(prospects, bt_rows, year)
    print(f"Matched {len(matched)} / unmatched {len(unmatched)}")

    out_path = ROOT / "data" / f"porpagatu_{year}.json"
    out_path.write_text(
        json.dumps({"matched": matched, "unmatched": unmatched}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
