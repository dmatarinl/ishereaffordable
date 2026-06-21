# Feature Specification: Source Transparency And Fallback Labeling

Feature ID: `001-source-transparency-fallback-labeling`
Created: 2026-06-15
Status: Ready for implementation

## User Need

Users need to know whether each affordability number comes from a real source,
a permitted scrape, a manual fallback, or the app's own formula. Trust is more
important than making the app look complete.

## Success Criteria

- Users can identify the origin of every line item without reading code.
- Manual seed values are never presented as scraped, official, or live data.
- Cached time and source observation time are not conflated.
- Fallbacks lower confidence and produce clear warnings.
- API consumers receive the same transparency data as the UI.

## User Stories

### Story 1: User Sees Real Data Versus Fallback Data

As a visitor comparing a Spanish city, I want each cost line to show whether it
is official, scraped, manually seeded, or calculated so I can decide how much to
trust the result.

Acceptance criteria:

- WHEN a line item is based on manual seed data, THE SYSTEM SHALL show a visible
  fallback label and low confidence.
- WHEN a line item uses an official source but the displayed amount also relies
  on maintained assumptions or calculations, THE SYSTEM SHALL show official
  provenance and medium estimate confidence.
- WHEN a displayed amount is supported by current authoritative data with
  minimal assumptions, THE SYSTEM SHALL show high estimate confidence.
- WHEN a line item is calculated by the app, THE SYSTEM SHALL label it as
  calculated and show the formula input.

### Story 2: User Understands Freshness

As a visitor, I want to know when the app cached a value and when the source
actually published or exposed it.

Acceptance criteria:

- WHEN a line item is displayed, THE SYSTEM SHALL distinguish `observed_at` from
  `cached_at`.
- WHEN a source does not provide an observation timestamp, THE SYSTEM SHALL show
  the cache timestamp and explain that source observation time is unavailable.
- WHEN data is stale, THE SYSTEM SHALL show a warning for the affected category.

### Story 3: Maintainer Can Audit Source Health

As the project owner, I want to see whether each provider refreshed from a real
source or fell back so I can prioritize source work.

Acceptance criteria:

- WHEN `/api/sources/status` is called, THE SYSTEM SHALL include the provider
  status, last refresh attempt, data mode, and fallback reason if any.
- WHEN a provider fails, THE SYSTEM SHALL keep previous cached observations
  where possible and record the failure.

## Functional Requirements

- The API response for `/api/affordability` MUST include `data_mode`,
  `source_name`, `source_url`, `confidence`, `methodology`, `observed_at`,
  `cached_at`, and `valid_until` for every line item.
- The API response MUST include top-level warnings for every low-confidence,
  stale, unavailable, or fallback category.
- The UI MUST replace ambiguous wording like "observed" with source-aware copy:
  "official source observed", "cached fallback", "calculated by formula", or
  equivalent.
- The UI MUST label confidence levels as high, medium, or low confidence and
  explain that they rate the final estimate, not the price or consumption.
- The UI MUST distinguish source provenance from estimate confidence. Official
  provenance does not automatically imply high confidence when the final amount
  depends on material assumptions or calculations.
- Refresh jobs MUST store normalized observations with both source metadata and
  cache metadata.
- Providers MUST NOT make live network calls during ordinary page loads.
- Tests MUST cover official-source success, missing credentials, fallback
  labeling, stale data, source status, and UI/API copy for fallback values.

## Non-Goals

- This feature does not add new rent, supermarket, water, gas, or tax sources.
- This feature does not change the affordability formula.
- This feature does not remove seed data; it makes seed data explicit and safe.

## Notes For Implementation

- Existing `confidence` is not enough; add a separate `data_mode`.
- Existing `observed_at` currently behaves like cache refresh time for seeds.
  Add `cached_at` and treat seed `observed_at` as unavailable or methodology-
  specific.
- Safety margin should be `data_mode=calculated`.
- eSIOS electricity without `ESIOS_API_TOKEN` should be `manual_seed`; with a
  valid token and parsed response it should be `official_api`.
