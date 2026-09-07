#!/usr/bin/env python3
"""
Auto-assigns Hit/Solid/Mixed/Bust outcomes to historical players based on:
  1. Career Win Shares (WS) adjusted for draft position tier
  2. Manual overrides for edge cases (injuries, late bloomers, context)

Skips 2025 (too early — only one season played).
Skips players already rated (won't overwrite manual curations).

Methodology:
  Win Shares thresholds scale down with draft position —
  a #1 pick needs much more WS to be a "Hit" than a #40 pick.

  Draft tiers:
    Lottery  (1-14):  Hit≥60, Solid≥28, Mixed≥10
    Late 1st (15-30): Hit≥40, Solid≥18, Mixed≥6
    2nd Rd   (31-60): Hit≥20, Solid≥8,  Mixed≥2

Usage: python3 scripts/assign_outcomes.py
       python3 scripts/assign_outcomes.py --dry-run   # print only, don't save
"""

import json
import os
import sys

DRY_RUN = "--dry-run" in sys.argv
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "prospects")

# ── Manual overrides ────────────────────────────────────────────────────────
# Players where raw WS doesn't tell the full story.
# Format: "player-name-year": "outcome"
# Reasons: injuries cutting careers short, off-court issues, context, late bloom

OVERRIDES = {
    # 2013 — Busts raw stats can't capture
    "nerlens-noel-2013":            "Mixed",  # Top pick, never clicked despite talent
    "ben-mclemore-2013":            "Bust",   # Never became the shooter expected
    "michael-carter-williams-2013": "Bust",   # ROY then fell off a cliff
    "trey-burke-2013":              "Bust",   # Top pick expectations, journeyman career
    "alex-len-2013":                "Bust",   # High pick, never developed

    # 2014
    "julius-randle-2014":           "Hit",    # WS might underrate peak — All-Star, big contract
    "zach-lavine-2014":             "Hit",    # All-Star, max player
    "nikola-jokic-2014":            "Hit",    # 3x MVP — greatest 2nd round pick ever
    "clint-capela-2014":            "Solid",  # Reliable starter, WS may undersell longevity
    "shabazz-napier-2014":          "Bust",
    "noah-vonleh-2014":             "Bust",
    "embiid-2014":                  "Hit",    # Injuries early but transcendent peak

    # 2015
    "kristaps-porzingis-2015":      "Mixed",  # Injury-plagued, never fulfilled top pick promise
    "emmanuel-mudiay-2015":         "Bust",
    "myles-turner-2015":            "Solid",  # Consistent starting center, maybe underselling
    "devin-booker-2015":            "Hit",    # All-Star, max player
    "terry-rozier-2015":            "Solid",

    # 2016
    "ben-simmons-2016":             "Mixed",  # ROY, All-Star, then implosion / shooting refusal
    "dragan-bender-2016":           "Bust",
    "marquese-chriss-2016":         "Bust",
    "georgios-papagiannis-2016":    "Bust",
    "deyonta-davis-2016":           "Bust",
    "pascal-siakam-2016":           "Hit",    # Champion, All-Star, max player
    "fred-vanvleet-2016":           "Hit",    # Undrafted level pick → All-Star starter

    # 2017
    "markelle-fultz-2017":          "Bust",   # #1 pick, lost his shot, never recovered
    "lonzo-ball-2017":              "Mixed",  # Flashes but injuries and inconsistency
    "de-aaron-fox-2017":            "Hit",    # All-Star, max extension
    "lauri-markkanen-2017":         "Solid",  # Consistent starter, All-Star season
    "og-anunoby-2017":              "Hit",    # DPOY candidate, max player
    "john-collins-2017":            "Solid",
    "bam-adebayo-2017":             "Hit",    # All-Star, DPOY candidate, max player
    "kyle-kuzma-2017":              "Solid",

    # 2018
    "marvin-bagley-iii-2018":       "Bust",   # #2 pick, never delivered
    "miles-bridges-2018":           "Mixed",  # Great play then domestic violence conviction
    "zhaire-smith-2018":            "Bust",   # Career derailed by injury
    "kevin-knox-2018":              "Bust",
    "donte-divincenzo-2018":        "Solid",
    "shai-gilgeous-alexander-2018": "Hit",    # All-NBA, max player, OKC cornerstone
    "landry-shamet-2018":           "Solid",
    "jordan-nwora-2018":            "Bust",

    # 2019
    "ja-morant-2019":               "Hit",    # All-Star, max player (off-court issues aside)
    "rj-barrett-2019":              "Solid",  # Consistent starter, improving
    "darius-garland-2019":          "Hit",    # All-Star
    "jarrett-culver-2019":          "Bust",   # #6 pick, never delivered
    "bol-bol-2019":                 "Bust",
    "jordan-nwora-2019":            "Bust",
    "matisse-thybulle-2019":        "Mixed",  # Elite defender, offensive liability limits him

    # 2020
    "james-wiseman-2020":           "Bust",   # #2 pick, injuries and development stalled
    "lamelo-ball-2020":             "Hit",    # ROY, All-Star
    "patrick-williams-2020":        "Mixed",  # High pick, injuries stunted development
    "obi-toppin-2020":              "Mixed",  # #8 pick, solid role player but not starter level
    "kira-lewis-jr-2020":           "Bust",   # Injury, never found footing
    "precious-achiuwa-2020":        "Mixed",
    "tyrese-haliburton-2020":       "Hit",    # All-Star, max player

    # 2021
    "evan-mobley-2021":             "Hit",    # DPOY, All-Star, max extension
    "scottie-barnes-2021":          "Hit",    # ROY, All-Star
    "jalen-suggs-2021":             "Mixed",  # High pick, injuries and inconsistency
    "josh-giddey-2021":             "Mixed",  # Off-court issues, inconsistent production
    "alperen-sengun-2021":          "Hit",    # All-Star
    "franz-wagner-2021":            "Hit",    # All-Star, max player
    "davion-mitchell-2021":         "Bust",
    "keon-johnson-2021":            "Bust",
    "james-bouknight-2021":         "Bust",

    # 2022
    "jabari-smith-jr-2022":         "Mixed",  # #3 pick, solid but not top pick impact
    "keegan-murray-2022":           "Solid",
    "jaden-ivey-2022":              "Mixed",  # Flashes but inconsistent
    "mark-williams-2022":           "Solid",  # Good young center
    "tari-eason-2022":              "Solid",
    "jake-laravia-2022":            "Bust",
    "dyson-daniels-2022":           "Solid",  # Elite defender

    # 2023 — still early but 2 seasons in
    "victor-wembanyama-2023":       "Hit",    # Generational talent, DPOY, All-Star
    "scoot-henderson-2023":         "Mixed",  # #3 pick, struggled in year 2
    "brandon-miller-2023":          "Solid",  # Consistent starter
    "amen-thompson-2023":           "Solid",
    "ausar-thompson-2023":          "Mixed",  # Injury year 2
    "bilal-coulibaly-2023":         "Solid",
    "gradey-dick-2023":             "Mixed",
    "cason-wallace-2023":           "Mixed",
    "taylor-hendricks-2023":        "Mixed",  # Serious injury year 2

    # 2024 — only one season, very limited ratings
    "zaccharie-risacher-2024":      None,     # Too early
    "alex-sarr-2024":               None,
    "reed-sheppard-2024":           None,
    "stephon-castle-2024":          None,
    "ron-holland-2024":             None,
}


