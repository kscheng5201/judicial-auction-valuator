# Project Brief: Taiwan Judicial Auction Property Valuation System

## 1. Problem Statement

Taiwan's judicial (court-ordered) property auctions publish listings
through the Judicial Yuan's auction announcement site. The raw listing
data exists, but it is not structured for investment decision-making:
there is no standardized way to compare a listing's fair value against
market price, and no systematic way to account for the many factors
that move price up or down (building type, age, floor, delivery status,
transit proximity, neighborhood amenities, hazards nearby, etc.).

Additionally, commercial real-estate listing sites commonly advertise
"5 minutes to MRT" using straight-line distance, when the actual walking
route may cross a river, bridge, or highway and take 3x as long. This is
a known source of misrepresentation in the market that this project aims
to detect and correct for, rather than repeat.

## 2. Goal

Build a system that:

1. Ingests judicial auction listings and enriches each one with
   structured, comparable features.
2. Computes a **suggested bid range** (not a single number) backed by
   an interpretable pricing model, so users understand *why* a price
   was suggested, not just what it is.
3. Explicitly flags cases where advertised proximity claims (e.g.
   "5 min to MRT") diverge from actual walking distance/time, using a
   straight-line vs. actual-route distortion ratio.

## 3. System Architecture

The system is split into four independently evolvable layers:

```
Ingestion → Enrichment → Valuation → Application
```

- **Ingestion**: pulls raw data from each external source and persists
  an untouched snapshot before any parsing.
- **Enrichment**: converts raw listings into structured, comparable
  features (geocoding, distance correction, amenity scoring, hazard
  flags).
- **Valuation**: turns feature vectors into a suggested bid range using
  an explainable pricing model.
- **Application**: the user-facing app/API layer.

Keeping these layers separate means a change in one (e.g. the Judicial
Yuan site changing its HTML structure, or swapping the pricing model
from linear regression to gradient boosting) does not require changes
in the others.

## 4. Data Sources

Full technical notes belong in `docs/DATA_SOURCES.md`. Summary:

| Source | Category | Notes |
|---|---|---|
| Judicial Yuan auction announcements | Scraping only, no API | Primary listing source: address, floor, area, delivery status, ownership share, appraisal report |
| Enforcement Agency (行政執行署) auction listings | Scraping only, no API | Secondary/supplementary listing source |
| Taiwan real-estate price registry (實價登錄, MOI) | Periodic batch file release, not a live API | Used as the "normal market price" baseline and for regression training labels |
| TDX (Transport Data eXchange) | Genuine REST API, OIDC auth | MRT/rail/bus station coordinates and route shapes |
| OSM Overpass API | Genuine open API | Fallback/supplement for amenity points (convenience stores, schools, hospitals, markets) |
| Google Places API | Commercial API | Optional, higher-quality amenity data; check usage terms before using for a paid product |
| Municipal open data portals | Mixed — some APIs, mostly file downloads | Hazard/nuisance facility locations (gas stations, substations, cemeteries, waste facilities); coverage varies significantly by city |
| Address/geocoding services (TGOS, municipal land offices, OSM Nominatim, Google Geocoding) | Mixed | Needs empirical testing against real auction-listing addresses, which are often cadastral (段/小段/地號) rather than standard street addresses |

Key operational point: **"open data" in Taiwan frequently means a
periodically-published file, not a queryable API.** Before integrating
any new source, classify it into one of three categories (real API /
batch file / scrape-required) and record that classification — this
determines whether you build a polling client or a scheduled
fetch-and-diff job.

## 5. Valuation Features

### 5.1 Building characteristics
- Age (banded, not continuous — matches how buyers actually reason
  about it: new / <15 years / >30 years)
- Elevator building vs. walk-up apartment
- Floor number, **interacted with** elevator presence (walk-up + high
  floor is a strong negative; elevator + high floor can be a positive)
- Registered floor area vs. actual main-structure area (public-area
  ratio matters — do not conflate the two)
