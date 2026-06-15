# Is Here Affordable Constitution

Version: 1.0.0
Ratified: 2026-06-15
Last amended: 2026-06-15

## Core Principles

### 1. Source Truthfulness

The product must never imply that fallback, seeded, estimated, or manually
maintained data is scraped, live, official, or independently verified.

Every cost line item shown to users or returned by the API must make the data
mode explicit:

- `official_api`: fetched from an official API or official open-data endpoint.
- `permitted_scrape`: scraped only after terms, robots, and rate limits are
  reviewed and respected.
- `manual_seed`: maintained fallback data used while real sources are missing.
- `calculated`: produced by the Is Here Affordable formula from other line
  items.
- `unavailable`: no trustworthy value is available.

### 2. Legitimate Data Acquisition

Provider priority is:

1. Official API or open-data source.
2. Provider-approved API.
3. Permitted scraping with source-specific guardrails.
4. Manual seed fallback.

Scrapers must not bypass authentication, CAPTCHAs, paywalls, robots rules,
rate limits, or anti-abuse controls. They must use a descriptive user agent,
cache results, and avoid running during ordinary user page loads.

### 3. Freshness Is Not Source Verification

The app must distinguish between:

- `observed_at`: when the source value was observed or published.
- `cached_at`: when Is Here Affordable stored the observation.
- `valid_until`: when the observation should be considered stale.

The UI must not use vague labels such as "observed" when the value is only a
manual seed refreshed into the local cache.

### 4. Explainable Calculations

Every displayed total must be reconstructable from visible line items and
documented assumptions. The formula must expose the profile, usage assumptions,
safety margin, included categories, and missing categories.

### 5. Graceful Degradation

When a real source is unavailable, the app may fall back only if the response
clearly labels the fallback, lowers confidence, and shows a warning. Silent
substitution is not allowed.

### 6. Testable Source Boundaries

External providers must be tested with fixtures or fake clients. Unit and API
tests must not depend on live network access. Any provider that talks to a real
source must have tests for success, missing credentials, source failure, empty
payloads, and fallback behavior.

## Governance

This constitution applies to source integrations, formulas, API responses,
refresh jobs, and UI copy. Any change that affects data acquisition,
confidence, freshness, or user-facing claims must update the relevant spec and
tests in the same pull request.

Changes to this constitution require:

1. A clear reason for the amendment.
2. A migration note describing affected specs or code.
3. Updated tests or documentation where behavior changes.
