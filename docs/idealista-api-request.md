# Idealista Search API Access Request

Use this document to request Idealista Search API access for the rent source in
Is Here Affordable?.

Access form: https://developers.idealista.com/access-request

## Copy/Paste Project Description

Is Here Affordable? will be a public web app at https://ishereaffordable.com (not ready yet) that
helps people understand the monthly amount they may need to live in a Spanish
city. The first version focuses on one adult living alone, renting a
one-bedroom home, without a car, and currently supports Madrid, Barcelona,
Valencia, Sevilla, Zaragoza, Málaga, Bilbao, and Alicante.

I would like to use the Idealista Search API as the primary source for rental
costs. Rent is the largest category in the estimate, so our goal is to replace
our current low-confidence manual fallback values with source-attributed market
data from Idealista.

The app will query long-term rental listings for one-bedroom homes by city,
calculate aggregated city-level rent statistics, and show those aggregate
results to users. The default value shown will be the median monthly rent. When
the sample size allows it, we will also show P25 and P75 ranges, sample size,
source name, source URL, refresh time, confidence level, and a clear
methodology note.

I will not call the API on ordinary user page loads. The public app reads from
our cache only. API calls will run in scheduled refresh jobs, initially once per
day or less for the supported cities. For the MVP this means roughly one
scheduled search per supported city per refresh cycle, with conservative usage
and respect for any rate limits or display requirements provided by Idealista.

I plan to store normalized aggregate observations, not a mirrored copy of
Idealista. For rent, the cache will contain fields such as city, monthly median
rent, P25/P75 range where available, sample count, query profile, observed_at,
cached_at, source name, and methodology. We do not intend to store or republish
full listing descriptions, images, contact information, or other listing-level
content beyond what is necessary for transparent attribution and aggregate
calculation.

The project prioritizes trustworthy, explainable data. If the API is
unavailable, expired, or returns too little data for a city, the app will label
that category as fallback or unavailable instead of presenting the value as
official Idealista data.

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
| Fallback behavior | Manual seed stays clearly labeled low-confidence fallback |

## Questions To Ask Idealista

- Which authentication fields should we use in production and staging?
- What are the Search API rate limits and recommended refresh cadence?
- Which fields may be stored for aggregate calculations, and for how long?
- What attribution wording and source links are required in the public UI?
- Are P25/P75 rent ranges and sample counts permitted as public aggregate
  outputs?
- Which query parameters should be used for long-term rental, one-bedroom homes
  by city?
- Is there a minimum sample size they recommend before displaying an aggregate?

## Implementation Checklist After Approval

- Add the approved credential names to `.env.example`, Render environment
  variables, and `app/core/config.py`.
- Implement `app/providers/idealista.py` behind the existing `HousingProvider`
  interface.
- Keep Idealista disabled unless the required credentials are configured.
- Fetch rent only inside refresh jobs, never inside `/api/affordability`.
- Store only aggregate rent observations and provider metadata in the database.
- Mark successful Idealista observations as `official_api`.
- Downgrade confidence or mark unavailable when the sample is empty or too
  small.
- Keep `SeedHousingProvider` as the fallback, but continue labeling it as
  `manual_seed`.
- Add provider tests with recorded fixtures and no live API calls in CI.
- Update the UI to show sample size and P25/P75 once the provider supplies them.

## Guardrails

- Do not scrape Idealista listing pages while waiting for API access.
- Do not republish full listing content as a substitute for the Idealista
  product.
- Do not make API calls per visitor request.
- Do not hide fallback rent data behind official-source language.
- Do not add more cities or profiles until the initial usage pattern is stable
  and within the approved limits.
