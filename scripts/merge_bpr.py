"""
Merge EvanMiya's "BPR" (Bayesian Performance Rating) metric into a draft
class's prospect data files, for any year.

EvanMiya has no bulk/JSON API (it's an R Shiny app; all interaction happens
over a live WebSocket session), but its Player Ratings table supports a
1000-rows-per-page view and a Year selector going back to 2009-10. The full
D1 table for a season is pulled via browser automation (set rows/page to
1000, page through, extract via DOM) and saved to
data/bpr_{year}_bulk_raw.txt before running this script.

Usage:
    python3 scripts/merge_bpr.py <year>

Input:
    data/bpr_{year}_bulk_raw.txt — one `name|team|bpr` line per D1 player in
    EvanMiya's Player Ratings table for that season.

Output:
    Writes college_stats.bpr into matched players in
    data/prospects/{year}.json (and -draft-extras.json if present).
    Prints match/unmatched counts and the list of still-unmatched players.
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Manual name-mapping fixes: EvanMiya spelling -> our board's canonical name.
# Keyed by year, then EvanMiya-normalized-name -> our-board-normalized-name.
ALIASES = {
    2017: {
        "edrice adebayo": "bam adebayo",
        "wesley iwundu": "wes iwundu",
    },
    2018: {
        "vincent edwards": "vince edwards",
        "mohamed bamba": "mo bamba",
        "sviatoslav mykhailiuk": "svi mykhailiuk",
        "hamdiou diallo": "hamidou diallo",
    },
    2019: {
        "nicolas claxton": "nic claxton",
    },
    2021: {
        "nahshon hyland": "bones hyland",
        "cameron thomas": "cam thomas",
    },
    2023: {
        'gregory "gg" jackson': "gg jackson",
    },
    2024: {
        "carlton carrington": "bub carrington",
    },
    2025: {
        "egor demin": "egor dmin",  # our board has a mangled Cyrillic 'ё' in this name
    },
    2026: {
        "cameron boozer": "cam boozer",
        "emanuel sharp": "emmanuel sharp",
        "kohl rosario": "cole rosario",
        "yaxel lendeborg": "yaxel lendoborg",
        "rueben chinyelu": "ruben chinleyu",
        "paul mcneil, jr.": "paul mcneil jr.",
        "xaivian lee": "xavian lee",
        "joseph tugler": "jojo tugler",
        "maliq brown": "malique brown",
        "dennis smith, jr.": "dennis smith jr.",
        "roddy gayle jr.": "roddy gayle",
        "khadim mboup": "kadim mboup",
        "alvaro folgueiras": "alvaro folguerias",
    },
}


def norm(s):
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = s.lower()
    s = s.replace("-", " ")
    s = re.sub(r"[.',]", "", s)
    s = re.sub(r"\b(jr|sr|ii|iii|iv)\b", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def load_raw(year):
    path = ROOT / "data" / f"bpr_{year}_bulk_raw.txt"
    raw = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split("|")
            if len(parts) != 3:
                continue
            name, team, bpr = parts
            if bpr in ("NONE", ""):
                continue
            try:
                raw.append((name, team, float(bpr)))
            except ValueError:
                continue
    return raw


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/merge_bpr.py <year>")
        sys.exit(1)
    year = int(sys.argv[1])

    raw = load_raw(year)
    aliases = ALIASES.get(year, {})

    seen = {}
    for name, team, bpr in raw:
        key = aliases.get(norm(name), norm(name))
        if key not in seen:
            seen[key] = (name, team, bpr)

    main_path = ROOT / "data" / "prospects" / f"{year}.json"
    extras_path = ROOT / "data" / "prospects" / f"{year}-draft-extras.json"
    main_data = json.loads(main_path.read_text(encoding="utf-8"))
    extras_data = json.loads(extras_path.read_text(encoding="utf-8")) if extras_path.exists() else []
    all_prospects = main_data + extras_data

    matched, unmatched = [], []
    for p in all_prospects:
        entry = seen.get(norm(p["name"]))
        if entry:
            matched.append({"id": p["id"], "name": p["name"], "bt_name": entry[0], "team": entry[1], "bpr": entry[2]})
        else:
            unmatched.append({"id": p["id"], "name": p["name"], "school": p.get("school")})

    print(f"{year}: matched {len(matched)} / unmatched {len(unmatched)} (of {len(all_prospects)})")

    by_id = {m["id"]: m["bpr"] for m in matched}
    for path in (main_path, extras_path):
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        updated = 0
        for p in data:
            if p["id"] in by_id:
                if p.get("college_stats") is None:
                    p["college_stats"] = {}
                p["college_stats"]["bpr"] = round(by_id[p["id"]], 2)
                updated += 1
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"  merged into {path.relative_to(ROOT)}: {updated} of {len(data)}")

    unmatched_str = ", ".join(f"{u['name']} ({u['school']})" for u in unmatched) or "none"
    print("  unmatched:", unmatched_str.encode("ascii", "backslashreplace").decode("ascii"))


if __name__ == "__main__":
    main()
