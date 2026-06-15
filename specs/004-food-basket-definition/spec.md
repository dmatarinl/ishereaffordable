# Feature Specification: Food Basket Definition

Feature ID: `004-food-basket-definition`
Created: 2026-06-15
Status: Implemented as canonical basket definition

## User Need

Users need the food estimate to be based on a stable, explainable consumption
basket before supermarket scraping starts. Supermarkets vary by city, but the
cost comparison must price the same lifestyle assumption everywhere.

## Success Criteria

- The basket contains 30-50 canonical products for one adult and one month.
- Each product has a quantity, unit, required flag, matching terms,
  substitutions, and a seed unit price.
- The basket defines how to combine supermarket results when a source is
  missing in a city.
- The basket defines how unavailable products affect confidence.
- The seed food provider reads the canonical basket instead of maintaining a
  separate hardcoded list.

## Source Basis

- MAPA Panel de Consumo Alimentario grounds the basket categories in Spanish
  household consumption.
- INE Encuesta de Presupuestos Familiares sanity-checks the final monthly
  amount against observed spending.
- AESAN dietary guidance keeps the basket oriented toward a basic, healthy, and
  sustainable diet rather than cheap calories only.

## Basket Rules

- The canonical basket is identical for every supported city.
- Supermarket availability varies by city and postcode; adapters price the
  canonical basket against products available in each source.
- Each supermarket produces its own basket total first.
- The city food cost uses the median valid supermarket basket total.
- Missing optional products should be shown but should not invalidate a source.
- Missing required products lower coverage and can invalidate a source.
- Substitutions are allowed only when listed on the canonical item.

## Confidence Rules

- `high`: at least 90% required-product coverage, at least two valid
  supermarket sources, and no more than 25% substitutions.
- `medium`: at least 75% required-product coverage, at least one valid
  supermarket source, and no more than 40% substitutions.
- `low`: lower coverage, one weak source, heavy substitutions, or manual seed.
- `unavailable`: not enough required products to price the basket fairly.

## Non-Goals

- This feature does not scrape supermarket sites.
- This feature does not decide representative city postcodes.
- This feature does not add a separate household consumables category.

## Notes For Implementation

- Keep the basket in `app/data/food_basket.json`.
- Keep loading and validation in `app/food/basket.py`.
- Supermarket adapters should use item `id`, `reference_terms`, and
  `substitutions` rather than inventing their own product definitions.
