"""
Merge NBA.com Draft Combine Anthropometric measurements into a draft
class's prospect data files, for any year.

Source: https://www.nba.com/stats/draft/combine-anthro?SeasonYear={Y}-{Y+1}
where Y is the NBA rookie season a draft class enters — e.g. SeasonYear
2026-27 holds combine measurements for our "2026" draft class (players
measured ahead of the June 2026 draft, entering the 2026-27 season).
So: SeasonYear = f"{year}-{str(year + 1)[-2:]}".

The page renders a plain server-rendered <table> (78ish rows, one page,
no pagination), so the raw data was pulled by navigating to each year's
URL and reading the table via DOM (no scraping bypass needed).

Usage:
    python3 scripts/merge_combine.py <year>

Input:
    data/combine_{year}_raw.txt — one `|`-delimited line per combine
    participant: NAME|HAND_LENGTH|HAND_WIDTH|HEIGHT_NO_SHOES|STANDING_REACH|WEIGHT|WINGSPAN
    Height/reach/wingspan are in NBA.com's raw "6' 10.75''" feet-inches
    format (or blank/"-" when not measured); hand length/width and weight
    are already plain decimals.

Output:
    Writes measurements.{height_no_shoes, weight, wingspan, hand_length,
    hand_width, standing_reach} into matched players in
    data/prospects/{year}.json (and -draft-extras.json if present).
    Does NOT touch height_with_shoes, vertical_no_step, or vertical_max —
    those aren't sourced from this page.
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Manual name-mapping fixes: NBA.com spelling -> our board's canonical name.
ALIASES = {
    2017: {
        "edrice adebayo": "bam adebayo",
        "wesley iwundu": "wes iwundu",
        "justin jackson (unc)": "justin jackson",
    },
    2018: {
        "mohamed bamba": "mo bamba",
        "sviatoslav mykhailiuk": "svi mykhailiuk",
    },
    2019: {
        "nicolas claxton": "nic claxton",
        "cameron reddish": "cam reddish",
    },
    2020: {
        "jayden scrubb": "jay scrubb",
    },
    2021: {
        "nahshon hyland": "bones hyland",
    },
    2022: {
        "josh minnott": "josh minott",
    },
    2024: {
        "carlton carrington": "bub carrington",
        "robert dillingham": "rob dillingham",
        "alexandre sarr": "alex sarr",
    },
    2025: {
        "egor demin": "egor dmin",  # our board has a mangled Cyrillic 'ё' in this name
        "hansen yang": "yang hansen",  # NBA.com uses given-name-first order
    },
    2026: {
        "anicet dybantsa": "aj dybantsa",
        "rueben chinyelu": "ruben chinleyu",
        "yaxel lendeborg": "yaxel lendoborg",
        "emanuel sharp": "emmanuel sharp",
        "maliq brown": "malique brown",
        "christopher cenac": "chris cenac",
        "cameron boozer": "cam boozer",
        "nathaniel ament": "nate ament",
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


def parse_feet_inches(s):
    """'6' 10.75\\'\\'' -> 82.75 (total inches). Returns None if blank/invalid."""
    if not s or s.strip() in ("", "-"):
        return None
    m = re.match(r"(\d+)'\s*([\d.]+)", s.strip())
    if not m:
        return None
    feet, inches = m.groups()
    return round(int(feet) * 12 + float(inches), 2)


def parse_float(s):
    if not s or s.strip() in ("", "-"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def load_raw(year):
    path = ROOT / "data" / f"combine_{year}_raw.txt"
    raw = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            parts = line.split("|")
            if len(parts) != 7:
                continue
            name, hand_len, hand_wid, height_ns, reach, weight, wingspan = parts
            raw.append({
                "name": name,
                "hand_length": parse_float(hand_len),
                "hand_width": parse_float(hand_wid),
                "height_no_shoes": parse_feet_inches(height_ns),
                "standing_reach": parse_feet_inches(reach),
                "weight": parse_float(weight),
                "wingspan": parse_feet_inches(wingspan),
            })
    return raw


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/merge_combine.py <year>")
        sys.exit(1)
    year = int(sys.argv[1])

    raw = load_raw(year)
    aliases = ALIASES.get(year, {})

    seen = {}
    for r in raw:
        key = aliases.get(norm(r["name"]), norm(r["name"]))
        if key not in seen:
            seen[key] = r

    main_path = ROOT / "data" / "prospects" / f"{year}.json"
    extras_path = ROOT / "data" / "prospects" / f"{year}-draft-extras.json"
    main_data = json.loads(main_path.read_text(encoding="utf-8"))
    extras_data = json.loads(extras_path.read_text(encoding="utf-8")) if extras_path.exists() else []
    all_prospects = main_data + extras_data

    matched, unmatched = [], []
    for p in all_prospects:
        entry = seen.get(norm(p["name"]))
        if entry:
            matched.append({"id": p["id"], "name": p["name"], "raw_name": entry["name"], "data": entry})
        else:
            unmatched.append({"id": p["id"], "name": p["name"], "school": p.get("school")})

    print(f"{year}: matched {len(matched)} / unmatched {len(unmatched)} (of {len(all_prospects)})")

    by_id = {m["id"]: m["data"] for m in matched}
    fields = ("height_no_shoes", "weight", "wingspan", "hand_length", "hand_width", "standing_reach")
    for path in (main_path, extras_path):
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        updated = 0
        for p in data:
            if p["id"] in by_id:
                entry = by_id[p["id"]]
                if p.get("measurements") is None:
                    p["measurements"] = {}
                for f in fields:
                    if entry[f] is not None:
                        p["measurements"][f] = entry[f]
                updated += 1
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"  merged into {path.relative_to(ROOT)}: {updated} of {len(data)}")

    unmatched_str = ", ".join(f"{u['name']} ({u['school']})" for u in unmatched) or "none"
    print("  unmatched:", unmatched_str.encode("ascii", "backslashreplace").decode("ascii"))


if __name__ == "__main__":
    main()
