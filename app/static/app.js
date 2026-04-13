const state = {
  scenarios: [],
  datasets: [],
  workspaces: [],
  runs: [],
  platform: null,
  selectedRunId: null,
};

function formatPct(value) {
  return `${(Number(value) * 100).toFixed(2)}%`;
}

function formatNum(value) {
  return Number(value).toFixed(2);
}

async function getJson(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    throw new Error(`Request failed: ${url}`);
  }
  return response.json();
}

function renderSystemCard(system) {
  document.getElementById("system-card").innerHTML = `
    <h2>Runtime Snapshot</h2>
    <div class="metric-grid">
      <div class="metric"><span>Runtime</span><strong>${system.runtime}</strong></div>
      <div class="metric"><span>Scenarios</span><strong>${system.scenario_count}</strong></div>
      <div class="metric"><span>Datasets</span><strong>${system.dataset_count}</strong></div>
      <div class="metric"><span>Workspaces</span><strong>${system.workspace_count}</strong></div>
      <div class="metric"><span>Platform components</span><strong>${system.platform_component_count}</strong></div>
      <div class="metric"><span>Validation gates</span><strong>${system.validation_gate_count}</strong></div>
    </div>
    <p class="check">Runs are persisted locally and each completed experiment now carries lineage, validation, attribution, and tear-sheet artifacts for review.</p>
  `;
}

function renderScenarioOptions() {
  const scenarioSelect = document.getElementById("scenario-select");
  scenarioSelect.innerHTML = state.scenarios
    .map((scenario) => `<option value="${scenario.scenario_id}">${scenario.name}</option>`)
    .join("");

  document.getElementById("scenario-count").textContent = `${state.scenarios.length} strategies`;
  document.getElementById("scenario-list").innerHTML = state.scenarios
    .map(
      (scenario) => `
        <article class="card">
          <h3>${scenario.name}</h3>
          <p>${scenario.description}</p>
          <p><strong>Score:</strong> ${scenario.score_column}</p>
          <p><strong>Holding period:</strong> ${scenario.holding_period} trading days</p>
        </article>
      `
    )
    .join("");
}

function renderDatasets() {
  const datasetSelect = document.getElementById("dataset-select");
  datasetSelect.innerHTML = state.datasets
    .map((dataset) => `<option value="${dataset.dataset_id}">${dataset.name}</option>`)
    .join("");
}

function renderWorkspaces() {
  const workspaceSelect = document.getElementById("workspace-select");
  workspaceSelect.innerHTML = state.workspaces
    .map((workspace) => `<option value="${workspace.workspace_id}">${workspace.name}</option>`)
    .join("");
  document.getElementById("workspace-count").textContent = `${state.workspaces.length} workspaces`;
}

function renderResources(resources) {
  document.getElementById("resource-list").innerHTML = resources
    .map(
      (resource) => `
        <article class="card">
          <h3>${resource.title}</h3>
          <p>${resource.summary}</p>
          <p><strong>${resource.category}</strong></p>
          <a href="${resource.url}" target="_blank" rel="noreferrer">Open source</a>
        </article>
      `
    )
    .join("");
}

function renderPlatform(platform) {
  document.getElementById("platform-panel").innerHTML = `
    <article class="card">
      <h3>${platform.platform_name}</h3>
      <p>This repo now shows the platform layer behind the backtests: point-in-time data, experiment lineage, risk gates, and artifact bundles.</p>
      <div class="chip-row">
        ${platform.validation_gates.map((gate) => `<span class="tag">${gate}</span>`).join("")}
      </div>
    </article>
    ${platform.components
      .map(
        (component) => `
          <article class="card">
            <div class="panel-head">
              <h3>${component.name}</h3>
              <span>${component.layer}</span>
            </div>
            <p>${component.role}</p>
          </article>
        `
      )
      .join("")}
  `;
}

