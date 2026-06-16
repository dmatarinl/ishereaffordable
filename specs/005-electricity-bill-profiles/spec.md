# Feature Specification: Electricity Bill Profiles

Feature ID: `005-electricity-bill-profiles`
Created: 2026-06-16
Status: Implemented

## User Need

Users need the electricity estimate to look more like a real monthly amount
they would pay, not only an energy-price signal. They also need the estimate to
adapt to different one-person usage patterns.

## Success Criteria

- The app supports `light`, `standard`, and `high` electricity profiles.
- The app uses official eSIOS PVPC energy-term data as the source signal.
- The app derives a monthly regulated-bill estimate using maintained
  assumptions for power term, meter rental, electricity tax, and VAT.
- The electricity profile can be selected in the API and UI.
- The methodology makes it clear which parts are official and which parts are
  maintained assumptions.

## Functional Requirements

- The system MUST keep the eSIOS energy-term signal cached server-side.
- The system MUST derive the monthly electricity amount from the cached
  EUR/kWh signal plus bill assumptions, without re-querying eSIOS per profile.
- The system MUST expose the supported electricity profiles through an API
  endpoint.
- The system MUST make `standard` the default profile.
- The system MUST lower confidence from `high` to `medium` when official eSIOS
  data is combined with maintained bill assumptions.

## Current Profile Assumptions

- `light`: 120 kWh/month, 3.45 kW contracted power in P1 and P2.
- `standard`: 180 kWh/month, 3.45 kW contracted power in P1 and P2.
- `high`: 250 kWh/month, 4.6 kW contracted power in P1 and P2.

## Current Bill Components

- Official eSIOS PVPC energy-term average for Península.
- Maintained 2.0TD power-term assumptions.
- Maintained electricity-tax assumption.
- Maintained VAT assumption.
- Maintained meter-rental assumption.

## Non-Goals

- This feature does not model household-specific time-of-use consumption.
- This feature does not model social-bonus discounts.
- This feature does not make electricity city-specific within Península.
