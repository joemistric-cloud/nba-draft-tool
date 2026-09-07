"""
Writes inferred `position` for historical prospects (2013-2025) that are
missing it. Logic and thresholds match scripts/infer_position_dryrun.py,
reviewed and approved by the user 2026-09-07 -- see that script's docstring
for the reasoning. Does NOT touch 2026.json (current class positions are
assigned manually via the Big Board UI, not inferred).

Categories written:
  - "PG" / "C": confident stat-shape match (assist/rebound ratio), with a
    height sanity check when height is available.
  - "Wing": everything else that has a usable stat signal but isn't a
    confident PG/C call -- SG/SF/PF/smallball-PF are not reliably
    separable from assist/rebound/height alone, so they're grouped rather
    than force-split.
  - Left null: no NBA stats, no college stats, no measurements at all --
    nothing to infer from.
"""

import json
import glob
import sys

sys.stdout.reconfigure(encoding="utf-8")

PG_HEIGHT_MAX = 77.0
C_HEIGHT_MIN = 81.0
WING_EXCLUDE = {"Brandon Ingram", "Justin Jackson", "Tyrese Martin"}


def classify(ast, trb, blk=None):
    if ast is None or trb is None:
        return None
    if ast >= 4.0 and trb <= 4.5 and ast > trb * 1.3:
        return "PG"
    if trb >= 6.0 and ast <= 2.0 and trb > ast * 2.5:
        if blk is not None and blk < 0.3:
            return None
        return "C"
    return None


def get_signal(p):
    st = p.get("stats") or {}
    if st.get("ast_per_g") is not None and st.get("trb_per_g") is not None:
        cls = classify(st["ast_per_g"], st["trb_per_g"])
        if cls:
            return cls, st["ast_per_g"], st["trb_per_g"]

    cs = p.get("college_stats") or {}
    if cs.get("ast_per_g") is not None and cs.get("trb_per_g") is not None:
        cls = classify(cs["ast_per_g"], cs["trb_per_g"], cs.get("blk_per_g"))
        if cls:
            return cls, cs["ast_per_g"], cs["trb_per_g"]

    return None, None, None


def has_any_signal(p):
    st = p.get("stats") or {}
    cs = p.get("college_stats") or {}
    return (st.get("ast_per_g") is not None and st.get("trb_per_g") is not None) or \
           (cs.get("ast_per_g") is not None and cs.get("trb_per_g") is not None)


counts = {"PG": 0, "C": 0, "Wing": 0, "unassigned": 0}

files = sorted(glob.glob("data/prospects/201*.json")) + sorted(glob.glob("data/prospects/202[0-5].json"))
for f in files:
    with open(f, encoding="utf-8") as fh:
        data = json.load(fh)

    changed = False
    for p in data:
        if p.get("position"):
            continue

        cls, ast, trb = get_signal(p)
        height = (p.get("measurements") or {}).get("height_no_shoes")

        if cls and p["name"] not in WING_EXCLUDE:
            height_agrees = True
            if height is not None:
                if cls == "PG" and height > PG_HEIGHT_MAX:
                    height_agrees = False
                if cls == "C" and height < C_HEIGHT_MIN:
                    height_agrees = False
            if height_agrees:
                p["position"] = cls
                counts[cls] += 1
                changed = True
                continue

        # Not a confident PG/C -> Wing if there's any usable signal at all
        if has_any_signal(p):
            p["position"] = "Wing"
            counts["Wing"] += 1
            changed = True
        else:
            counts["unassigned"] += 1

    if changed:
        with open(f, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
            fh.write("\n")

print(f"PG assigned:   {counts['PG']}")
print(f"C assigned:    {counts['C']}")
print(f"Wing assigned: {counts['Wing']}")
print(f"Left unassigned (no signal): {counts['unassigned']}")
