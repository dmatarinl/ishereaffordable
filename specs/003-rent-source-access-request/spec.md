# Feature Specification: Rent Source Access Request

Feature ID: `003-rent-source-access-request`
Created: 2026-06-15
Status: Active Template

## User Need

The project needs a reusable, provider-neutral request document for rental
market data. Rent work is paused on commercial portal integrations until a
legally and economically viable source is available.

The active rent-source strategy is official rental reference/open data first,
then an approved real-estate API if the licensing and cost work, and only then
permitted scraping after terms and robots checks.

## Success Criteria

- The repository contains a clear rent-source access request description.
- The request explains the product, supported cities, data purpose, expected
  usage, cache strategy, and public display behavior.
- The request states that the app will use aggregate observations rather than
  mirroring full listings.
- The request includes questions needed before implementation begins.
- The request includes an implementation checklist for turning credentials into
  a real provider safely.

## Functional Requirements

- The project MUST provide copy/paste text for a provider outreach message.
- The project MUST state that source calls run from scheduled refresh jobs, not
  from ordinary user page loads.
- The project MUST state that stored rent data is aggregate and normalized.
- The project MUST identify the initial cities and rental profile.
- The project MUST document fallback behavior when a rent source is unavailable
  or returns insufficient data.
- The project MUST list open questions for authentication, rate limits,
  attribution, storage, display, query parameters, and cache terms.

## Non-Goals

- This feature does not implement a rent provider.
- This feature does not request credentials automatically.
- This feature does not change the rent calculation or seed values.
- This feature does not approve scraping for any specific portal.

## Acceptance Checks

- `docs/rent-source-access-request.md` exists.
- The README links to the request document.
- The request document includes a copy/paste project description.
- The request document includes implementation guardrails against unauthorized
  scraping or per-request source calls.
