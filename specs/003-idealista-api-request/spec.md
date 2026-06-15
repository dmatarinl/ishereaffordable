# Feature Specification: Idealista API Access Request

Feature ID: `003-idealista-api-request`
Created: 2026-06-15
Status: Ready for external request

## User Need

The project needs Idealista Search API access before rent can move from manual
fallback data to source-attributed market observations.

## Success Criteria

- The repository contains a clear API access request description.
- The request explains the product, supported cities, data purpose, expected
  usage, cache strategy, and public display behavior.
- The request states that the app will use aggregate observations rather than
  mirroring full listings.
- The request includes questions needed before implementation begins.
- The request includes an implementation checklist for turning credentials into
  a real provider safely.

## Functional Requirements

- The project MUST provide copy/paste text for Idealista's "Describe your
  project" form field.
- The project MUST state that API calls run from scheduled refresh jobs, not
  from ordinary user page loads.
- The project MUST state that stored rent data is aggregate and normalized.
- The project MUST identify the initial cities and rental profile.
- The project MUST document fallback behavior when Idealista is unavailable or
  returns insufficient data.
- The project MUST list open questions for authentication, rate limits,
  attribution, storage, display, and query parameters.

## Non-Goals

- This feature does not implement the Idealista provider.
- This feature does not request credentials automatically.
- This feature does not change the rent calculation or seed values.

## Acceptance Checks

- `docs/idealista-api-request.md` exists.
- The README links to the request document.
- The request document includes a copy/paste project description.
- The request document includes implementation guardrails against scraping or
  per-request API calls.