function renderRuns() {
  const runList = document.getElementById("run-list");
  if (!state.runs.length) {
    runList.innerHTML = `<div class="detail-empty">No runs yet. Launch one from the composer.</div>`;
    return;
  }
  runList.innerHTML = state.runs
    .map(
      (run) => `
        <article class="card">
          <label><input type="checkbox" class="compare-check" value="${run.run_id}" /> Compare</label>
          <h3>${run.label}</h3>
          <p>${run.summary?.scenario_name || run.scenario_id}</p>
          <div class="metric-grid">
            <div class="metric"><span>Return</span><strong>${run.summary ? formatPct(run.summary.annualized_return) : "-"}</strong></div>
            <div class="metric"><span>Sharpe</span><strong>${run.summary ? formatNum(run.summary.sharpe_ratio) : "-"}</strong></div>
            <div class="metric"><span>Drawdown</span><strong>${run.summary ? formatPct(run.summary.max_drawdown) : "-"}</strong></div>
            <div class="metric"><span>Alpha</span><strong>${run.summary ? formatPct(run.summary.alpha_annualized) : "-"}</strong></div>
            <div class="metric"><span>Readiness</span><strong>${run.platform_summary ? formatNum(run.platform_summary.research_readiness) : "-"}</strong></div>
          </div>
          <div class="run-actions">
            <button data-run-detail="${run.run_id}">Inspect</button>
            <button data-run-replay="${run.run_id}">Replay</button>
          </div>
        </article>
      `
    )
    .join("");
}

function renderRunDetail(run) {
  state.selectedRunId = run.run_id;
  const validation = run.validation_report || { overall_status: "n/a", gates: [] };
  const platformSummary = run.platform_summary || { research_readiness: 0, execution_mode: "n/a", tracker: {}, component_health: [] };
  const attribution = run.attribution || { factor_contributions: [], sector_contributions: [], diagnostics: {} };
  const lineage = run.lineage || { config_fingerprint: "n/a", dataset_snapshot: { dataset_version: "n/a" } };
  document.getElementById("detail-label").textContent = run.label;
  document.getElementById("run-detail").innerHTML = `
    <div class="metric-grid">
      <div class="metric"><span>Annualized return</span><strong>${formatPct(run.summary.annualized_return)}</strong></div>
      <div class="metric"><span>Sharpe ratio</span><strong>${formatNum(run.summary.sharpe_ratio)}</strong></div>
      <div class="metric"><span>Max drawdown</span><strong>${formatPct(run.summary.max_drawdown)}</strong></div>
      <div class="metric"><span>Average turnover</span><strong>${formatNum(run.summary.average_turnover)}</strong></div>
      <div class="metric"><span>Research readiness</span><strong>${formatNum(platformSummary.research_readiness)}</strong></div>
      <div class="metric"><span>Execution mode</span><strong>${platformSummary.execution_mode}</strong></div>
    </div>
    <p><strong>Scenario:</strong> ${run.summary.scenario_name}</p>
    <p><strong>Periods:</strong> ${run.summary.period_count}</p>
    <p><strong>Dataset:</strong> ${run.dataset_id}</p>
    <p><strong>Seed:</strong> ${run.seed}</p>
    <p><strong>Fingerprint:</strong> <code>${lineage.config_fingerprint}</code></p>
    <p><strong>Dataset version:</strong> ${lineage.dataset_snapshot.dataset_version}</p>
    <div class="chip-row">
      <span class="status-chip">Validation: ${validation.overall_status}</span>
      <span class="status-chip">Rebalances: ${run.summary.rebalance_count}</span>
      <span class="status-chip">Capacity proxy: ${formatNum(run.summary.median_capacity_proxy)}</span>
    </div>
    <div class="split-list">
      <div class="mini-list">
        <div class="mini-card">
          <h4>Validation gates</h4>
          ${validation.gates
            .map((gate) => `<p><strong>${gate.name}</strong>: ${gate.status} (${gate.actual} vs ${gate.threshold})</p>`)
            .join("")}
        </div>
      </div>
      <div class="mini-list">
        <div class="mini-card">
          <h4>Top factor attribution</h4>
          ${attribution.factor_contributions
            .slice(0, 4)
            .map(
              (row) =>
                `<p><strong>${row.factor}</strong>: ${formatPct(row.contribution)} contribution, mean exposure ${formatNum(
                  row.mean_exposure
                )}</p>`
            )
            .join("")}
        </div>
      </div>
    </div>
  `;

  const artifacts = Object.entries(run.artifacts || {});
  const preview = artifacts
    .filter(([name]) => name.endsWith(".svg"))
    .slice(0, 3)
    .map(([name]) => `<img src="/api/artifacts/${run.run_id}/${name}" alt="${name}" />`)
    .join("");
  const artifactLinks = artifacts
    .map(([name]) => `<a href="/api/artifacts/${run.run_id}/${name}" target="_blank" rel="noreferrer">${name}</a>`)
    .join("");
  document.getElementById("artifact-preview").innerHTML = `
    ${preview}
    <div class="artifact-list">${artifactLinks}</div>
  `;
}

