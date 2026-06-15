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
curl "http://127.0.0.1:8000/api/cities"
curl "http://127.0.0.1:8000/api/sources/status"
curl "http://127.0.0.1:8000/api/sources/rules"
```

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

The current implementation includes source-aware seed providers for all eight
Spain MVP cities:

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

- Rent: Idealista Search API once access is granted. The access-request draft is
  in [`docs/idealista-api-request.md`](docs/idealista-api-request.md).
- Electricity: eSIOS/PVPC data when `ESIOS_API_TOKEN` is configured. Without
  that token, the app keeps a low-confidence electricity fallback so the MVP
  remains usable.
- Gas: official TUR data.
- Water and trash tax: municipal/provider tariffs.
- Food: fixed basket refreshed from supermarket adapters for Mercadona,
  Carrefour, and Dia/Alcampo where allowed by terms and robots rules.

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
3. Run `python -m app.jobs.refresh_all`.
4. Check `/api/sources/status` and the electricity line item in the UI.

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
ELECTRICITY_MONTHLY_KWH=180
ELECTRICITY_FIXED_MONTHLY_EUR=14
ENABLE_SUPERMARKET_SCRAPING=false
SOURCE_USER_AGENT="IsHereAffordableBot/0.1 (+https://ishereaffordable.com)"
```

Use PostgreSQL in production by setting `DATABASE_URL` to the managed database
URL provided by the host.
