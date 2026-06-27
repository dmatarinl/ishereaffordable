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
const result = document.querySelector("#result");

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

async function loadCities() {
  const response = await fetch("/api/cities");
  const payload = await response.json();
  citySelect.innerHTML = payload.cities
    .map(
      (city) =>
        `<option value="${escapeAttr(city.key)}">${escapeHtml(city.name)}</option>`,
    )
    .join("");
}

async function loadElectricityProfiles() {
  const response = await fetch("/api/electricity/profiles");
  const payload = await response.json();
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
}

async function loadGasProfiles() {
  const response = await fetch("/api/gas/profiles");
  const payload = await response.json();
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
}

async function loadWaterProfiles() {
  const response = await fetch("/api/water/profiles");
  const payload = await response.json();
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
  const params = new URLSearchParams({
    city: citySelect.value,
    currency: "EUR",
    electricity_profile: selectedRadioValue("electricity_profile"),
    gas_profile: selectedRadioValue("gas_profile"),
    water_profile: selectedRadioValue("water_profile"),
    safety_margin_percent: selectedSafetyMargin(),
  });

  result.hidden = false;
  result.textContent = "Calculating...";

  const response = await fetch(`/api/affordability?${params.toString()}`);
  const estimate = await response.json();

  if (!response.ok) {
    result.innerHTML = `<div class="warnings">${escapeHtml(estimate.detail)}</div>`;
    return;
  }

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

customSafetyMarginInput.addEventListener("input", calculate);

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

Promise.all([
  loadCities(),
  loadElectricityProfiles(),
  loadGasProfiles(),
  loadWaterProfiles(),
]).then(calculate);