function renderComparison(rows) {
  if (!rows.length) {
    document.getElementById("comparison-table").innerHTML = `<div class="detail-empty">Select at least two runs.</div>`;
    return;
  }
  const header = `
    <table>
      <thead>
        <tr>
          <th>Label</th>
          <th>Scenario</th>
          <th>Annualized Return</th>
          <th>Sharpe</th>
          <th>Drawdown</th>
          <th>Alpha</th>
          <th>Turnover</th>
          <th>Readiness</th>
          <th>Fingerprint</th>
        </tr>
      </thead>
      <tbody>
  `;
  const body = rows
    .map(
      (row) => `
        <tr>
          <td>${row.label}</td>
          <td>${row.scenario}</td>
          <td>${formatPct(row.annualized_return)}</td>
          <td>${formatNum(row.sharpe_ratio)}</td>
          <td>${formatPct(row.max_drawdown)}</td>
          <td>${formatPct(row.alpha_annualized)}</td>
          <td>${formatNum(row.average_turnover)}</td>
          <td>${row.research_readiness ? formatNum(row.research_readiness) : "-"}</td>
          <td><code>${row.fingerprint || "-"}</code></td>
        </tr>
      `
    )
    .join("");
  document.getElementById("comparison-table").innerHTML = `${header}${body}</tbody></table>`;
}

async function loadOverview() {
  const [system, scenarios, datasets, workspaces, overview, runs, platform] = await Promise.all([
    getJson("/api/system"),
    getJson("/api/scenarios"),
    getJson("/api/public-datasets"),
    getJson("/api/workspaces"),
    getJson("/api/overview"),
    getJson("/api/runs"),
    getJson("/api/platform"),
  ]);

  state.scenarios = scenarios;
  state.datasets = datasets;
  state.workspaces = workspaces;
  state.runs = runs;
  state.platform = platform;

  renderSystemCard(system);
  renderScenarioOptions();
  renderDatasets();
  renderWorkspaces();
  renderResources(overview.public_resources);
  renderPlatform(platform);
  renderRuns();

  if (runs.length) {
    renderRunDetail(runs[0]);
  }
}

document.getElementById("run-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = {
    scenario_id: document.getElementById("scenario-select").value,
    workspace_id: document.getElementById("workspace-select").value,
    dataset_id: document.getElementById("dataset-select").value,
    label: document.getElementById("label-input").value || null,
    seed: Number(document.getElementById("seed-input").value),
  };
  await getJson("/api/runs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  await loadOverview();
});

document.getElementById("workspace-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  await getJson("/api/workspaces", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name: document.getElementById("workspace-name").value,
      description: document.getElementById("workspace-description").value,
    }),
  });
  document.getElementById("workspace-form").reset();
  await loadOverview();
});

document.getElementById("refresh-button").addEventListener("click", loadOverview);

document.getElementById("run-list").addEventListener("click", async (event) => {
  const detailButton = event.target.closest("[data-run-detail]");
  if (detailButton) {
    const run = await getJson(`/api/runs/${detailButton.dataset.runDetail}`);
    renderRunDetail(run);
  }

  const replayButton = event.target.closest("[data-run-replay]");
  if (replayButton) {
    await getJson(`/api/runs/${replayButton.dataset.runReplay}/replay`, { method: "POST" });
    await loadOverview();
  }
});

document.getElementById("compare-button").addEventListener("click", async () => {
  const runIds = [...document.querySelectorAll(".compare-check:checked")].map((input) => input.value);
  if (runIds.length < 2) {
    renderComparison([]);
    return;
  }
  const response = await getJson("/api/compare", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ run_ids: runIds }),
  });
  renderComparison(response.rows);
});

loadOverview().catch((error) => {
  document.getElementById("run-detail").textContent = error.message;
});
