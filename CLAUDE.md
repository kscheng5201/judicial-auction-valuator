# CLAUDE.md

This file provides guidance to Claude Code when working in this repository.

## Project Overview

This project is a valuation system for Taiwan judicial property auctions
("法拍屋"). It ingests auction listings published by the Judicial Yuan
(and related sources), enriches each listing with location, transit,
amenity, and risk features, and produces a suggested bid range backed
by an explainable pricing model.

See `docs/PROJECT_BRIEF.md` for the full background, rationale, and
architecture discussion. Read that file before starting any new phase
of work — it contains the reasoning behind design decisions, not just
the decisions themselves.

## Language Rules

- `README.md` is written in **Traditional Chinese** (繁體中文). It is the
  only Chinese-language file in the repository.
- Every other file — code, comments, commit messages, docstrings, issue/PR
  templates, other docs under `docs/`, config files — must be in **English**.
- Do not mix languages within a single non-README file.

## Repository Structure (target)

```
.
├── README.md                  # Traditional Chinese project overview
├── CLAUDE.md                  # This file
├── docs/
│   ├── PROJECT_BRIEF.md       # Full background and architecture rationale
│   ├── DATA_SOURCES.md        # Source-by-source integration notes
│   └── VALUATION_MODEL.md     # Feature list, weighting methodology
├── src/
│   ├── ingestion/              # Scrapers and API clients per source
│   ├── enrichment/             # Geocoding, distance correction, feature engineering
│   ├── valuation/               # Pricing model (hedonic regression, later ML)
│   └── api/                    # Backend service exposing data to the app
├── data/
│   ├── raw/                     # Untouched snapshots (HTML, CSV, JSON)
│   └── processed/               # Cleaned, feature-engineered datasets
├── scripts/                    # One-off or scheduled jobs (cron entry points)
└── tests/
```

Do not assume this structure already exists — create directories as
needed when implementing each phase, and keep this section updated if
the structure changes.

## Development Priorities (in order)

1. **Ingestion layer, MVP scope**: Judicial Yuan auction scraper (raw HTML
   snapshot + parser), address normalization pipeline, and a geocoding
   client (start with one provider, keep the interface swappable).
2. **Distance correction feature**: straight-line vs. actual walking
   route distance/time, producing a "distortion ratio" per listing.
   This is a core product differentiator — do not treat it as optional.
3. **Enrichment layer**: TDX transit data client, amenity point ingestion
   (OSM Overpass as default), risk/hazard proximity checks.
4. **Valuation layer**: start with an interpretable hedonic pricing model
   (weighted/regression-based). Do not introduce a black-box ML model
   before the linear baseline exists and is validated — see
   `docs/VALUATION_MODEL.md` for why explainability matters here.
5. **API + app integration**: expose enriched listings and valuation
   output to the client app.

## Data Source Handling Conventions

- Treat every external data source as either: (a) a real API with
  request parameters and authentication, (b) a batch file drop with no
  query interface, or (c) unstructured HTML requiring scraping. Record
  which category each source falls into in `docs/DATA_SOURCES.md`.
- For scraped or batch-downloaded sources, always persist the raw
  snapshot (`data/raw/`) before parsing. Parsing logic must be
  re-runnable against a stored snapshot without re-fetching.
- Judicial Yuan auction site has no public API — scraping only. Respect
  reasonable request rates; do not parallelize aggressively against
  government infrastructure.
- Taiwan real-estate price registry (實價登錄) is a periodic batch file
  release, not a live API — build a scheduled fetch-and-diff job, not a
  polling client.
- TDX (Transport Data eXchange) is a genuine REST API with OIDC client
  credential auth — prefer it for all transit station/route data.

## Coding Conventions

- Prefer explicit, typed interfaces between ingestion / enrichment /
  valuation layers so each can be tested and swapped independently.
- Every feature used in the valuation model must be traceable back to
  a named, documented source field — no silently derived magic numbers.
- Write unit tests for parsers and geocoding/distance logic before
  wiring them into scheduled jobs; these are the most fragile parts of
  the pipeline (source formats change without notice).
- Do not commit API keys, credentials, or `.env` files. Use
  `.env.example` with placeholder values.

## Out of Scope / Do Not Do

- Do not present model output as a guaranteed valuation or formal
  appraisal — the product is a decision-support tool. Keep disclaimers
  in both the app copy and API response metadata.
- Do not scrape or store data in violation of a source's published
  terms of use — check and note licensing in `docs/DATA_SOURCES.md`
  before integrating a new source.

