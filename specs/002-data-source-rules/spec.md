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
| Rent | Idealista API or approved real-estate API | Permitted portal scrape | Manual seed | 7 days |
| Electricity | eSIOS API | None | Manual seed | 1 day |
| Gas | Official TUR, BOE, or CNMC data | None | Manual seed | 90 days |
| Water | Municipal/provider tariff data | Permitted provider/city scrape | Manual seed | 180 days |
| Trash tax | Municipal ordinance/open data | Permitted city tax-page scrape | Manual seed | 365 days |
| Food | Supermarket API/feed | Permitted supermarket scrape | Manual basket seed | 7 days |
| Public transport | Official transport authority fares | Permitted fare-page scrape | Manual seed | 90 days |
| Safety margin | Calculated formula | None | None | Always current |

## Confidence Rules

- `high`: official API/open data, parsed successfully, inside freshness window,
  and methodology complete.
- `medium`: permitted scrape from a stable public page, or official data with
  minor assumptions/manual mapping, inside freshness window.
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
