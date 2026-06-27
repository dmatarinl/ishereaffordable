# Rent Source Access Request

Status: active template. Use this document when contacting a rental data
provider, public-data maintainer, or approved real-estate API.

The active rent-source strategy is official rental reference/open data first,
then an approved real-estate API if the licensing and cost work for the MVP,
and only then permitted scraping after terms and robots checks.

## Copy/Paste Project Description

Is Here Affordable? will be a public web app at https://ishereaffordable.com
that helps people understand the monthly amount they may need to live in a
Spanish city. The first version focuses on one adult living alone, renting a
one-bedroom home, without a car, and currently supports Madrid, Barcelona,
Valencia, Sevilla, Zaragoza, Málaga, Bilbao, and Alicante.

For the rent category, we do not need to display individual listings. We need
source-attributed aggregate market data that can support a transparent monthly
cost estimate.

For the MVP, the target dataset is:

- Long-term rental housing.
- One-bedroom homes, or a surface-based approximation if bedroom count is not
  available.
- Median monthly rent by city.
- P25/P75 range where available.
- Sample count or coverage indicator used to calculate the metric.
- City-level data first, with neighborhood-level data as a future extension.
- Daily, weekly, or monthly refresh depending on source terms.
- Permission to cache aggregate observations on our server and show public
  aggregate metrics with attribution.

The app will not call provider systems on ordinary user page loads. Public
users read from our cache only. Source calls run inside scheduled refresh jobs,
initially once per day or less for the supported cities.

We plan to store normalized aggregate observations, not a mirrored copy of
listing pages. For rent, the cache will contain fields such as city, monthly
median rent, P25/P75 range where available, sample count, query profile,
observed_at, cached_at, source name, source URL, and methodology. We do not
intend to store or republish full listing descriptions, images, contact
information, or other listing-level content beyond what is necessary for
transparent attribution and aggregate calculation.

The project prioritizes trustworthy, explainable data. If a source is
unavailable, expired, or returns too little data for a city, the app will label
that category as city estimate or unavailable instead of presenting the value as
source-backed market data.

## Request Details

| Field | Value |
| --- | --- |
| Product | Is Here Affordable? |
| Domain | https://ishereaffordable.com |
| Repository | https://github.com/dmatarinl/ishereaffordable |
| Data purpose | Aggregate monthly rent estimates by Spanish city |
| Initial geography | Madrid, Barcelona, Valencia, Sevilla, Zaragoza, Málaga, Bilbao, Alicante |
| Initial profile | Long-term rental, one-bedroom home, one adult |
| Refresh cadence | Daily at most for MVP, cache-backed public reads |
| User-facing output | Median rent, optional P25/P75 range, sample count, source attribution, methodology |
| Storage | Aggregate normalized observations, not full listing replication |
| Fallback behavior | Manual city estimate stays clearly labeled as city estimate |

## Questions To Ask Providers

- Which authentication fields should we use in production and staging?
- What are the rate limits and recommended refresh cadence?
- Which fields may be stored for aggregate calculations, and for how long?
- What attribution wording and source links are required in the public UI?
- Are P25/P75 rent ranges and sample counts permitted as public aggregate
  outputs?
- Which query parameters should be used for long-term rental, one-bedroom homes
  by city?
- Is there a minimum sample size they recommend before displaying an aggregate?
- Are public web display, caching, and scheduled refreshes explicitly allowed?

## Implementation Checklist After Approval

- Add the approved credential names to `.env.example`, production environment
  variables, and `app/core/config.py`.
- Implement a provider behind the existing `HousingProvider` interface.
- Keep the provider disabled unless the required credentials and source flags
  are configured.
- Fetch rent only inside refresh jobs, never inside `/api/affordability`.
- Store only aggregate rent observations and provider metadata in the database.
- Mark successful official/open-data observations as `official_api` or
  `official_publication` as appropriate.
- Mark permitted scraping as `permitted_scrape` only after terms and robots
  checks pass.
- Mark unavailable or insufficient samples clearly instead of inflating the
  city estimate.
- Keep `SeedHousingProvider` as the fallback, labeled as `manual_seed`.
- Add provider tests with recorded fixtures and no live API calls in CI.
- Update the UI to show sample size and P25/P75 once the provider supplies
  them.

## Guardrails

- Do not scrape listing pages without documented permission or terms review.
- Do not republish full listing content as a substitute for licensed or
  official aggregate data.
- Do not make source calls per visitor request.
- Do not hide fallback rent data behind official-source language.
- Do not add more cities or profiles until the initial usage pattern is stable
  and within the approved limits.
