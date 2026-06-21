# Feature Specification: Hybrid Municipal Waste Model

Feature ID: `007-hybrid-municipal-waste-model`
Created: 2026-06-21
Status: Implemented

## User Need

Users need a realistic monthly waste-charge estimate even though Spanish
municipalities publish different formulas and often require property-specific
inputs that a renter does not know.

## Model

The default result uses the strongest available city-level method in this order:

1. An official published city average.
2. A representative estimate calculated from an official tariff rule and the
   selected household profile.
3. The midpoint of an official range, with that range visible in methodology.
4. A visibly labelled low-confidence manual fallback.

The model supports reusable rule types rather than one calculator implementation
per city:

- `published_city_average`
- `water_consumption_bands`
- `official_range_midpoint`

## Initial Official Coverage

| City | Rule | Default basis |
| --- | --- | --- |
| Madrid | Published city average | Official 2026 average |
| Zaragoza | Water-consumption bands | Selected water profile |
| Alicante | Official range midpoint | Residential property up to 60 m2 |

Barcelona, Valencia, Sevilla, Malaga, and Bilbao remain manual fallbacks until
their complete collection and treatment charges can be modelled without omitting
required bill components.

## Transparency Requirements

- Official municipal pages and ordinances MUST use
  `data_mode=official_publication`, not `official_api`.
- Representative estimates MUST use medium confidence.
- Manual fallbacks MUST use low confidence and produce a warning.
- Every official rule MUST expose its tariff year, validity, source URL, annual
  amount, calculation kind, required exact inputs, and whether the amount is
  exact.
- Annual charges MUST be converted to monthly costs only after the annual
  calculation is complete.
- A selected water profile MUST recalculate water-band waste tariffs without a
  new source request.

## Refresh And Scaling

- Public requests MUST use cached observations and never call municipal sites.
- Tariff publications are reviewed annually and stored as normalized rule data.
- Adding a compatible city SHOULD require catalog data rather than a new
  provider class.
- A city-specific adapter is acceptable only when its official formula cannot be
  represented by an existing rule type.

## Non-Goals

- Exact tax bills without the municipality's required household/property inputs.
- A nationwide Spanish average.
- Scraping municipal sites before robots, terms, and page stability are reviewed.
