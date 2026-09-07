#!/usr/bin/env python3
"""
Import a headerless CSV export from Google Sheets into the prospects JSON format.

Column order (no headers):
  0: Name
  1: School / Club
  2: Bust Risk
  3: Description
  4, 5, 6: Blank (ignored)
  7: Draft Range
  8: Comparisons

Usage: python3 scripts/import_csv.py path/to/sheet.csv 2026
"""

import csv
import json
import sys
import os
import re

BUST_RISK_ORDER = [
    "None", "Very Low", "Low", "Low Mid", "Mid", "Upper Mid", "High", "Very High"
]

BUST_RISK_NORMALIZE = {
    "NONE":           "None",
    "VERY LOW":       "Very Low",
    "LOW":            "Low",
    "LOW MID":        "Low Mid",
    "LOWER MID":      "Low Mid",       # non-standard → Low Mid
    "MID":            "Mid",
    "UPPER MID":      "Upper Mid",
    "UPPER MID/HIGH": "Upper Mid",     # non-standard → closer to Upper Mid
    "HIGH":           "High",
    "VERY HIGH":      "Very High",
}

# Words to keep uppercase regardless of length (school abbreviations, suffixes, etc.)
KEEP_UPPER = {
    "BYU", "UNC", "NBL", "UCLA", "USC", "LSU", "TCU", "VCU", "SMU",
    "UAB", "UNLV", "UTEP", "UConn", "UCONN", "PNR", "II", "III", "IV",
    "NBA", "AJ", "VJ", "TJ", "DJ", "RJ", "PJ", "CJ",
}

def smart_title(s: str) -> str:
    """Title case with exceptions for known abbreviations and short initials."""
    if not s:
        return s
    words = s.strip().split()
    result = []
    for word in words:
        # Strip punctuation for comparison
        clean = word.strip("\"',.")
        upper_clean = clean.upper()
        if upper_clean in ("JR", "JR."):
            result.append("Jr.")
        elif upper_clean in {k.upper() for k in KEEP_UPPER}:
            # Find the canonical casing
            canonical = next((k for k in KEEP_UPPER if k.upper() == upper_clean), clean.upper())
            result.append(word.replace(clean, canonical))
        else:
            result.append(word.capitalize())
    return " ".join(result)

def sentence_case(s: str) -> str:
    """Capitalize only the first word, lowercase everything else."""
    if not s:
        return s
    lowered = s.strip().lower()
    return lowered[0].upper() + lowered[1:]

def slugify(name: str, year: int) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return f"{slug}-{year}"

def normalize_bust_risk(raw: str):
    if not raw:
        return None
    normalized = BUST_RISK_NORMALIZE.get(raw.strip().upper())
    if not normalized:
        # Try case-insensitive match against order list
        for canonical in BUST_RISK_ORDER:
            if canonical.upper() == raw.strip().upper():
                return canonical
        print(f"  WARNING: Unrecognized bust risk '{raw}' — storing as-is")
        return raw.strip().title()
    return normalized

def import_csv(csv_path: str, year: int):
    prospects = []

    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        for rank, row in enumerate(reader, start=1):
            # Pad row to ensure enough columns
            while len(row) < 9:
                row.append("")

            name        = row[0].strip()
            school      = row[1].strip()
            bust_risk   = row[2].strip()
            description = row[3].strip()
            # cols 4,5,6 are blank
            draft_range  = row[7].strip()
            comparisons  = row[8].strip() if len(row) > 8 else ""

            if not name:
                continue

            prospect = {
                "id":                   slugify(smart_title(name), year),
                "name":                 smart_title(name),
                "draft_class":          year,
                "rank":                 rank,
                "position":             None,
                "role":                 None,
                "school":               smart_title(school),
                "nationality":          None,
                "age":                  None,
                "bust_risk":            normalize_bust_risk(bust_risk),
                "description":          sentence_case(description) if description else None,
                "perceived_draft_range": draft_range if draft_range else None,
                "comparisons":          comparisons if comparisons else None,
                "measurements": {
                    "height_no_shoes":  None,
                    "height_with_shoes": None,
                    "wingspan":         None,
                    "weight":           None,
                    "hand_length":      None,
                    "hand_width":       None,
                    "standing_reach":   None,
                    "vertical_no_step": None,
                    "vertical_max":     None
                },
                "stats":    {},
                "notes":    "",
                "drafted":  None
            }
            prospects.append(prospect)

    return prospects

def main():
    if len(sys.argv) < 3:
        print("Usage: python3 scripts/import_csv.py path/to/sheet.csv 2026")
        sys.exit(1)

    csv_path = sys.argv[1]
    year = int(sys.argv[2])

    if not os.path.exists(csv_path):
        print(f"Error: File not found: {csv_path}")
        sys.exit(1)

    print(f"Importing {csv_path} as draft class {year}...")
    prospects = import_csv(csv_path, year)
    print(f"Found {len(prospects)} prospects")

    out_dir = os.path.join(os.path.dirname(__file__), "..", "data", "prospects")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{year}.json")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(prospects, f, indent=2, ensure_ascii=False)

    print(f"Saved to {out_path}")

if __name__ == "__main__":
    main()
