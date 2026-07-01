import { neon } from "@neondatabase/serverless";

declare const Netlify: {
  env: {
    get(name: string): string | undefined;
  };
};

type CostLineItem = {
  category: string;
  label: string;
  monthly_amount: number;
  currency: string;
  data_mode: string;
  source_name: string;
  source_url: string;
  observed_at: string;
  cached_at: string | null;
  valid_until: string | null;
  confidence: string;
  methodology: string;
  details: Record<string, unknown>;
};

type SupportedCity = {
  key: string;
  name: string;
  province: string;
  region: string;
  country: string;
  currency: string;
};

const SUPPORTED_CITIES: SupportedCity[] = [
  { key: "madrid", name: "Madrid", province: "Madrid", region: "Madrid", country: "Spain", currency: "EUR" },
  { key: "barcelona", name: "Barcelona", province: "Barcelona", region: "Catalonia", country: "Spain", currency: "EUR" },
  { key: "valencia", name: "Valencia", province: "Valencia", region: "Valencian Community", country: "Spain", currency: "EUR" },
  { key: "sevilla", name: "Sevilla", province: "Sevilla", region: "Andalusia", country: "Spain", currency: "EUR" },
  { key: "zaragoza", name: "Zaragoza", province: "Zaragoza", region: "Aragon", country: "Spain", currency: "EUR" },
  { key: "malaga", name: "Málaga", province: "Málaga", region: "Andalusia", country: "Spain", currency: "EUR" },
  { key: "bilbao", name: "Bilbao", province: "Bizkaia", region: "Basque Country", country: "Spain", currency: "EUR" },
  { key: "alicante", name: "Alicante", province: "Alicante", region: "Valencian Community", country: "Spain", currency: "EUR" },
];

const ELECTRICITY_PROFILES = {
  light: {
    key: "light",
    label: "Light",
    monthly_kwh: 120,
    contracted_power_p1_kw: 3.45,
    contracted_power_p2_kw: 3.45,
    description: "Small one-person flat with careful use and no heavy electric heating.",
  },
  standard: {
    key: "standard",
    label: "Standard",
    monthly_kwh: 180,
    contracted_power_p1_kw: 3.45,
    contracted_power_p2_kw: 3.45,
    description: "Typical one-person flat with moderate appliance use.",
  },
  high: {
    key: "high",
    label: "High",
    monthly_kwh: 250,
    contracted_power_p1_kw: 4.6,
    contracted_power_p2_kw: 4.6,
    description: "One-person home with higher appliance use, AC, or electric water heating.",
  },
} as const;

const GAS_PROFILES = {
  low: {
    key: "low",
    label: "Low",
    monthly_kwh: 120,
    annual_kwh: 1440,
    rate_code: "TUR.1",
    description: "Cooking and/or modest hot-water use without gas heating.",
  },
  standard: {
    key: "standard",
    label: "Standard",
    monthly_kwh: 250,
    annual_kwh: 3000,
    rate_code: "TUR.1",
    description: "One adult using gas for cooking and hot water.",
  },
  heating: {
    key: "heating",
    label: "Heating",
    monthly_kwh: 8000 / 12,
    annual_kwh: 8000,
    rate_code: "TUR.2",
    description: "One-person home with gas heating averaged across the year.",
  },
} as const;

const WATER_PROFILE_METHODOLOGY =
  "Spain has no single household water tariff: providers use local fixed fees, consumption bands, sanitation charges and taxes. Until city tariff adapters are implemented, these profiles scale the current city estimate from its 6 m3/month reference. Actual bills are not necessarily linear.";

const WATER_PROFILE_SOURCES = [
  {
    name: "INE household water consumption",
    url: "https://www.ine.es/dyngs/Prensa/es/ESSA2022.htm",
    relevance:
      "INE reports 128 litres per inhabitant/day in 2022, approximately 3.9 m3/month and rounded to the 4 m3 low scenario.",
  },
  {
    name: "Aigues de Barcelona domestic bands",
    url: "https://www.aiguesdebarcelona.cat/es/servicio-agua/factura-y-tarifas-agua/tarifas-de-suministro",
    relevance:
      "The published domestic bands end at 6 m3/month for band one and 9 m3/month for band two, providing understandable standard and high scenario boundaries.",
  },
];