- Ownership share / co-ownership status (partial ownership share is a
  strong negative due to resale and financing friction)
- Delivery status ("點交" vs "不點交") — expected to be one of the
  largest-weight features; non-delivery implies the buyer must resolve
  occupancy issues independently

### 5.2 Location and transit
- Straight-line distance to nearest MRT/rail station (fast filtering)
- **Actual walking route distance/time** via a routing service
- **Distortion ratio = actual route distance / straight-line distance**
  — values near 1 mean the advertised proximity is credible; high
  values indicate a barrier (river, rail line, highway) and should
  discount or flag the "near transit" bonus rather than apply it at
  face value
- Proximity to rail lines/elevated tracks as a separate negative
  feature (noise/vibration) — must be modeled independently from
  "near a station," since the two often co-occur geographically and
  can cancel each other out if conflated

### 5.3 Neighborhood amenities
- Density of amenity points within 500m (convenience stores, markets,
  schools, hospitals, department stores)
- Same straight-line vs. actual-route correction as transit distance
- Consider weighting amenities by buyer persona (e.g. schools/markets
  matter more for families; malls/theaters more for younger buyers) —
  a future personalization feature, not required for MVP

### 5.4 Hazards / risk flags
- Proximity to gas stations, substations, temples, funeral facilities,
  waste facilities
- Haunted-house / unnatural-death disclosures, third-party occupancy,
  illegal additions, sand-contaminated concrete — these are often
  buried in free-text remarks in the listing, not structured fields,
  and require NLP/keyword extraction rather than a simple column read

## 6. Valuation Model

### Phase 1 (MVP): Interpretable hedonic pricing model
A weighted/regression-based model:

```
estimated_market_price = base_unit_price(district/segment)
                          × (1 + Σ feature_adjustment_coefficients)
```

Coefficients are derived by regressing historical auction sale prices
and normal-market transaction prices (from the price registry) against
the feature set above. This is the standard "hedonic pricing" approach
used in real-estate valuation research.

Include an **auction discount ratio** (auction sale price ÷ contemporaneous
normal market price for the same area) as a feature in its own right —
it is itself influenced by delivery status and number of failed auction
rounds, so it carries independent signal.

This phase must ship before any non-linear model, because every
adjustment needs to be explainable to the user — this is a high-stakes,
high-risk purchase decision, and a black-box number will not earn user
trust.

### Phase 2 (later): Non-linear refinement
Once there is sufficient historical data, a gradient-boosted model
(XGBoost/LightGBM) may be layered on top to correct residuals from the
Phase 1 model. The Phase 1 linear estimate should remain visible to the
user even after Phase 2 ships — do not fully replace it.

### Output format
Never output a single number. Output:
- Conservative bid (lower risk, lower win probability)
- Suggested bid (model median estimate)
- Aggressive bid (near market price, higher win probability)
- A confidence indicator based on how much historical data exists for
  that area/listing type

## 7. Application Features (high level)

1. Listing list with filters (city, court, property type, auction type)
2. Listing detail page showing the raw announcement data plus a
   transparent breakdown of every positive/negative adjustment and its
   source
3. **Transit distortion warning**: visual flag when advertised proximity
   diverges significantly from actual walking route — this is a
   deliberate product differentiator
4. Suggested bid range with explanation text
5. Historical comparable sales for the same building/street segment
6. User-adjustable feature weights (e.g. "walk-up is acceptable" or
   "school district matters a lot to me") for personalized ranking

## 8. Risks and Constraints

- **Terms of use**: high-frequency scraping of government sites must
  respect published usage terms and rate limits; check each source's
  open-data license before relying on it for a commercial product.
- **Not a substitute for professional appraisal**: the tool is decision
  support, not a certified valuation. This must be stated clearly in
  the app and in API responses — judicial auctions carry real legal and
  financial risk (hidden liens, occupancy disputes, etc.).
- **Sparse data problem**: some areas/property types will have very
  few historical comparables. Surface the confidence level honestly
  rather than presenting a falsely precise number.

