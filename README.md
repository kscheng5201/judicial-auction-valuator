# judicial-auction-valuator

**Data-driven valuation system for Taiwan judicial property auctions —
aggregates court auction listings, transit/amenity proximity, and
historical pricing to estimate fair bid ranges.**

[繁體中文說明](README.zh-TW.md)

> ⚠️ Early-stage project. No runnable version yet. This README reflects
> current planning and will evolve alongside development.

## What This Is

Taiwan's judicial auction listings (法拍屋) are publicly available, but
as raw announcements they are not structured for investment decisions.
Buyers have no systematic way to judge a fair bid range, weigh the many
factors that move price (building age, floor, elevator access, delivery
status, ownership share, transit access, neighborhood amenities), or
verify the marketing claims that come with a listing.

One recurring problem this project specifically targets: real-estate
listings commonly advertise proximity to MRT/rail stations using
**straight-line distance**, when the actual walking route may cross a
river, rail line, or highway and take several times longer. This project
computes and surfaces that discrepancy rather than repeating it.

## Approach

1. **Data aggregation** — court auction announcements, government price
   registry data, transit station data, neighborhood amenity points, and
   hazard/nuisance facility locations.
2. **Distance-accuracy correction** — straight-line vs. actual walking
   route distance/time, flagged as a distortion ratio, to catch inflated
   "X minutes to MRT" claims.
3. **Explainable pricing model** — a hedonic (feature-weighted) pricing
   model trained on historical auction and market transaction data, so
   every price adjustment is traceable to a specific, named factor
   rather than a black-box output.
4. **Bid range, not a single number** — conservative / suggested /
   aggressive bid estimates, with a confidence indicator based on how
   much historical data supports the estimate for that area.

## Architecture

```
Ingestion → Enrichment → Valuation → Application
```

Each layer is designed to evolve independently — see
[`docs/PROJECT-BRIEF.md`](docs/PROJECT-BRIEF.md) for the full rationale
behind this split, the complete feature list, data source classification,
and the reasoning behind the valuation model design.

## Data Sources

| Source | Access Method |
|---|---|
| Judicial Yuan auction announcements | Web scraping (no public API) |
| Taiwan real-estate price registry (實價登錄) | Periodic batch file releases |
| MRT/rail station data | TDX (Transport Data eXchange) API |
| Neighborhood amenities | OpenStreetMap / map service APIs |
| Hazard facilities, cadastral data | Municipal open data portals (mixed: some APIs, mostly file downloads) |

Full source-by-source notes belong in `docs/DATA_SOURCES.md`.

## Project Scope and Limitations

- This system produces **decision-support estimates**, not certified
  appraisals, and does not guarantee auction outcomes. Judicial auctions
  carry real legal and financial risk (occupancy disputes, hidden liens,
  etc.) — consult a licensed appraiser or auction advisor before bidding.
- Where historical data for an area or property type is sparse, the
  system reports a lower confidence level rather than presenting a
  falsely precise estimate.

## Documentation Language

This `README.md` is the default, English-language project overview. A
Traditional Chinese version is available at
[`README.zh-TW.md`](README.zh-TW.md). All other project documentation,
code, comments, and commit messages are in English — see
[`CLAUDE.md`](CLAUDE.md) for the full language policy.

## Status

Early planning phase. See [`CLAUDE.md`](CLAUDE.md) and
[`docs/PROJECT-BRIEF.md`](docs/PROJECT-BRIEF.md) for development
priorities and architecture details.