const WATER_PROFILES = {
  low: {
    key: "low",
    label: "Low",
    monthly_m3: 4,
    description: "Careful one-person household use.",
    rationale: "Rounded from the INE national per-person household average.",
  },
  standard: {
    key: "standard",
    label: "Standard",
    monthly_m3: 6,
    description: "One adult with moderate daily water use.",
    rationale: "Adds headroom above the INE average and matches a first-band cap.",
  },
  high: {
    key: "high",
    label: "High",
    monthly_m3: 9,
    description: "Higher shower, laundry, cleaning or home-working use.",
    rationale: "Matches the upper boundary of a published second domestic band.",
  },
} as const;

const CORE_CATEGORIES = [
  "rent",
  "electricity",
  "gas",
  "water",
  "trash_tax",
  "food",
  "public_transport",
];

const SOURCE_RULES: Record<string, { label: string; first_choice: string; allowed_data_modes: string[]; freshness_days: number | "always" }> = {
  rent: {
    label: "Rent",
    first_choice: "Official rental reference/open data",
    allowed_data_modes: ["official_api", "permitted_scrape", "manual_seed", "unavailable"],
    freshness_days: 7,
  },
  electricity: {
    label: "Electricity",
    first_choice: "eSIOS API",
    allowed_data_modes: ["official_api", "manual_seed", "unavailable"],
    freshness_days: 1,
  },
  gas: {
    label: "Gas",
    first_choice: "BOE OpenData gas TUR resolution discovery",
    allowed_data_modes: ["official_api", "manual_seed", "unavailable"],
    freshness_days: 90,
  },
  water: {
    label: "Water",
    first_choice: "Municipal/provider tariff data",
    allowed_data_modes: ["official_api", "permitted_scrape", "manual_seed", "unavailable"],
    freshness_days: 180,
  },
  trash_tax: {
    label: "Trash tax",
    first_choice: "Municipal ordinance, official publication, or open data",
    allowed_data_modes: ["official_api", "official_publication", "permitted_scrape", "manual_seed", "unavailable"],
    freshness_days: 365,
  },
  food: {
    label: "Food",
    first_choice: "Supermarket API/feed",
    allowed_data_modes: ["official_api", "permitted_scrape", "manual_seed", "unavailable"],
    freshness_days: 7,
  },
  public_transport: {
    label: "Public transport",
    first_choice: "Official transport authority fares",
    allowed_data_modes: ["official_api", "official_publication", "permitted_scrape", "manual_seed", "unavailable"],
    freshness_days: 365,
  },
  safety_margin: {
    label: "Safety margin",
    first_choice: "Calculated formula",
    allowed_data_modes: ["calculated"],
    freshness_days: "always",
  },
};

const REGULATED_ELECTRICITY_ASSUMPTIONS = {
  days_per_month: 365 / 12,
  power_price_p1_eur_kw_day: 0.068041426,
  power_price_p2_eur_kw_day: 0.002646239,
  electricity_tax_rate: 0.0511269632,
  vat_rate: 0.21,
  meter_rental_monthly_eur: 0.81,
};

const BROWSER_REVALIDATE = "public, max-age=0, must-revalidate";
const STABLE_READ_CACHE = "public, durable, max-age=3600, stale-while-revalidate=86400";
const AFFORDABILITY_CACHE = "public, durable, max-age=300, stale-while-revalidate=900";
const EXPECTED_API_ORIGIN = "https://is-here-affordable-api.onrender.com";

function jsonResponse(body: unknown, status = 200, cdnCacheControl?: string) {
  const headers: Record<string, string> = {
    "content-type": "application/json; charset=utf-8",
    "cache-control": cdnCacheControl ? BROWSER_REVALIDATE : "no-store",
  };
  if (cdnCacheControl) {
    headers["Netlify-CDN-Cache-Control"] = cdnCacheControl;
  }
  return new Response(JSON.stringify(body), { status, headers });
}

function normalizeCityKey(value: string) {
  return value
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/\s+/g, "-");
}

function getSupportedCity(value: string | null) {
  if (!value) return null;
  const key = normalizeCityKey(value);
  return SUPPORTED_CITIES.find((city) => city.key === key) ?? null;
}

function parseDetails(value: unknown) {
  if (typeof value !== "string" || !value) return {};
  try {
    const parsed = JSON.parse(value);
    return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : {};
  } catch {
    return {};
  }
}

