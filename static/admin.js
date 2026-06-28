const state = {
  token: sessionStorage.getItem("iha_admin_token") || "",
  payload: null,
};

const elements = {
  authForm: document.querySelector("#admin-auth-form"),
  adminKey: document.querySelector("#admin-key"),
  forgetKey: document.querySelector("#forget-key"),
  adminContent: document.querySelector("#admin-content"),
  message: document.querySelector("#admin-message"),
  latestCache: document.querySelector("#latest-cache"),
  sourcesTotal: document.querySelector("#sources-total"),
  sourcesIssues: document.querySelector("#sources-issues"),
  observationsTotal: document.querySelector("#observations-total"),
  refreshCity: document.querySelector("#refresh-city"),
  refreshButton: document.querySelector("#refresh-button"),
  reloadStatus: document.querySelector("#reload-status"),
  manualRefreshState: document.querySelector("#manual-refresh-state"),
  manualRefreshResults: document.querySelector("#manual-refresh-results"),
  sourcesTable: document.querySelector("#sources-table"),
  observationCity: document.querySelector("#observation-city"),
  observationsTable: document.querySelector("#observations-table"),
};

function setMessage(message, isError = false) {
  elements.message.textContent = message;
  elements.message.style.color = isError ? "#a83f32" : "#5f6875";
}

function formatDate(value) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "-";
  }
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function labelForMode(value) {
  return String(value || "-").replaceAll("_", " ");
}

function badge(text, modifier) {
  const badgeElement = document.createElement("span");
  const normalizedModifier = String(modifier || "unknown").replaceAll("_", "-");
  badgeElement.className = `badge badge-${normalizedModifier}`;
  badgeElement.textContent = text;
  return badgeElement;
}

function clear(element) {
  while (element.firstChild) {
    element.removeChild(element.firstChild);
  }
}

function appendCell(row, value) {
  const cell = document.createElement("td");
  if (value instanceof Node) {
    cell.append(value);
  } else {
    cell.textContent = value;
  }
  row.append(cell);
}

async function adminFetch(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      ...(options.headers || {}),
      authorization: `Bearer ${state.token}`,
    },
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail || "Admin request failed");
  }
  return payload;
}

function renderCityOptions(cities) {
  const existingRefreshCity = elements.refreshCity.value;
  const existingObservationCity = elements.observationCity.value;
  clear(elements.refreshCity);
  clear(elements.observationCity);

  const allRefresh = document.createElement("option");
  allRefresh.value = "";
  allRefresh.textContent = "All cities";
  elements.refreshCity.append(allRefresh);

  const allObservation = document.createElement("option");
  allObservation.value = "";
  allObservation.textContent = "All cities";
  elements.observationCity.append(allObservation);

  for (const city of cities) {
    const refreshOption = document.createElement("option");
    refreshOption.value = city.name;
    refreshOption.textContent = city.name;
    elements.refreshCity.append(refreshOption);

    const observationOption = document.createElement("option");
    observationOption.value = city.key;
    observationOption.textContent = city.name;
    elements.observationCity.append(observationOption);
  }

  elements.refreshCity.value = existingRefreshCity;
  elements.observationCity.value = existingObservationCity;
}

function renderSummary(summary) {
  elements.latestCache.textContent = formatDate(summary.latest_cached_at);
  elements.sourcesTotal.textContent = String(summary.sources_total);
  elements.sourcesIssues.textContent = String(
    summary.sources_failed + summary.sources_degraded,
  );
  elements.observationsTotal.textContent = String(summary.observations_total);
}

function renderManualRefresh(manualRefresh) {
  if (!manualRefresh.last_status) {
    elements.manualRefreshState.textContent =
      "No manual refresh has run in this server session.";
  } else {
    elements.manualRefreshState.textContent = [
      labelForMode(manualRefresh.last_status),
      `scope: ${manualRefresh.last_scope || "-"}`,
      `started: ${formatDate(manualRefresh.last_started_at)}`,
      `finished: ${formatDate(manualRefresh.last_finished_at)}`,
      manualRefresh.last_message || "",
    ]
      .filter(Boolean)
      .join(" · ");
  }

  clear(elements.manualRefreshResults);
  for (const result of manualRefresh.last_results || []) {
    const item = document.createElement("li");
    item.textContent = `${result.city_key}: ${result.observations} observations`;
    elements.manualRefreshResults.append(item);
  }
}

function renderSources(sources) {
  clear(elements.sourcesTable);
  for (const source of sources) {
    const row = document.createElement("tr");
    appendCell(row, source.source_name);
    appendCell(row, badge(source.status, source.status));
    appendCell(row, formatDate(source.last_started_at));
    appendCell(row, formatDate(source.last_finished_at));
    appendCell(row, source.message || "-");
    elements.sourcesTable.append(row);
  }
}

function renderObservations(observations) {
  clear(elements.observationsTable);
  const cityFilter = elements.observationCity.value;
  const visibleObservations = cityFilter
    ? observations.filter((item) => item.city_key === cityFilter)
    : observations;

  for (const item of visibleObservations) {
    const row = document.createElement("tr");
    appendCell(row, item.city);
    appendCell(row, labelForMode(item.category));
    appendCell(row, badge(labelForMode(item.data_mode), item.data_mode));
    appendCell(row, item.source_name);
    appendCell(row, formatDate(item.observed_at));
    appendCell(row, formatDate(item.cached_at));
    appendCell(row, formatDate(item.valid_until));
    elements.observationsTable.append(row);
  }
}

function render(payload) {
  state.payload = payload;
  elements.adminContent.hidden = false;
  renderCityOptions(payload.cities);
  renderSummary(payload.summary);
  renderManualRefresh(payload.manual_refresh);
  renderSources(payload.sources);
  renderObservations(payload.observations);
}

async function loadStatus() {
  setMessage("Loading admin status...");
  const payload = await adminFetch("/admin-api/sources/status");
  render(payload);
  setMessage("Admin status loaded.");
}

async function runRefresh() {
  const city = elements.refreshCity.value;
  const query = city ? `?city=${encodeURIComponent(city)}` : "";
  elements.refreshButton.disabled = true;
  setMessage(`Queueing refresh for ${city || "all cities"}...`);
  try {
    const payload = await adminFetch(`/admin-api/refresh${query}`, {
      method: "POST",
    });
    setMessage(payload.message || "Refresh queued.");
    await loadStatus();
  } finally {
    elements.refreshButton.disabled = false;
  }
}

elements.authForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  state.token = elements.adminKey.value.trim();
  sessionStorage.setItem("iha_admin_token", state.token);
  try {
    await loadStatus();
  } catch (error) {
    sessionStorage.removeItem("iha_admin_token");
    setMessage(error.message, true);
  }
});

elements.forgetKey.addEventListener("click", () => {
  state.token = "";
  elements.adminKey.value = "";
  elements.adminContent.hidden = true;
  sessionStorage.removeItem("iha_admin_token");
  setMessage("Admin key forgotten.");
});

elements.reloadStatus.addEventListener("click", () => {
  loadStatus().catch((error) => setMessage(error.message, true));
});

elements.refreshButton.addEventListener("click", () => {
  runRefresh().catch((error) => setMessage(error.message, true));
});

elements.observationCity.addEventListener("change", () => {
  if (state.payload) {
    renderObservations(state.payload.observations);
  }
});

if (state.token) {
  elements.adminKey.value = state.token;
  loadStatus().catch((error) => setMessage(error.message, true));
}
