"""
Dry-run: conservative PG/C inference for prospects missing `position`.

Signal priority: NBA career per-game stats (reflects actual pro role) first,
falling back to college stats when NBA stats aren't available. Height is a
secondary sanity check, not a requirement (some players lack measurements).

NBA `stats` has no block/steal rate, so the NBA-stats signal is
assists-vs-rebounds shape only. `college_stats` has blk_per_g, used as an
extra confirming signal for centers when available.

Deliberately conservative: anything that doesn't clearly clear a threshold
is left alone (no position assigned) -- matches the SG/SF/PF middle being
harder to call automatically. This only PRINTS a report; it does not write
to any data file.
"""

import json
import glob
import sys

sys.stdout.reconfigure(encoding="utf-8")

PG_HEIGHT_MAX = 77.0   # 6'5"
C_HEIGHT_MIN = 81.0    # 6'9"


def classify(ast, trb, blk=None):
    """Returns 'PG', 'C', or None based on per-game rate shape."""
    if ast is None or trb is None:
        return None
    if ast >= 4.0 and trb <= 4.5 and ast > trb * 1.3:
        return "PG"
    if trb >= 6.0 and ast <= 2.0 and trb > ast * 2.5:
        if blk is not None and blk < 0.3:
            return None  # rebounds without blocks/assists is ambiguous (PF-ish)
        return "C"
    return None


def get_signal(p):
    """Returns (classification, source, ast, trb, blk) or (None, None, ...)."""
    st = p.get("stats") or {}
    if st.get("ast_per_g") is not None and st.get("trb_per_g") is not None:
        cls = classify(st["ast_per_g"], st["trb_per_g"])
        if cls:
            return cls, "nba", st["ast_per_g"], st["trb_per_g"], None

    cs = p.get("college_stats") or {}
    if cs.get("ast_per_g") is not None and cs.get("trb_per_g") is not None:
        cls = classify(cs["ast_per_g"], cs["trb_per_g"], cs.get("blk_per_g"))
        if cls:
            return cls, "college", cs["ast_per_g"], cs["trb_per_g"], cs.get("blk_per_g")

    return None, None, None, None, None


results = {"PG": [], "C": []}
flagged = []
total_missing = 0

files = sorted(glob.glob("data/prospects/201*.json")) + sorted(glob.glob("data/prospects/202[0-5].json"))
for f in files:
    year = f.split("\\")[-1].split("/")[-1].replace(".json", "")
    with open(f, encoding="utf-8") as fh:
        data = json.load(fh)
    for p in data:
        if p.get("position"):
            continue
        total_missing += 1
        cls, source, ast, trb, blk = get_signal(p)
        if not cls:
            continue

        height = (p.get("measurements") or {}).get("height_no_shoes")
        height_agrees = True
        if height is not None:
            if cls == "PG" and height > PG_HEIGHT_MAX:
                height_agrees = False
            if cls == "C" and height < C_HEIGHT_MIN:
                height_agrees = False

        row = {
            "name": p["name"], "year": year, "source": source,
            "ast": ast, "trb": trb, "blk": blk, "height": height,
        }
        if height_agrees:
            results[cls].append(row)
        else:
            row["would_be"] = cls
            flagged.append(row)

print(f"Total players missing position: {total_missing}\n")

for pos in ("PG", "C"):
    rows = results[pos]
    print(f"=== {pos} — {len(rows)} candidates ===")
    for r in rows:
        h = f"{r['height']:.1f}in" if r["height"] else "no height"
        print(f"  {r['name']:<28} {r['year']}  [{r['source']:<7}] ast={r['ast']:.1f} trb={r['trb']:.1f}"
              + (f" blk={r['blk']:.1f}" if r["blk"] is not None else "") + f"  ({h})")
    print()

print(f"=== FLAGGED (stat signal present but height disagrees) — {len(flagged)} ===")
for r in flagged:
    print(f"  {r['name']:<28} {r['year']}  would be {r['would_be']}, but height={r['height']:.1f}in"
          f"  [{r['source']}] ast={r['ast']:.1f} trb={r['trb']:.1f}")

WING_EXCLUDE = {"Brandon Ingram", "Justin Jackson", "Tyrese Martin"}

# Anything with a stat signal that isn't a confident PG/C call (including
# players flagged for height mismatch -- smallball PFs like Aaron Gordon,
# Julius Randle, Pascal Siakam) becomes "Wing": SG/SF/PF/smallball-PF are
# not reliably separable from assist/rebound/height alone, so per the
# user's call, group them rather than force a fragile split.
wing_from_flagged = [r for r in flagged if r["name"] not in WING_EXCLUDE]

c_final = [r for r in results["C"] if r["name"] not in WING_EXCLUDE]
wing_from_c_errors = [r for r in results["C"] if r["name"] in WING_EXCLUDE]

wing_count = len(wing_from_flagged) + len(wing_from_c_errors)
# residual = everyone missing position, with a usable signal, not in PG/C/flagged
residual_wing_count = 0
files2 = sorted(glob.glob("data/prospects/201*.json")) + sorted(glob.glob("data/prospects/202[0-5].json"))
classified_names = {r["name"] for r in results["PG"]} | {r["name"] for r in c_final} | {r["name"] for r in flagged}
for f in files2:
    with open(f, encoding="utf-8") as fh:
        data = json.load(fh)
    for p in data:
        if p.get("position") or p["name"] in classified_names:
            continue
        st = p.get("stats") or {}
        cs = p.get("college_stats") or {}
        has_signal = (st.get("ast_per_g") is not None and st.get("trb_per_g") is not None) or \
                     (cs.get("ast_per_g") is not None and cs.get("trb_per_g") is not None)
        if has_signal:
            residual_wing_count += 1

total_wing = wing_count + residual_wing_count
total_classified = len(results["PG"]) + len(c_final)

print()
print(f"=== FINAL PLAN ===")
print(f"  PG:   {len(results['PG'])}")
print(f"  C:    {len(c_final)}  (excluded {len(WING_EXCLUDE)} misclassified wings: {', '.join(WING_EXCLUDE)})")
print(f"  Wing: {total_wing}  ({len(wing_from_flagged)} smallball-PF/height-flagged + {len(wing_from_c_errors)} reclassified + {residual_wing_count} SG/SF/PF-shaped residual)")
print(f"  Left unassigned: {total_missing - len(results['PG']) - len(c_final) - total_wing} (no usable signal at all)")
