# Feature Specification: Data Source Rules

Feature ID: `002-data-source-rules`
Created: 2026-06-15
Status: Ready for implementation

## User Need

Users need each cost category to follow the same trustworthy sourcing rules, so
that one category cannot silently use weaker data while another presents itself
as official.

## Success Criteria

- Every category has an explicit source priority order.
- Every category has allowed data modes and a freshness window.
- Confidence levels are assigned consistently from data mode and freshness.
- API and UI warnings are generated from shared rules, not scattered copy.
- Manual seed data remains allowed, but only as a visibly low-confidence
  fallback.

## Source Priority Matrix

| Category | First choice | Second choice | Fallback | Freshness target |
| --- | --- | --- | --- | --- |
| Rent | Idealista Search API or approved real-estate API | Permitted portal scrape | Manual seed | 7 days |
| Electricity | eSIOS API | None | Manual seed | 1 day |
| Gas | BOE OpenData gas TUR resolution discovery | None | Manual seed | 90 days |
| Water | Municipal/provider tariff data | Permitted provider/city scrape | Manual seed | 180 days |
| Trash tax | Municipal ordinance/official publication/open data | Permitted city tax-page scrape | Manual seed | 365 days |
| Food | Supermarket API/feed | Permitted supermarket scrape | Manual basket seed | 7 days |
| Public transport | Official transport authority fare/API or publication | Permitted fare-page scrape | Manual seed | Through stated tariff validity, reviewed at least annually |
| Safety margin | Calculated formula | None | None | Always current |

## Confidence Rules

- `high`: official API/open data, parsed successfully, inside freshness window,
  and methodology complete.
- `medium`: permitted scrape from a stable public page, or official publication
  with assumptions, representative averages, ranges, or manual mapping, inside
  the freshness window.
- `low`: manual seed, stale data, partial basket/listing data, unavailable data,
  or any provider failure using fallback.

## Functional Requirements

- The system MUST define one machine-readable rule per cost category.
- The system MUST validate every returned line item against the category rule.
- The system MUST warn when a line item uses manual seed data.
- The system MUST warn when a line item is stale according to its category
  freshness window.
- The system MUST warn when a line item uses a data mode that the category does
  not allow.
- The system MUST expose the source rules through an API endpoint so the UI and
  future admin screens can render the same policy.
- The system MUST keep safety margin as `calculated`; it must never be treated
  as sourced data.
- The system MUST keep personal API tokens on the server side only; they must
  never be exposed to public clients or committed to version control.
- The system MUST serve public affordability requests from cached observations
  stored on our server, not by calling source APIs directly during user page
  loads.
- The system MUST avoid redundant refresh calls to the same source when one
  shared response can be reused safely across multiple cities.
- A refresh that falls back to a weaker data mode MUST retain a stronger cached
  observation when one exists and mark the source run as degraded.

## Source-Specific Notes

- eSIOS tokens are personal to the requester and are allowed only for
  server-side use.
- eSIOS-backed public pages must read electricity data from our cache database,
  never directly from REE systems in the browser.
- Because the current PVPC electricity model is national rather than
  city-specific, one refresh run should fetch the eSIOS indicator once and
  reuse it for every supported city.
- eSIOS refreshes should run at most on the scheduled cache-refresh cadence
  unless there is a clear need to backfill missing data.
- Gas TUR refreshes should use BOE OpenData daily summaries to discover the
  latest resolution, parse the official BOE document, and show tax assumptions
  separately from the source tariff because BOE publishes TUR prices before
  taxes.
- Municipal waste charges should use reusable tariff rules for published city
  averages, water-consumption bands, and official ranges. Exact household bills
  must not be implied when required property or billing inputs are unavailable.

## Non-Goals

- This feature does not add new real providers.
- This feature does not scrape any website.
- This feature does not change the affordability formula.

## Notes For Implementation

- Prefer `app/sources/catalog.py` as the rule catalog.
- Add an endpoint such as `/api/sources/rules`.
- Do not duplicate rule strings in the UI if the API can provide them.
- Rule validation should add warnings but should not block the estimate unless
  data is missing or structurally invalid.