function isoDate(value: unknown) {
  if (value == null) return null;
  if (value instanceof Date) return value.toISOString();
  const parsed = new Date(String(value));
  return Number.isNaN(parsed.getTime()) ? String(value) : parsed.toISOString();
}

function toNumber(value: unknown, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function round2(value: number) {
  return Math.round((value + Number.EPSILON) * 100) / 100;
}

function formatNumber(value: number) {
  return Number.isInteger(value) ? String(value) : String(Number(value.toFixed(6)));
}

function envNumber(name: string, fallback: number) {
  const value = Netlify.env.get(name);
  if (!value) return fallback;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

async function latestCityObservations(cityKey: string): Promise<CostLineItem[]> {
  const databaseUrl = Netlify.env.get("DATABASE_URL");
  if (!databaseUrl) {
    throw new Error("DATABASE_URL is not configured on Netlify");
  }
  const sql = neon(databaseUrl);
  const rows = await sql`
    select distinct on (category)
      category,
      label,
      monthly_amount,
      currency,
      data_mode,
      source_name,
      source_url,
      observed_at,
      cached_at,
      valid_until,
      confidence,
      methodology,
      details_json,
      created_at
    from cost_observations
    where city_key = ${cityKey}
    order by category, observed_at desc, id desc
  `;

  return rows.map((row) => ({
    category: String(row.category),
    label: String(row.label),
    monthly_amount: toNumber(row.monthly_amount),
    currency: String(row.currency),
    data_mode: String(row.data_mode),
    source_name: String(row.source_name),
    source_url: String(row.source_url),
    observed_at: isoDate(row.observed_at) ?? new Date().toISOString(),
    cached_at: isoDate(row.cached_at) ?? isoDate(row.created_at),
    valid_until: isoDate(row.valid_until),
    confidence: String(row.confidence),
    methodology: String(row.methodology),
    details: parseDetails(row.details_json),
  }));
}

async function renderFallback(req: Request) {
  const apiOrigin = Netlify.env.get("API_ORIGIN");
  const proxySecret = Netlify.env.get("BACKEND_PROXY_SECRET");
  if (!apiOrigin || !proxySecret) {
    return jsonResponse({ detail: "Public API data store is not configured" }, 503);
  }
  const parsedOrigin = new URL(apiOrigin);
  if (parsedOrigin.origin !== EXPECTED_API_ORIGIN) {
    return jsonResponse({ detail: "Backend API origin is not allowed" }, 503);
  }
  const incomingUrl = new URL(req.url);
  const backendUrl = new URL(incomingUrl.pathname, parsedOrigin.origin);
  backendUrl.search = incomingUrl.search;
  const upstream = await fetch(backendUrl, {
    method: req.method,
    headers: {
      accept: req.headers.get("accept") ?? "application/json",
      "x-ishereaffordable-proxy-secret": proxySecret,
      "user-agent": "IsHereAffordableNetlifyPublicApiFallback/0.1",
    },
  });
  const headers = new Headers(upstream.headers);
  headers.delete("content-encoding");
  headers.delete("content-length");
  headers.delete("transfer-encoding");
  headers.set("Cache-Control", upstream.ok ? BROWSER_REVALIDATE : "no-store");
  if (upstream.ok) {
    headers.set("Netlify-CDN-Cache-Control", AFFORDABILITY_CACHE);
  }
  headers.set("x-ishereaffordable-data-origin", "render-fallback");
  return new Response(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers,
  });
}

function calculateMonthlyElectricityBill(averageEurPerKwh: number, profileKey: keyof typeof ELECTRICITY_PROFILES) {
  const profile = ELECTRICITY_PROFILES[profileKey];
  const energyTerm = averageEurPerKwh * profile.monthly_kwh;
  const powerTerm = REGULATED_ELECTRICITY_ASSUMPTIONS.days_per_month * (
    profile.contracted_power_p1_kw * REGULATED_ELECTRICITY_ASSUMPTIONS.power_price_p1_eur_kw_day
    + profile.contracted_power_p2_kw * REGULATED_ELECTRICITY_ASSUMPTIONS.power_price_p2_eur_kw_day
  );
  const subtotalBeforeTax = energyTerm + powerTerm;
  const electricityTax = subtotalBeforeTax * REGULATED_ELECTRICITY_ASSUMPTIONS.electricity_tax_rate;
  const vatBase = subtotalBeforeTax + electricityTax + REGULATED_ELECTRICITY_ASSUMPTIONS.meter_rental_monthly_eur;
  const vat = vatBase * REGULATED_ELECTRICITY_ASSUMPTIONS.vat_rate;
  const monthlyAmount = vatBase + vat;
  return {
    monthly_amount: round2(monthlyAmount),
    energy_term_eur: round2(energyTerm),
    power_term_eur: round2(powerTerm),
    electricity_tax_eur: round2(electricityTax),
    meter_rental_eur: round2(REGULATED_ELECTRICITY_ASSUMPTIONS.meter_rental_monthly_eur),
    vat_eur: round2(vat),
    subtotal_before_tax_eur: round2(subtotalBeforeTax),
  };
}

function applyElectricityProfile(item: CostLineItem, profileKey: keyof typeof ELECTRICITY_PROFILES) {
  const average = item.details.average_eur_per_kwh ?? item.details.seed_variable_eur_per_kwh;
  if (average == null) return item;
  const profile = ELECTRICITY_PROFILES[profileKey];
  const bill = calculateMonthlyElectricityBill(toNumber(average), profileKey);
  const official = item.data_mode === "official_api";
  return {
    ...item,
    monthly_amount: bill.monthly_amount,
    confidence: official ? "medium" : item.confidence,
    source_name: official
      ? "eSIOS PVPC energy term + maintained regulated bill estimate"
      : item.source_name,
    methodology: `${official ? "Official eSIOS PVPC energy-term average for Península" : "Fallback PVPC-style energy-term estimate"}, applied to the ${profile.label.toLowerCase()} profile at ${formatNumber(profile.monthly_kwh)} kWh/month and combined with maintained 2.0TD power-term, meter-rental, electricity-tax, and VAT assumptions.`,
    details: {
      ...item.details,
      electricity_profile: profile.key,
      electricity_profile_label: profile.label,
      electricity_profile_description: profile.description,
      monthly_kwh: profile.monthly_kwh,
      contracted_power_p1_kw: profile.contracted_power_p1_kw,
      contracted_power_p2_kw: profile.contracted_power_p2_kw,
      ...REGULATED_ELECTRICITY_ASSUMPTIONS,
      ...bill,
    },
  };
}

function calculateMonthlyGasBill(
  fixedTermEurMonth: number,
  variableTermEurPerKwh: number,
  profileKey: keyof typeof GAS_PROFILES,
) {
  const profile = GAS_PROFILES[profileKey];
  const hydrocarbonsTaxRate = envNumber("GAS_HYDROCARBONS_TAX_EUR_PER_KWH", 0.00234);
  const vatRate = envNumber("GAS_VAT_RATE_PERCENT", 21) / 100;
  const meterRental = envNumber("GAS_METER_RENTAL_MONTHLY_EUR", 0);
  const fixedTerm = fixedTermEurMonth;
  const variableTerm = variableTermEurPerKwh * profile.monthly_kwh;
  const subtotalBeforeTax = fixedTerm + variableTerm;
  const hydrocarbonsTax = hydrocarbonsTaxRate * profile.monthly_kwh;
  const vatBase = subtotalBeforeTax + hydrocarbonsTax + meterRental;
  const vat = vatBase * vatRate;
  return {
    monthly_amount: round2(vatBase + vat),
    fixed_term_eur: round2(fixedTerm),
    variable_term_eur: round2(variableTerm),
    hydrocarbons_tax_eur: round2(hydrocarbonsTax),
    meter_rental_eur: round2(meterRental),
    vat_eur: round2(vat),
    subtotal_before_tax_eur: round2(subtotalBeforeTax),
    hydrocarbons_tax_eur_per_kwh: hydrocarbonsTaxRate,
    vat_rate: vatRate,
    meter_rental_monthly_eur: meterRental,
  };
}

function gasTermsForProfile(item: CostLineItem, rateCode: string) {
  const gasTerms = item.details.gas_terms;
  if (gasTerms && typeof gasTerms === "object" && !Array.isArray(gasTerms)) {
    const terms = (gasTerms as Record<string, unknown>)[rateCode];
    if (terms && typeof terms === "object" && !Array.isArray(terms)) {
      return terms as Record<string, unknown>;
    }
  }
  if (item.details.fixed_term_eur_month == null || item.details.variable_term_eur_per_kwh == null) {
    return null;
  }
  return item.details;
}

function applyGasProfile(item: CostLineItem, profileKey: keyof typeof GAS_PROFILES) {
  const profile = GAS_PROFILES[profileKey];
  const terms = gasTermsForProfile(item, profile.rate_code);
  if (!terms) return item;
  const bill = calculateMonthlyGasBill(
    toNumber(terms.fixed_term_eur_month),
    toNumber(terms.variable_term_eur_per_kwh),
    profileKey,
  );
  const official = item.data_mode === "official_api";
  return {
    ...item,
    monthly_amount: bill.monthly_amount,
    confidence: official ? "medium" : item.confidence,
    source_name: official ? "BOE TUR gas tariff + maintained tax estimate" : item.source_name,
    methodology: `${official ? "Official BOE TUR gas prices before taxes" : "Fallback regulated gas tariff seed before taxes"}, applied to the ${profile.label.toLowerCase()} profile at ${formatNumber(profile.monthly_kwh)} kWh/month using ${profile.rate_code}, then combined with maintained hydrocarbons-tax and VAT assumptions.`,
    details: {
      ...item.details,
      gas_profile: profile.key,
      gas_profile_label: profile.label,
      gas_profile_description: profile.description,
      monthly_kwh: profile.monthly_kwh,
      annual_kwh: profile.annual_kwh,
      rate_code: profile.rate_code,
      fixed_term_eur_month: round6(toNumber(terms.fixed_term_eur_month)),
      variable_term_eur_per_kwh: round6(toNumber(terms.variable_term_eur_per_kwh)),
      ...bill,
    },
  };
}

function round6(value: number) {
  return Math.round((value + Number.EPSILON) * 1_000_000) / 1_000_000;
}

function applyWaterProfile(item: CostLineItem, profileKey: keyof typeof WATER_PROFILES) {
  const profile = WATER_PROFILES[profileKey];
  const referenceM3 = toNumber(item.details.reference_monthly_m3 ?? item.details.monthly_m3, 6);
  const referenceAmount = toNumber(item.details.reference_monthly_amount_eur ?? item.monthly_amount);
  const scaleFactor = profile.monthly_m3 / referenceM3;
  const scenarioMethodology = profileKey === "standard"
    ? `Standard water usage scenario at ${profile.monthly_m3} m3/month, using the current city estimate as its reference.`
    : `${profile.label} water usage scenario at ${profile.monthly_m3} m3/month, estimated by scaling the ${referenceM3} m3/month city estimate.`;
  return {
    ...item,
    monthly_amount: round2(referenceAmount * scaleFactor),
    methodology: `${scenarioMethodology} This is not an official municipal tariff bill; local fixed fees and progressive bands may make real bills differ.`,
    details: {
      ...item.details,
      water_profile: profile.key,
      water_profile_label: profile.label,
      water_profile_description: profile.description,
      water_profile_rationale: profile.rationale,
      monthly_m3: profile.monthly_m3,
      reference_monthly_m3: referenceM3,
      reference_monthly_amount_eur: referenceAmount,
      profile_scale_factor: round6(scaleFactor),
      profile_sources: WATER_PROFILE_SOURCES,
    },
  };
}

function calculateWasteTariff(rule: Record<string, unknown>, monthlyWaterM3: number) {
  if (rule.kind === "published_city_average") {
    const annualAmount = toNumber(rule.annual_amount_eur);
    return {
      annual_amount_eur: annualAmount,
      annual_min_eur: null,
      annual_max_eur: null,
      amount_kind: "official_city_average",
      methodology: `Official published citywide average of ${annualAmount.toFixed(2)} EUR/year. Exact household bills vary with the property and local generation factors.`,
      details: {},
    };
  }
  if (rule.kind === "water_consumption_bands") {
    const bands = Array.isArray(rule.bands) ? rule.bands as Record<string, unknown>[] : [];
    const dailyM3 = monthlyWaterM3 * 12 / 365;
    const band = bands.find((candidate) => candidate.max_daily_m3 == null || dailyM3 <= toNumber(candidate.max_daily_m3)) ?? bands[bands.length - 1];
    const components = band?.components && typeof band.components === "object" ? band.components as Record<string, number> : {};
    const componentText = Object.entries(components)
      .map(([name, amount]) => `${name} ${Number(amount).toFixed(2)} EUR`)
      .join(" + ");
    return {
      annual_amount_eur: toNumber(band?.annual_amount_eur),
      annual_min_eur: null,
      annual_max_eur: null,
      amount_kind: "water_profile_estimate",
      methodology: `Official annual tariff band for ${formatNumber(monthlyWaterM3)} m3/month (${dailyM3.toFixed(3)} m3/day): ${componentText}. The selected water profile is a usage scenario rather than an actual meter reading.`,
      details: {
        monthly_water_m3: monthlyWaterM3,
        daily_water_m3: round6(dailyM3),
        selected_band: band?.label,
        components,
      },
    };
  }
  const annualMin = toNumber(rule.annual_min_eur);
  const annualMax = toNumber(rule.annual_max_eur);
  const annualAmount = round2((annualMin + annualMax) / 2);
  const referenceProperty = String(rule.reference_property ?? "");
  return {
    annual_amount_eur: annualAmount,
    annual_min_eur: annualMin,
    annual_max_eur: annualMax,
    amount_kind: "official_range_midpoint",
    methodology: `Representative midpoint of the official annual range ${annualMin.toFixed(2)}-${annualMax.toFixed(2)} EUR for ${referenceProperty.toLowerCase()}. The exact bill depends on the property's tariff inputs.`,
    details: { reference_property: referenceProperty },
  };
}

function applyMunicipalWasteProfile(item: CostLineItem, waterProfileKey: keyof typeof WATER_PROFILES) {
  const rule = item.details.tariff_rule;
  if (!rule || typeof rule !== "object" || Array.isArray(rule)) return item;
  const profile = WATER_PROFILES[waterProfileKey];
  const calculation = calculateWasteTariff(rule as Record<string, unknown>, profile.monthly_m3);
  return {
    ...item,
    monthly_amount: round2(calculation.annual_amount_eur / 12),
    methodology: calculation.methodology,
    details: {
      ...item.details,
      ...calculation.details,
      annual_amount: calculation.annual_amount_eur,
      annual_min: calculation.annual_min_eur,
      annual_max: calculation.annual_max_eur,
      amount_kind: calculation.amount_kind,
      water_profile: waterProfileKey,
    },
  };
}

function applyRequestProfiles(
  observations: CostLineItem[],
  electricityProfile: keyof typeof ELECTRICITY_PROFILES,
  gasProfile: keyof typeof GAS_PROFILES,
  waterProfile: keyof typeof WATER_PROFILES,
) {
  return observations.map((item) => {
    if (item.category === "electricity") return applyElectricityProfile(item, electricityProfile);
    if (item.category === "gas") return applyGasProfile(item, gasProfile);
    if (item.category === "water") return applyWaterProfile(item, waterProfile);
    if (item.category === "trash_tax") return applyMunicipalWasteProfile(item, waterProfile);
    return item;
  });
}

function electricityAssumptions(profileKey: keyof typeof ELECTRICITY_PROFILES) {
  const profile = ELECTRICITY_PROFILES[profileKey];
  return [
    `${profile.monthly_kwh} kWh/month electricity usage (${profile.label.toLowerCase()} profile)`,
    "Single-tariff 2.0TD estimate uses maintained regulated power-term assumptions",
    "Electricity bill estimate includes meter rental, electricity tax, and VAT",
  ];
}

function gasAssumptions(profileKey: keyof typeof GAS_PROFILES) {
  const profile = GAS_PROFILES[profileKey];
  return [
    `${profile.monthly_kwh} kWh/month gas usage (${profile.label.toLowerCase()} profile)`,
    `Gas profile uses ${profile.rate_code} based on ${profile.annual_kwh} kWh/year assumed consumption`,
    "Gas bill estimate includes hydrocarbons tax and VAT; meter rental is a maintained assumption",
  ];
}

function waterAssumptions(profileKey: keyof typeof WATER_PROFILES) {
  const profile = WATER_PROFILES[profileKey];
  return [
    `${profile.monthly_m3} m3/month water usage (${profile.label.toLowerCase()} profile)`,
    "Water uses the current city estimate scaled as a simple scenario",
    "Municipal fixed fees, tariff bands and taxes are not yet modelled",
  ];
}

function municipalWasteAssumptions(item: CostLineItem) {
  if (!item.details.tariff_rule) {
    return ["Trash tax remains a manually maintained city estimate"];
  }
  const assumptions = [
    "Trash tax is converted from an annual official tariff to a monthly cost",
    "The displayed trash-tax amount is representative, not an exact tax bill",
  ];
  const required = item.details.exact_inputs_required;
  if (Array.isArray(required) && required.length) {
    assumptions.push(`Exact trash-tax inputs required: ${required.join(", ")}`);
  }
  return assumptions;
}

function publicTransportAssumption(details: Record<string, unknown>) {
  const product = String(details.product_name ?? "published adult transport fare");
  const summary = String(details.calculation_summary ?? "");
  return `Public transport uses ${product}: ${summary}`;
}

function validateLineItems(lineItems: CostLineItem[]) {
  const warnings: string[] = [];
  const now = Date.now();
  for (const item of lineItems) {
    const rule = SOURCE_RULES[item.category];
    if (!rule) {
      warnings.push(`${item.label} has no source rule.`);
      continue;
    }
    if (!rule.allowed_data_modes.includes(item.data_mode)) {
      warnings.push(`${item.label} uses ${item.data_mode}, which is not allowed for ${rule.label}.`);
    }
    if (item.data_mode === "manual_seed") {
      warnings.push(`${item.label} uses manual seed fallback data; preferred source is ${rule.first_choice}.`);
    }
    if (item.data_mode === "unavailable") {
      warnings.push(`${item.label} is unavailable.`);
    }
    if (item.valid_until && new Date(item.valid_until).getTime() < now) {
      warnings.push(`${item.label} tariff validity ended on ${item.valid_until.slice(0, 10)}; refresh the official source.`);
    } else if (rule.freshness_days !== "always") {
      const reference = new Date(item.cached_at ?? item.observed_at).getTime();
      if (reference < now - rule.freshness_days * 24 * 60 * 60 * 1000) {
        warnings.push(`${item.label} is stale; ${rule.label} should refresh within ${rule.freshness_days} days.`);
      }
    }
  }
  return warnings;
}

function estimate(
  city: SupportedCity,
  observations: CostLineItem[],
  electricityProfile: keyof typeof ELECTRICITY_PROFILES,
  gasProfile: keyof typeof GAS_PROFILES,
  waterProfile: keyof typeof WATER_PROFILES,
  safetyMarginPercent: number,
) {
  const adjusted = applyRequestProfiles(observations, electricityProfile, gasProfile, waterProfile);
  const municipalWaste = adjusted.find((item) => item.category === "trash_tax");
  const publicTransport = adjusted.find((item) => item.category === "public_transport");
  const categoryOrder = new Map(CORE_CATEGORIES.map((category, index) => [category, index]));
  const byCategory = new Map(adjusted.map((item) => [item.category, item]));
  const missingCategories = CORE_CATEGORIES.filter((category) => !byCategory.has(category));
  const baselineItems = adjusted
    .filter((item) => item.category !== "safety_margin")
    .sort((left, right) => (categoryOrder.get(left.category) ?? 999) - (categoryOrder.get(right.category) ?? 999));
  const monthlyBaseline = baselineItems.reduce((total, item) => total + item.monthly_amount, 0);
  const monthlySafetyMargin = monthlyBaseline * safetyMarginPercent / 100;
  const now = new Date().toISOString();
  const safetyMargin: CostLineItem = {
    category: "safety_margin",
    label: "Safety margin",
    monthly_amount: round2(monthlySafetyMargin),
    currency: city.currency,
    data_mode: "calculated",
    source_name: "Is Here Affordable formula",
    source_url: "https://github.com/dmatarinl/ishereaffordable",
    observed_at: now,
    cached_at: now,
    valid_until: null,
    confidence: "medium",
    methodology: `${formatNumber(safetyMarginPercent)}% buffer applied to the monthly baseline for irregular expenses and small estimation errors.`,
    details: { safety_margin_percent: safetyMarginPercent },
  };
  const lineItems = [...baselineItems, safetyMargin];
  const warnings = [
    ...missingCategories.map((category) => `Missing cached data for category: ${category}`),
    ...validateLineItems(lineItems),
  ];
  return {
    city: city.name,
    city_key: city.key,
    country: city.country,
    currency: city.currency,
    profile: `Single adult, one-bedroom rental, no car, Spain MVP (${electricityProfile} electricity, ${gasProfile} gas, ${waterProfile} water)`,
    electricity_profile: electricityProfile,
    gas_profile: gasProfile,
    water_profile: waterProfile,
    safety_margin_percent: safetyMarginPercent,
    monthly_baseline: round2(monthlyBaseline),
    monthly_safety_margin: round2(monthlySafetyMargin),
    monthly_required: round2(monthlyBaseline + monthlySafetyMargin),
    annual_required: round2((monthlyBaseline + monthlySafetyMargin) * 12),
    line_items: lineItems,
    assumptions: [
      "One adult household",
      "Long-term one-bedroom rental",
      "No private car ownership",
      ...electricityAssumptions(electricityProfile),
      ...gasAssumptions(gasProfile),
      ...waterAssumptions(waterProfile),
      ...(municipalWaste ? municipalWasteAssumptions(municipalWaste) : []),
      ...(publicTransport ? [publicTransportAssumption(publicTransport.details)] : []),
    ],
    warnings,
    freshness: Object.fromEntries(lineItems.map((item) => [item.category, item.cached_at ?? item.observed_at])),
  };
}

function parseKey<T extends Record<string, unknown>>(value: string | null, fallback: keyof T, catalog: T): keyof T {
  if (value && Object.hasOwn(catalog, value)) {
    return value as keyof T;
  }
  return fallback;
}

async function handleAffordability(req: Request) {
  const url = new URL(req.url);
  const currency = (url.searchParams.get("currency") ?? "EUR").toUpperCase();
  if (currency !== "EUR") {
    return jsonResponse({ detail: "Spain MVP currently supports EUR only." }, 400);
  }
  const city = getSupportedCity(url.searchParams.get("city"));
  if (!city) {
    return jsonResponse({ detail: "City is not supported in the Spain MVP." }, 404);
  }
  const electricityProfile = parseKey(url.searchParams.get("electricity_profile"), "standard", ELECTRICITY_PROFILES);
  const gasProfile = parseKey(url.searchParams.get("gas_profile"), "standard", GAS_PROFILES);
  const waterProfile = parseKey(url.searchParams.get("water_profile"), "standard", WATER_PROFILES);
  const safetyMarginPercent = Math.max(0, toNumber(url.searchParams.get("safety_margin_percent"), 15));
  let observations: CostLineItem[];
  try {
    observations = await latestCityObservations(city.key);
  } catch (error) {
    if (
      error instanceof Error
      && error.message === "DATABASE_URL is not configured on Netlify"
    ) {
      return await renderFallback(req);
    }
    throw error;
  }
  if (!observations.length) {
    return jsonResponse({ detail: "No cached observations found. Run python -m app.jobs.refresh_all." }, 503);
  }
  return jsonResponse(
    estimate(city, observations, electricityProfile, gasProfile, waterProfile, safetyMarginPercent),
    200,
    AFFORDABILITY_CACHE,
  );
}

export default async (req: Request) => {
  if (!["GET", "HEAD"].includes(req.method)) {
    return jsonResponse({ detail: "Method not allowed" }, 405);
  }

  try {
    const path = new URL(req.url).pathname;
    if (path === "/api/cities") {
      return jsonResponse({ cities: SUPPORTED_CITIES }, 200, STABLE_READ_CACHE);
    }
    if (path === "/api/electricity/profiles") {
      return jsonResponse(
        { default: "standard", profiles: Object.values(ELECTRICITY_PROFILES) },
        200,
        STABLE_READ_CACHE,
      );
    }
    if (path === "/api/gas/profiles") {
      return jsonResponse(
        { default: "standard", profiles: Object.values(GAS_PROFILES) },
        200,
        STABLE_READ_CACHE,
      );
    }
    if (path === "/api/water/profiles") {
      return jsonResponse(
        {
          default: "standard",
          profiles: Object.values(WATER_PROFILES),
          methodology: WATER_PROFILE_METHODOLOGY,
          sources: WATER_PROFILE_SOURCES,
        },
        200,
        STABLE_READ_CACHE,
      );
    }
    if (path === "/api/affordability") {
      return await handleAffordability(req);
    }
    return jsonResponse({ detail: "Not found" }, 404);
  } catch (error) {
    return jsonResponse(
      {
        detail: error instanceof Error ? error.message : "Public API is unavailable",
      },
      503,
    );
  }
};

export const config = {
  path: [
    "/api/affordability",
    "/api/cities",
    "/api/electricity/profiles",
    "/api/gas/profiles",
    "/api/water/profiles",
  ],
};
