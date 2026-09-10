"""
Merge EvanMiya's "BPR" (Bayesian Performance Rating) metric into the 2026
prospect data files. BPR has no bulk/JSON API (EvanMiya is an R Shiny app —
all interaction happens over a live WebSocket session), so the raw data in
data/bpr_2026_raw.txt was collected by hand via the Player Ratings page's
Search box, one player at a time, using browser automation.

Usage:
    python3 scripts/merge_bpr_2026.py

Input:
    data/bpr_2026_raw.txt — one `name|team|bpr` line per player searched,
    with `NONE|NONE` recorded for confirmed non-matches (so re-running this
    script doesn't require re-scraping to know who was already checked).

Output:
    Writes college_stats.bpr into matched players in
    data/prospects/2026.json and data/prospects/2026-draft-extras.json.
    Prints match/unmatched counts and the list of still-unmatched players.
"""
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_PATH = ROOT / "data" / "bpr_2026_raw.txt"


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


# Manual name-mapping fixes: EvanMiya spelling -> our board's canonical name
ALIASES = {
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
}


def load_raw():
    raw = []
    with RAW_PATH.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split("|")
            if len(parts) != 3:
                continue
            name, team, bpr = parts
            if bpr == "NONE":
                continue
            raw.append((name, team, float(bpr)))
    return raw


def main():
    raw = load_raw()

    # dedupe, keep first occurrence; apply alias so scraped name maps to board's spelling
    seen = {}
    for name, team, bpr in raw:
        key = ALIASES.get(norm(name), norm(name))
        if key not in seen:
            seen[key] = (name, team, bpr)

    main_path = ROOT / "data" / "prospects" / "2026.json"
    extras_path = ROOT / "data" / "prospects" / "2026-draft-extras.json"
    main_data = json.loads(main_path.read_text(encoding="utf-8"))
    extras_data = json.loads(extras_path.read_text(encoding="utf-8"))
    all_prospects = main_data + extras_data

    matched, unmatched = [], []
    for p in all_prospects:
        entry = seen.get(norm(p["name"]))
        if entry:
            matched.append({"id": p["id"], "name": p["name"], "bt_name": entry[0], "team": entry[1], "bpr": entry[2]})
        else:
            unmatched.append({"id": p["id"], "name": p["name"], "school": p.get("school")})

    print(f"matched: {len(matched)} / unmatched: {len(unmatched)}")

    by_id = {m["id"]: m["bpr"] for m in matched}
    for path in (main_path, extras_path):
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

    print("\n--- still unmatched ---")
    for u in unmatched:
        print(u["name"], "|", u["school"])


if __name__ == "__main__":
    main()
