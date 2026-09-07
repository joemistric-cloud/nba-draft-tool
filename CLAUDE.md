# NBA Draft Analysis Tool — CLAUDE.md

## Project Purpose

A personal NBA Draft prospect analysis tool and website for tracking, ranking, and comparing prospects across draft classes from 2013 to present. The core mechanic is comparison — every element of the interface is a trigger for contextual comparison against historical prospects. The site is read-only for anyone it is shared with; only the owner edits data and rankings.

## Who This Is For

Built by and for an NBA Draft analyst. The owner has deep domain knowledge of the draft process, prospect evaluation, and historical draft classes. This is not a general sports stats site — it is a scouting and analysis workflow tool. Assume the user understands NBA terminology and does not need it explained.

## Core Concept

The homepage is a **Big Board** — a ranked list of all prospects eligible for the current NBA Draft. Every element on the board is clickable and opens a contextual comparison view:

- **Player name** → player profile + historically comparable prospects
- **School / club team** → all prospects from that program across all draft classes
- **Position** → all prospects at that position across all draft classes
- **Measurements** (height, wingspan, weight, etc.) → prospects with similar physical profiles
- **Any other attribute** → relevant cross-class comparison

The comparison engine — drawing connections between current prospects and historical ones — is the heart of this project.

## Draft Classes in Scope

2013 through present (current year draft class included). Every feature should be built with multi-class data in mind from the start.

## Architecture

This project has two distinct parts:

### 1. Data Pipeline (Python)
- Python scripts scrape and collect prospect data from external sources
- Output is stored as structured JSON files in `data/prospects/` (one file per draft class, e.g. `2025.json`)
- Scripts live in `scripts/`
- Data is collected once and cached locally — scripts are not run continuously
- Be respectful of source sites: add delays between requests, do not hammer servers

### 2. Web Application (Next.js)
- Frontend reads from local JSON data files
- No live scraping at runtime — all data is pre-collected
- Built with Next.js (App Router) and Tailwind CSS
- Hosted on Vercel (free tier)
- Read-only for all users except the owner

## Tech Stack

- **Frontend**: Next.js (App Router), React, Tailwind CSS
- **Data storage**: JSON files (flat file, no database to start)
- **Scraping**: Python (BeautifulSoup, requests, pandas)
- **Hosting**: Vercel
- **Package manager**: npm

## Data Sources (to be scraped)

Primary targets:
- Basketball Reference — historical draft data, stats, measurements
- NBA.com — official combine measurements
- Additional sources TBD as the project evolves

Scraping is for personal, non-commercial use. Always cache results locally.

## Data Model (initial)

Each prospect entry should include where available:

```json
{
  "id": "unique-slug",
  "name": "Player Name",
  "draft_class": 2025,
  "rank": 1,
  "position": "PG",
  "school": "Kentucky",
  "nationality": "USA",
  "age": 19,
  "measurements": {
    "height_no_shoes": 75.5,
    "height_with_shoes": 76.0,
    "wingspan": 80.5,
    "weight": 185,
    "hand_length": 8.5,
    "hand_width": 9.0,
    "standing_reach": 98.0,
    "vertical_no_step": 32.0,
    "vertical_max": 38.5
  },
  "stats": {},
  "notes": "",
  "drafted": {
    "pick": 1,
    "team": "Atlanta Hawks"
  }
}
```

Current class prospects will not have `drafted` data. Historical prospects will have it.

## File Structure

```
nba-draft-tool/
  CLAUDE.md
  data/
    prospects/
      2025.json
      2024.json
      ...
      2013.json
  scripts/
    scrape_bball_reference.py
    scrape_combine.py
  src/
    app/
      page.tsx              ← Big Board homepage
      player/[id]/page.tsx  ← Player profile + comparables
      compare/page.tsx      ← Comparison views
    components/
    lib/
      data.ts               ← Data loading utilities
  public/
  package.json
```

## Design Principles

- **Simple homepage, deep on click** — the big board should be clean and fast to scan. Complexity lives one layer deeper.
- **Comparison first** — every design decision should ask: does this make comparison easier?
- **Expandable** — build data structures and components to accommodate new attributes, new draft classes, and new views without rewrites.
- **No over-engineering** — start with flat JSON files. Only add a database if flat files become genuinely unworkable.
- **Mobile-aware** — the board should be usable on a phone, even if not perfectly optimized for it initially.

## What to Avoid

- Do not add authentication or user accounts — this is read-only for viewers
- Do not add a CMS or admin panel in early stages
- Do not use a database until JSON files are clearly insufficient
- Do not build comparison features before the base big board is working
- Do not scrape data at runtime — always pre-collect and cache

