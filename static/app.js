const form = document.querySelector("#calculator-form");
const citySelect = document.querySelector("#city");
const electricityProfileGroup = document.querySelector("#electricity-profile");
const gasProfileGroup = document.querySelector("#gas-profile");
const waterProfileGroup = document.querySelector("#water-profile");
const waterProfileHelp = document.querySelector(
  "#water-profile-help-content",
);
const waterProfileHelpControl = document.querySelector(".profile-help");
const customSafetyMarginInput = document.querySelector("#custom-safety-margin");
const calculateButton = document.querySelector("#calculate-button");
const result = document.querySelector("#result");
let appReady = false;
let activeCalculationId = 0;
let customMarginTimer;

const formatMoney = (value, currency) =>
  new Intl.NumberFormat("en", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(value);

const formatFare = (value, currency) =>
  new Intl.NumberFormat("en", {
    style: "currency",
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(value);

const formatDate = (value) =>
  new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));

const escapeHtml = (value) =>
  String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");

const escapeAttr = escapeHtml;

const cssToken = (value) =>
  String(value ?? "").replace(/[^a-zA-Z0-9_-]/g, "");

const safeExternalUrl = (value) => {
  try {
    const url = new URL(String(value ?? ""), window.location.origin);
    if (url.protocol === "https:" || url.protocol === "http:") {
      return url.href;
    }
  } catch (error) {
    return "#";
  }
  return "#";
};

const categoryLabels = {
  rent: "Rent",
  electricity: "Electricity",
  gas: "Gas",
  water: "Water",
  trash_tax: "Trash tax",
  food: "Food",
  public_transport: "Public transport",
  safety_margin: "Safety margin",
};

const dataModeLabels = {
  official_api: "Official API",
  official_publication: "Official publication",
  permitted_scrape: "Permitted scrape",
  manual_seed: "City estimate",
  calculated: "Calculated",
  unavailable: "Unavailable",
};

const sleep = (milliseconds) =>
  new Promise((resolve) => {
    window.setTimeout(resolve, milliseconds);
  });

const shouldRetryStatus = (status) =>
  [408, 429, 500, 502, 503, 504].includes(status);

async function fetchJsonWithRetry(url, label, options = {}) {
  const retries = options.retries ?? 4;
  const delays = options.delays ?? [500, 1000, 1800, 3000];
  let lastError = new Error(`Could not load ${label}`);

  for (let attempt = 0; attempt <= retries; attempt += 1) {
    try {
      const response = await fetch(url, {
        headers: { accept: "application/json" },
      });
      let payload = {};
      try {
        payload = await response.json();
      } catch {
        payload = {};
      }

      if (response.ok) {
        return payload;
      }

      const detail = payload.detail ? String(payload.detail) : response.statusText;
      lastError = new Error(detail || `Could not load ${label}`);
      lastError.retryable = shouldRetryStatus(response.status);
      if (!lastError.retryable || attempt === retries) {
        throw lastError;
      }
    } catch (error) {
      lastError = error instanceof Error
        ? error
        : new Error(`Could not load ${label}`);
      if (lastError.retryable === false || attempt === retries) {
        throw lastError;
      }
    }

    await sleep(delays[Math.min(attempt, delays.length - 1)]);
  }

  throw lastError;
}

async function loadCities() {
  const payload = await fetchJsonWithRetry("/api/cities", "cities");
  citySelect.innerHTML = payload.cities
    .map(
      (city) =>
        `<option value="${escapeAttr(city.key)}">${escapeHtml(city.name)}</option>`,
    )
    .join("");
  citySelect.disabled = false;
}

async function loadElectricityProfiles() {
  const payload = await fetchJsonWithRetry(
    "/api/electricity/profiles",
    "electricity profiles",
  );
  electricityProfileGroup.innerHTML = payload.profiles
    .map(
      (profile) =>
        `<label>
          <input
            type="radio"
            name="electricity_profile"
            value="${escapeAttr(profile.key)}"
            ${profile.key === payload.default ? "checked" : ""}
          />
          ${escapeHtml(profile.label)}
        </label>`,
    )
    .join("");
  electricityProfileGroup.removeAttribute("aria-busy");
}

async function loadGasProfiles() {
  const payload = await fetchJsonWithRetry("/api/gas/profiles", "gas profiles");
  gasProfileGroup.innerHTML = payload.profiles
    .map(
      (profile) =>
        `<label>
          <input
            type="radio"
            name="gas_profile"
            value="${escapeAttr(profile.key)}"
            ${profile.key === payload.default ? "checked" : ""}
          />
          ${escapeHtml(profile.label)}
        </label>`,
    )
    .join("");
  gasProfileGroup.removeAttribute("aria-busy");
}

async function loadWaterProfiles() {
  const payload = await fetchJsonWithRetry(
    "/api/water/profiles",
    "water profiles",
  );
  waterProfileGroup.innerHTML = payload.profiles
    .map(
      (profile) =>
        `<label title="${escapeAttr(profile.description)}">
          <input
            type="radio"
            name="water_profile"
            value="${escapeAttr(profile.key)}"
            ${profile.key === payload.default ? "checked" : ""}
          />
          ${escapeHtml(profile.label)}
        </label>`,
    )
    .join("");
  waterProfileGroup.removeAttribute("aria-busy");

  const profileReasons = payload.profiles
    .map(
      (profile) =>
        `<li><strong>${escapeHtml(profile.label)}: ${escapeHtml(profile.monthly_m3)} m&sup3;</strong> - ${escapeHtml(profile.rationale)}</li>`,
    )
    .join("");
  const sourceLinks = payload.sources
    .map(
      (source) =>
        `<a href="${escapeAttr(safeExternalUrl(source.url))}" target="_blank" rel="noopener noreferrer" title="${escapeAttr(source.relevance)}">${escapeHtml(source.name)}</a>`,
    )
    .join(" · ");

  waterProfileHelp.innerHTML = `
    <strong>Why 4, 6 and 9 m&sup3;?</strong>
    <p>${escapeHtml(payload.methodology)}</p>
    <ul>${profileReasons}</ul>
    <div>Sources: ${sourceLinks}</div>
  `;
}

function setStartupLoading() {
  calculateButton.disabled = true;
  calculateButton.textContent = "Loading data...";
  result.hidden = false;
  result.className = "result loading-card";
  result.innerHTML = `
    <div class="loading-spinner" aria-hidden="true"></div>
    <strong>Loading latest cached data</strong>
    <span>Preparing city, utility and profile data from the server.</span>
  `;
}

function setStartupError(message) {
  calculateButton.disabled = true;
  calculateButton.textContent = "Try again";
  result.hidden = false;
  result.className = "result";
  result.innerHTML = `
    <div class="warnings">
      <strong>Data could not load</strong>
      <p>${escapeHtml(message)}. Please refresh the page in a moment.</p>
    </div>
  `;
}

function setReadyState() {
  appReady = true;
  calculateButton.disabled = false;
  calculateButton.textContent = "Calculate";
}

function selectedRadioValue(name) {
  return document.querySelector(`input[name="${name}"]:checked`)?.value;
}

function selectedSafetyMargin() {
  const option = selectedRadioValue("safety_margin_option");
  if (option === "custom") {
    return customSafetyMarginInput.value || "0";
  }
  return option || "15";
}

function updateCustomSafetyMarginVisibility() {
  const isCustom = selectedRadioValue("safety_margin_option") === "custom";
  customSafetyMarginInput.hidden = !isCustom;
}

function renderWarnings(warnings) {
  if (!warnings.length) return "";
  return `
    <div class="warnings">
      <strong>Data warnings</strong>
      <ul>${warnings.map((warning) => `<li>${escapeHtml(warning)}</li>`).join("")}</ul>
    </div>
  `;
}

function renderLineItem(item, currency) {
  const label = categoryLabels[item.category] ?? item.label;
  const dataModeLabel = dataModeLabels[item.data_mode] ?? item.data_mode;
  const dataModeClass = `badge mode ${cssToken(item.data_mode)}`;
  const sourceTimeline = renderSourceTimeline(item);
  return `
    <div class="row">
      <div>
        <div class="row-title">
          <span>${escapeHtml(label)}</span>
          <span class="${escapeAttr(dataModeClass)}">${escapeHtml(dataModeLabel)}</span>
        </div>
        <div class="source">
          <span class="source-meta">${escapeHtml(item.source_name)} · ${escapeHtml(sourceTimeline)}</span>
          <br />${escapeHtml(item.methodology)}
        </div>
        ${renderTransportBasis(item, currency)}
      </div>
      <strong>${formatMoney(item.monthly_amount, currency)}</strong>
    </div>
  `;
}

function renderTransportBasis(item, currency) {
  if (item.category !== "public_transport") return "";

  const details = item.details ?? {};
  const included = (details.modes_included ?? []).map(escapeHtml).join(", ");
  const excluded = (details.excluded_modes ?? []).map(escapeHtml).join(", ");
  const baseFare = details.base_monthly_amount_eur;
  const fareComparison = baseFare
    ? `Current fare ${formatFare(item.monthly_amount, currency)}; published base fare ${formatFare(baseFare, currency)}.`
    : `Current fare ${formatFare(item.monthly_amount, currency)}.`;
  const excludedLine = excluded
    ? `<span><strong>Not included:</strong> ${excluded}.</span>`
    : "";

  return `
    <div class="calculation-basis">
      <span><strong>Calculation used:</strong> ${escapeHtml(details.product_name)}.</span>
      <span>${escapeHtml(details.calculation_summary)}</span>
      <span><strong>Included:</strong> ${included}.</span>
      ${excludedLine}
      <span>${escapeHtml(fareComparison)}</span>
    </div>
  `;
}

function renderSourceTimeline(item) {
  const cachedAt = item.cached_at ? formatDate(item.cached_at) : "unknown cache time";
  const observedAt = item.observed_at
    ? formatDate(item.observed_at)
    : "source observation unavailable";
  const validUntil = item.valid_until
    ? ` · valid until ${formatDate(item.valid_until)}`
    : "";

  if (item.data_mode === "manual_seed") {
    return `city estimate cached ${cachedAt}${validUntil}`;
  }
  if (item.data_mode === "official_api") {
    return `official source observed ${observedAt} · cached ${cachedAt}${validUntil}`;
  }
  if (item.data_mode === "official_publication") {
    return `official tariff published ${observedAt} · cached ${cachedAt}${validUntil}`;
  }
  if (item.data_mode === "permitted_scrape") {
    return `permitted scrape observed ${observedAt} · cached ${cachedAt}${validUntil}`;
  }
  if (item.data_mode === "calculated") {
    return `calculated by formula ${cachedAt}${validUntil}`;
  }
  return `unavailable · cached ${cachedAt}${validUntil}`;
}

async function calculate() {
  if (!appReady) return;

  const params = new URLSearchParams({
    city: citySelect.value,
    currency: "EUR",
    electricity_profile: selectedRadioValue("electricity_profile"),
    gas_profile: selectedRadioValue("gas_profile"),
    water_profile: selectedRadioValue("water_profile"),
    safety_margin_percent: selectedSafetyMargin(),
  });

  const calculationId = activeCalculationId + 1;
  activeCalculationId = calculationId;
  result.hidden = false;
  calculateButton.disabled = true;
  calculateButton.textContent = "Updating...";

  const hasEstimate = result.querySelector(".amount");
  if (hasEstimate) {
    result.classList.add("is-updating");
    result.setAttribute("aria-busy", "true");
  } else {
    result.className = "result loading-card";
    result.innerHTML = `
      <div class="loading-spinner" aria-hidden="true"></div>
      <strong>Loading latest cached estimate</strong>
      <span>Waking the public API if needed and reading cached observations.</span>
    `;
  }

  let estimate;
  try {
    estimate = await fetchJsonWithRetry(
      `/api/affordability?${params.toString()}`,
      "estimate",
      { retries: 5, delays: [600, 1200, 2200, 3500, 5000] },
    );
  } catch (error) {
    if (calculationId !== activeCalculationId) return;
    calculateButton.disabled = false;
    calculateButton.textContent = "Calculate";
    result.className = "result";
    result.removeAttribute("aria-busy");
    result.innerHTML = `
      <div class="warnings">
        <strong>Estimate is temporarily unavailable</strong>
        <p>${escapeHtml(error.message || "The public API is taking longer than expected")}. Please try again in a moment.</p>
      </div>
    `;
    return;
  }

  if (calculationId !== activeCalculationId) return;

  calculateButton.disabled = false;
  calculateButton.textContent = "Calculate";
  result.classList.remove("is-updating");
  result.removeAttribute("aria-busy");

  result.className = "result";
  result.innerHTML = `
    <div>${escapeHtml(estimate.city)}, ${escapeHtml(estimate.country)}</div>
    <div class="amount">${formatMoney(estimate.monthly_required, estimate.currency)}</div>
    <div>per month</div>
    <div class="source">${escapeHtml(estimate.profile)}</div>
    <div class="summary">
      <div class="metric"><span>Baseline</span><strong>${formatMoney(estimate.monthly_baseline, estimate.currency)}</strong></div>
      <div class="metric"><span>Safety margin</span><strong>${formatMoney(estimate.monthly_safety_margin, estimate.currency)}</strong></div>
      <div class="metric"><span>Annual target</span><strong>${formatMoney(estimate.annual_required, estimate.currency)}</strong></div>
    </div>
    <div class="breakdown-heading">
      <strong>Cost breakdown</strong>
      <details class="profile-help source-help">
        <summary
          aria-label="What do source labels mean?"
          title="What do source labels mean?"
        >i</summary>
        <div class="profile-tooltip">
          <strong>How each amount is sourced</strong>
          <ul>
            <li><strong>Official API:</strong> current data retrieved from an official API and cached on our server.</li>
            <li><strong>Official publication:</strong> a tariff, average, or rule taken from an official public document.</li>
            <li><strong>City estimate:</strong> a maintained city reference used while the preferred source integration is pending.</li>
            <li><strong>Calculated:</strong> an amount derived by the app from the selected profile and displayed costs.</li>
          </ul>
        </div>
      </details>
    </div>
    <div class="breakdown">
      ${estimate.line_items.map((item) => renderLineItem(item, estimate.currency)).join("")}
    </div>
    ${renderWarnings(estimate.warnings)}
  `;

  result.querySelectorAll(".profile-help").forEach(setupHoverHelp);

}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  calculate();
});

