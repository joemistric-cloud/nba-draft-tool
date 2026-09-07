#!/usr/bin/env python3
"""
Adds outcome and outcome_tags fields to all historical prospect JSON files.
Safe to run multiple times — only adds fields if missing.

Usage: python3 scripts/add_outcome_fields.py
"""

import json
import os

PROSPECTS_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "prospects")
CURRENT_CLASS = 2026

def main():
    files = sorted(f for f in os.listdir(PROSPECTS_DIR) if f.endswith(".json"))
    for filename in files:
        year = int(filename.replace(".json", ""))
        if year == CURRENT_CLASS:
            continue  # skip current class — outcome fields don't apply yet

        path = os.path.join(PROSPECTS_DIR, filename)
        with open(path, encoding="utf-8") as f:
            prospects = json.load(f)

        changed = 0
        for p in prospects:
            if "outcome" not in p:
                p["outcome"] = None
                changed += 1
            if "outcome_tags" not in p:
                p["outcome_tags"] = []
                changed += 1

        if changed:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(prospects, f, indent=2, ensure_ascii=False)
            print(f"  {filename}: added fields to {len(prospects)} players")
        else:
            print(f"  {filename}: already up to date")

    print("Done.")

if __name__ == "__main__":
    main()
