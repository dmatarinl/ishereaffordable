# Is Here Affordable?

Python web app to estimate how much money someone needs today to live in a
Spanish city.

The Spain MVP focuses on one adult renting a one-bedroom home, no car, EUR only.
It stores source-attributed cost observations in a cache database and calculates
an explainable monthly target from those observations.

## Stack

- Python 3.11+
- FastAPI
- Uvicorn
- SQLAlchemy
- SQLite for local development
- PostgreSQL-ready `DATABASE_URL` for production
- Pytest and Ruff

## Local Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
python -m app.jobs.refresh_all
uvicorn app.main:app --reload
```

Then open http://127.0.0.1:8000.

The first app startup also seeds the local cache automatically if there are no
observations yet.

## API

```bash
curl "http://127.0.0.1:8000/api/affordability?city=Madrid&currency=EUR"
curl "http://127.0.0.1:8000/api/affordability?city=Madrid&currency=EUR&electricity_profile=high"
curl "http://127.0.0.1:8000/api/affordability?city=Madrid&currency=EUR&electricity_profile=high&safety_margin_percent=10"
curl "http://127.0.0.1:8000/api/cities"
curl "http://127.0.0.1:8000/api/electricity/profiles"
curl "http://127.0.0.1:8000/api/public-transport/fares"
curl "http://127.0.0.1:8000/api/sources/status"
curl "http://127.0.0.1:8000/api/sources/rules"
```

The UI exposes electricity profiles as a toggle and lets the user choose a
5%, 10%, 15%, or custom safety margin. The API accepts the same controls through
`electricity_profile` and `safety_margin_percent`.

## Current Data Model

Each cost category is stored as a normalized observation:

- `rent`
- `electricity`
- `gas`
- `water`
- `trash_tax`
- `food`
- `public_transport`
- `safety_margin` is calculated, not stored as source data

Each line item includes monthly amount, source name, source URL, observation
time, cache time, data mode, confidence, methodology, and provider-specific
details.

Data mode is intentionally separate from confidence:

- `manual_seed`: cached fallback data maintained inside the app.
- `official_api`: fetched from an official API or open-data endpoint.
- `official_publication`: maintained from an official tariff or rule.
- `permitted_scrape`: scraped only where source rules allow it.
- `calculated`: produced by the Is Here Affordable formula.
- `unavailable`: no trustworthy value is available.

Source rules are machine-readable in `app/sources/catalog.py` and exposed via
`/api/sources/rules`. Each rule defines source priority, allowed data modes,
freshness limits, and user-facing guidance.

## Refresh Jobs

```bash
python -m app.jobs.refresh_all
python -m app.jobs.refresh_city --city Madrid
```

The public request path reads cached observations only. It does not scrape or
call external sources per user request.

## Source Strategy

Source work follows the project constitution in
[`.specify/memory/constitution.md`](.specify/memory/constitution.md). The first
spec-driven feature is
[`specs/001-source-transparency-fallback-labeling/spec.md`](specs/001-source-transparency-fallback-labeling/spec.md).

The current implementation supports all eight Spain MVP cities:

- Madrid
- Barcelona
- Valencia
- Sevilla
- Zaragoza
- Málaga
- Bilbao
- Alicante

These seed observations are intentionally marked as low or medium confidence.
They make the product usable while real sources are integrated.

Source integrations:

- Rent: paused on portal integrations until a legally and economically viable
  source is available. The preferred path is official rental reference/open data
  first, then an approved real-estate API, and only then permitted scraping.
  The previous Idealista request draft remains in
  [`docs/idealista-api-request.md`](docs/idealista-api-request.md) for context,
  but Idealista is not the current default target.
- Electricity: eSIOS/PVPC data when `ESIOS_API_TOKEN` is configured. Without
  that token, the app keeps a low-confidence electricity fallback so the MVP
  remains usable.
- Gas: official BOE TUR data from BOE OpenData summary discovery. If
  `BOE_GAS_TUR_URL` is set, that specific BOE XML/HTML/TXT/PDF document is used
  as an override. Without BOE access, the app keeps a low-confidence gas
  fallback so refreshes remain usable.
- Water and trash tax: municipal/provider tariffs.
- Food: fixed basket refreshed from supermarket adapters for Mercadona,
  Carrefour, and Dia/Alcampo where allowed by terms and robots rules.
- Public transport: maintained 2026 official adult fares. Each observation
  records the product or 40-journey scenario, modes included, exclusions,
  current and base fare where available, subsidy, and validity period. See
  [`specs/008-public-transport-methodology/spec.md`](specs/008-public-transport-methodology/spec.md).

## Food Basket

The canonical grocery basket is defined in
[`app/data/food_basket.json`](app/data/food_basket.json) and loaded through
`app/food/basket.py`. It represents one adult, one month, and stays identical
for every city. Supermarket adapters will price that same basket by city or
postcode, then the app will use the median valid supermarket basket total.

The basket includes item quantities, matching terms, allowed substitutions,
required/optional flags, source basis, and confidence thresholds for missing
products.

To enable eSIOS electricity:

1. Request a personal token from the official eSIOS API documentation site.
2. Set `ESIOS_API_TOKEN` in `.env` or production environment variables.
3. Keep the token server-side only. The browser must never call eSIOS
   directly.
4. Run `python -m app.jobs.refresh_all`.
5. Check `/api/sources/status` and the electricity line item in the UI.

The app is designed to stay within the eSIOS public-access guidance:

- public users read cached data from our server, not from REE directly
- scheduled refresh jobs perform the source fetches
- one `refresh_all` run reuses a single eSIOS response across all cities in the
  current national-PVPC model

The electricity estimate now exposes three household usage profiles:

- `light`: 120 kWh/month, 3.45 kW contracted power
- `standard`: 180 kWh/month, 3.45 kW contracted power
- `high`: 250 kWh/month, 4.6 kW contracted power

The monthly electricity line item is no longer a plain energy-term estimate. It
uses the official eSIOS PVPC signal for Península and then applies maintained
2.0TD bill assumptions for power term, meter rental, electricity tax, and VAT.

To enable BOE gas TUR:

1. Keep `BOE_GAS_ENABLE_DISCOVERY=true` so the refresh job discovers the latest
   BOE gas TUR resolution from `/datosabiertos/api/boe/sumario/{fecha}`.
2. Optionally set `BOE_GAS_TUR_URL` to a known BOE XML, HTML, TXT, or PDF URL to
   force a specific document during development.
3. Set `GAS_DEFAULT_PROFILE=standard` unless another profile should be cached by
   default.
4. Review `GAS_VAT_RATE_PERCENT`, `GAS_HYDROCARBONS_TAX_EUR_PER_KWH`, and
   `GAS_METER_RENTAL_MONTHLY_EUR` when tax rules change.
5. Run `python -m app.jobs.refresh_all`.

The BOE TUR table publishes prices before taxes. The app exposes three gas
usage profiles and converts the official terms into an estimated final monthly
bill:

- `low`: 120 kWh/month, TUR.1
- `standard`: 250 kWh/month, TUR.1
- `heating`: 8,000 kWh/year averaged monthly, TUR.2

The gas bill estimate applies maintained assumptions for hydrocarbons tax, VAT,
and meter rental. These are shown in the line-item details so BOE source data
and bill assumptions are not confused.

## Water Profiles

Water remains a low-confidence city seed while official municipal tariff
adapters are pending. The UI exposes three transparent usage scenarios:

- `low`: 4 m3/month, rounded from the INE national per-person household average
- `standard`: 6 m3/month, the current seed reference and a first-band boundary
- `high`: 9 m3/month, a higher-use second-band boundary

The 6 m3 city seed is scaled linearly for the selected scenario. This does not
yet reproduce fixed fees, progressive bands, sanitation charges or taxes. The
profile information control links to the INE consumption statistics and Aigues
de Barcelona's published domestic bands that support these boundaries.

## Deployment

The repo includes `render.yaml` and `Procfile`.

For `ishereaffordable.com` on Render:

1. Push this repo to GitHub.
2. Create a Render Blueprint from `render.yaml`.
3. Add `ishereaffordable.com` as a custom domain in Render.
4. Point the domain DNS to Render's target.
5. Set production environment variables.
6. Add a Render Cron Job that runs `python -m app.jobs.refresh_all` daily.

## Environment

```bash
APP_NAME="Is Here Affordable?"
APP_ENV=development
DEFAULT_CURRENCY=EUR
SAFETY_MARGIN_PERCENT=15
DATABASE_URL=sqlite:///./data/affordability.db
IDEALISTA_API_KEY=
ESIOS_API_TOKEN=
ESIOS_PVPC_INDICATOR_ID=1001
ESIOS_LOOKBACK_DAYS=30
ELECTRICITY_DEFAULT_PROFILE=standard
BOE_GAS_TUR_URL=
BOE_GAS_ENABLE_DISCOVERY=true
GAS_DEFAULT_PROFILE=standard
GAS_VAT_RATE_PERCENT=21
GAS_HYDROCARBONS_TAX_EUR_PER_KWH=0.00234
GAS_METER_RENTAL_MONTHLY_EUR=0
ENABLE_SUPERMARKET_SCRAPING=false
SOURCE_USER_AGENT="IsHereAffordableBot/0.1 (+https://ishereaffordable.com)"
```

Use PostgreSQL in production by setting `DATABASE_URL` to the managed database
URL provided by the host.
