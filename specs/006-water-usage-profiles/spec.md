# Feature Specification: Water Usage Profiles

Feature ID: `006-water-usage-profiles`
Created: 2026-06-21
Status: Implemented

## User Need

Users need a simple way to adjust water usage while city-specific official
tariff adapters are unavailable. They must also understand why the profiles use
4, 6 and 9 m3/month and that the resulting amount remains a low-confidence
scenario rather than an official municipal bill.

## Success Criteria

- The app supports `low`, `standard` and `high` water profiles.
- The selected profile changes the water amount without refreshing a source.
- The UI explains the profile rationale and links to the supporting sources.
- Water remains visibly labelled as manual fallback data with low confidence.
- Methodology states that linear scaling does not model local fixed fees,
  progressive bands, sanitation charges or taxes.

## Profile Definitions

- `low`: 4 m3/month. INE reports average household consumption of 128 litres
  per inhabitant/day, approximately 3.9 m3/month, rounded to 4 m3.
- `standard`: 6 m3/month. A buffered one-person scenario that also matches the
  upper boundary of the first published Aigues de Barcelona domestic band.
- `high`: 9 m3/month. A higher-use scenario matching the upper boundary of the
  second published Aigues de Barcelona domestic band.

These boundaries are usage scenarios. The Barcelona bands support clear user
communication but are not applied as tariffs to every supported city.

## Source References

- INE, Estadistica sobre el Suministro y Saneamiento del Agua, 2022:
  https://www.ine.es/dyngs/Prensa/es/ESSA2022.htm
- Aigues de Barcelona, domestic supply tariffs:
  https://www.aiguesdebarcelona.cat/es/servicio-agua/factura-y-tarifas-agua/tarifas-de-suministro

## Functional Requirements

- The system MUST expose profiles, rationale, methodology and source links at
  `/api/water/profiles`.
- The affordability endpoint MUST accept `water_profile` and default to
  `standard`.
- The current city seed MUST be treated as the 6 m3/month reference amount.
- Low and high scenarios MUST scale that reference by `4/6` and `9/6`.
- The API MUST expose the reference amount, selected consumption, scale factor
  and source references in water line-item details.
- The UI MUST provide an accessible information control with profile rationale
  and clickable source links.
- The UI and API MUST NOT describe the scenario as an official tariff bill.

## Non-Goals

- This feature does not parse official municipal water tariffs.
- This feature does not model fixed fees, progressive bands, sewerage, regional
  water canons, waste charges or VAT.
- This feature does not raise water confidence above `low`.