def get_thresholds(pick):
    if pick <= 14:
        return {"Hit": 60, "Solid": 28, "Mixed": 10}
    elif pick <= 30:
        return {"Hit": 40, "Solid": 18, "Mixed": 6}
    else:
        return {"Hit": 20, "Solid": 8, "Mixed": 2}


def assign(player):
    pick = player.get("drafted", {}).get("pick", 60) if player.get("drafted") else 60
    ws = player.get("stats", {}).get("ws")
    seasons = player.get("stats", {}).get("seasons", 0) or 0

    # No stats = no games played in NBA → Bust (for any meaningful pick)
    if ws is None:
        if pick <= 30:
            return "Bust"
        return None  # 2nd round with no stats — just leave unrated

    thresh = get_thresholds(pick)

    if ws >= thresh["Hit"]:
        return "Hit"
    elif ws >= thresh["Solid"]:
        return "Solid"
    elif ws >= thresh["Mixed"]:
        return "Mixed"
    else:
        return "Bust"


def main():
    total_assigned = 0
    total_skipped = 0

    for year in range(2013, 2026):
        if year == 2025:
            print(f"[2025] Skipping — too early to rate.")
            continue

        path = os.path.join(OUT_DIR, f"{year}.json")
        if not os.path.exists(path):
            continue

        with open(path, encoding="utf-8") as f:
            players = json.load(f)

        assigned = 0
        for p in players:
            if p.get("outcome"):
                total_skipped += 1
                continue  # don't overwrite manual curations

            # Check override first
            override = OVERRIDES.get(p["id"])
            if p["id"] in OVERRIDES:
                outcome = override  # could be None (explicit skip)
            else:
                outcome = assign(p)

            if outcome:
                p["outcome"] = outcome
                assigned += 1
                total_assigned += 1
                if DRY_RUN:
                    ws = p.get("stats", {}).get("ws", "?")
                    pick = p.get("drafted", {}).get("pick", "?")
                    print(f"  {p['name']:<30} pick={pick:<4} ws={ws:<6} → {outcome}")

        if not DRY_RUN:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(players, f, indent=2, ensure_ascii=False)

        print(f"[{year}] Assigned {assigned}/{len(players)} players")

    print(f"\nDone. Assigned {total_assigned} outcomes, skipped {total_skipped} already-rated.")
    if DRY_RUN:
        print("(dry run — nothing saved)")


if __name__ == "__main__":
    main()
