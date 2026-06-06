# Is Here Affordable?

Python web app to estimate how much money someone needs today to live in a city.

The first version is intentionally simple: it exposes a web form and an API, uses
mock cost-of-living data, and keeps the formula and data providers isolated so
they can evolve independently.

## Stack

- Python 3.11+
- FastAPI
- Uvicorn
- Pydantic settings
- Pytest

## Local Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Then open http://127.0.0.1:8000.

## API

```bash
curl "http://127.0.0.1:8000/api/affordability?city=Madrid&currency=EUR"
```

## Project Layout

```text
app/
  main.py                  FastAPI app and routes
  core/
    config.py              Runtime settings
  affordability/
    calculator.py          Cost-of-living formula
    models.py              Domain models
  providers/
    base.py                Provider protocol
    mock.py                Local seed data
static/
  index.html               First product screen
tests/
  test_calculator.py       Formula smoke tests
```

## Deployment

The repo includes a `render.yaml` and a `Procfile`, so platforms like Render,
Railway, or Fly.io can run:

```bash
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

For `ishereaffordable.com` on Render, the usual flow is:

1. Push this repo to GitHub.
2. Create a Render Blueprint from `render.yaml`.
3. Add `ishereaffordable.com` as a custom domain in Render.
4. Point the domain DNS to Render's target.
5. Set any environment variables from `.env.example` if you want to override
   the defaults.

## Next Steps

- Pick real data sources for rent, groceries, transport, utilities, and salary.
- Add scraping providers with source metadata and caching.
- Replace the initial formula with a validated affordability model.
- Add city autocomplete and country-aware currency defaults.