form.addEventListener("change", (event) => {
  if (event.target.name === "safety_margin_option") {
    updateCustomSafetyMarginVisibility();
  }
  if (
    event.target.name === "city" ||
    event.target.name === "electricity_profile" ||
    event.target.name === "gas_profile" ||
    event.target.name === "water_profile" ||
    event.target.name === "safety_margin_option"
  ) {
    calculate();
  }
});

customSafetyMarginInput.addEventListener("input", () => {
  window.clearTimeout(customMarginTimer);
  customMarginTimer = window.setTimeout(calculate, 250);
});

const usesDesktopHover = () =>
  window.matchMedia(
    "(min-width: 861px) and (hover: hover) and (pointer: fine)",
  ).matches;

function setupHoverHelp(control) {
  if (!control || control.dataset.helpReady === "true") return;
  control.dataset.helpReady = "true";
  const summary = control.querySelector("summary");
  let closeTimer;

  control.addEventListener("mouseenter", () => {
    if (usesDesktopHover()) {
      window.clearTimeout(closeTimer);
      control.open = true;
    }
  });

  control.addEventListener("mouseleave", () => {
    if (usesDesktopHover()) {
      closeTimer = window.setTimeout(() => {
        control.open = false;
      }, 350);
    }
  });

  control.addEventListener("focusin", () => {
    if (usesDesktopHover()) control.open = true;
  });

  control.addEventListener("focusout", (event) => {
    if (usesDesktopHover() && !control.contains(event.relatedTarget)) {
      control.open = false;
    }
  });

  summary.addEventListener("click", (event) => {
    if (usesDesktopHover()) event.preventDefault();
  });
}

setupHoverHelp(waterProfileHelpControl);
setStartupLoading();

Promise.all([
  loadCities(),
  loadElectricityProfiles(),
  loadGasProfiles(),
  loadWaterProfiles(),
])
  .then(() => {
    setReadyState();
    calculate();
  })
  .catch((error) => {
    setStartupError(error.message || "The public API is temporarily unavailable");
  });
