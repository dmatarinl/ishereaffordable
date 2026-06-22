# Public Transport Methodology

## Goal

Represent a realistic monthly public transport cost for one adult in each Spain
MVP city using current official fares, while making the selected product and its
coverage explicit to the user.

## Standard traveller

- One adult without age, income, disability, or family discounts.
- Resident in the principal urban fare zone.
- No private car.
- Airport and special-event services are excluded unless the selected official
  product explicitly includes them.

## Calculation rule

1. Prefer an official general-adult 30-day integrated or urban pass.
2. When a pay-as-you-go product is the clearer representative option, calculate
   40 one-way urban journeys per month.
3. Never present a pass as covering a mode that the fare authority excludes.
4. Store the current fare, published base fare when available, temporary subsidy,
   validity period, fare zone, included modes, and excluded modes.
5. Use household expenditure studies only as a reasonableness check, not as the
   primary city cost.

## 2026 city choices

| City | Calculation used | Monthly amount |
| --- | --- | ---: |
| Madrid | Abono Transporte 30 days, Zone A | EUR 32.70 |
| Barcelona | T-usual 30 days, one zone | EUR 22.80 |
| Valencia | SUMA Mensual 30 days, one zone | EUR 21.00 |
| Sevilla | TUSSAM 30 days | EUR 21.20 |
| Zaragoza | 40 journeys with Tarjeta Bus at EUR 0.55 | EUR 22.00 |
| Malaga | EMT monthly pass | EUR 23.97 |
| Bilbao | Bidai Oro 30 days, one zone | EUR 30.25 |
| Alicante | TAM Bono 30 days, Zone A | EUR 24.00 |

Valencia's listed discount expires on June 30, 2026. All other listed temporary
2026 fares must be reviewed no later than December 31, 2026. Expired validity
must produce a user-facing warning until a new official fare is recorded.

## Source handling

- These values are maintained from official transport authority publications and
  use the `official_publication` data mode.
- A refresh caches the maintained observation; it does not claim that an official
  API was called.
- Future permitted fare-page adapters may replace maintained entries, but must
  preserve the same product, coverage, and validity metadata.