## CSV Import

The Google Sheet export has no header row. Column order is fixed:

| Index | Field |
|-------|-------|
| 0 | Name (all caps in sheet — converted to title case on import) |
| 1 | School / Club |
| 2 | Bust Risk |
| 3 | Description (all caps in sheet — converted to sentence case on import) |
| 4-6 | Blank (ignored) |
| 7 | Perceived Draft Range |
| 8 | Comparisons (stored as-is, user's own shorthand) |

Run import with: `python3 scripts/import_csv.py path/to/sheet.csv 2026`

## Position vs Role

Every prospect has two separate fields:

- `position` — conventional (PG/SG/SF/PF/C). Used internally for data matching and scraping. **Never the primary display field.**
- `role` — user-defined classification reflecting how a player actually functions in the modern game. This is what gets displayed in the UI.

The role assignment system is a planned future feature: the user will define role archetypes, and the system will use stats/analytics to suggest assignments. Roles are always the owner's final call.

## Prospect Data Fields

Beyond the standard model, each prospect has:
- `bust_risk` — one of: None, Very Low, Low, Low Mid, Mid, Upper Mid, High, Very High
- `description` — concise scouting note in sentence case
- `perceived_draft_range` — e.g. "1-5", "10-20"
- `comparisons` — user's own shorthand player comps (e.g. "TMAC, SIAKAM")

Measurements and stats are null for all current prospects — to be populated via scraping scripts later.

## Current Status

Big board is live at localhost:3000. Stack is fully scaffolded.
- 198 prospects imported from Google Sheets (2026 draft class)
- Drag-to-reorder working with save via API route
- Inline position picker on big board — click Pos cell to assign PG/SG/SF/PF/C, auto-saves
- Data lives in `data/prospects/2026.json`
- Player constellation visualization built (`app/components/Constellation.tsx`) — SVG with golden angle layout, animated pulse/flow, clickable comp nodes
- Player panel redesigned (`app/components/PlayerPanel.tsx`) — 50/50 split: left side shows player info + stats, right side shows constellation + comps
- Stats displayed in two box-score style rows: Per Game and Shooting & Efficiency
- Clicking a player on `/outcomes` opens the same stats panel (left/right split)
- Historical draft data scraped (2013–2025): 779 players in `data/prospects/{year}.json`
- ~520 historical players have NBA combine measurements from `nba_api`
- **615 historical players have college stats** scraped from BRef (`college_stats` field) — 158 internationals have no college data
- **159 of 198 2026 prospects have college stats** — 156 from SR CBB + 3 international (Sergio De Larrea/ESP-2, Hugo Facorat/OTE, Jonas Boulefaa/FRA-2) scraped via Eurobasket.com — 39 still missing (NBL paywalled, obscure college, no online profile)
- College/pre-draft stats include: per game box (PTS/REB/AST/STL/BLK/TOV/ORB/PF/MIN), shooting splits (FG%/2P%/3P%/FT%), rates (3PAr/FTr), efficiency (TS%/eFG%/A/TO). 2026 stats also include USG%, AST%, BPM from SR CBB advanced table. International stats include league + team context. Rim finishing (Rim%/RimFr) columns present in UI but unpopulated — needs Hoop-Math scrape
- Historical Outcomes page live at `/outcomes` — Hit/Solid/Mixed/Bust zone layout, position group filter, click-to-edit (✎ icon), drag-to-reorder
- `data/legends.json` — 6 pre-2013 comp references (LeBron, KD, Kobe, TMAC, KG, Vince Carter)
- All 2026 prospect positions are null — user to fill in manually
- Outcome curation not yet started — user to manually assign Hit/Solid/Mixed/Bust starting with PG group
- 2026 combine measurements not yet available (coming May 2026)
- AJ Dybantsa name was corrected in 2026.json (was "Dybansta")

## Pending / Next Up
- Manual position entry for 2026 prospects (inline picker built, ready to use)
- Manual outcome curation for 2013–2025 players (start at /outcomes, PG group)
- International player stats — Eurobasket scraper built (`scripts/scrape_intl_stats.py`); got 3 players. Remaining 39 missing: NBL players are paywalled on australiabasket.com; others have no accessible public stats. May need manual entry or different sources
- Rim finishing stats — scrape Hoop-Math for `rim_fg_pct` and `rim_freq` fields (columns already in UI)
- Role system — user to define archetypes; system will suggest assignments via stats (future)
- Bust risk visual feature (designed in separate Claude chat, not yet built)
- Connect constellation view to historical outcome data (future)
- 2026 combine measurements (coming May 2026)
