"use strict";

// ===== Constants =====
const ALL_METRICS = [
  "GetGroupsAvgTime", "ThreadsBlocked", "ThreadsWaiting", "ThreadsTimedWaiting",
  "GcTimeMillisParNew", "GcTimeMillisConcurrentMarkSweep", "CallQueueLength",
  "RpcProcessingTimeAvgTime", "RpcQueueTimeAvgTime",
  "CreateAvgTime", "MkdirsAvgTime", "DeleteAvgTime", "RenameAvgTime",
  "Rename2AvgTime", "CompleteAvgTime", "GetFileInfoAvgTime", "GetBlockLocationsAvgTime",
  "GetListingAvgTime", "GetContentSummaryAvgTime", "FsyncAvgTime", "ConcatAvgTime",
  "CreateSnapshotAvgTime", "DeleteSnapshotAvgTime", "RenameSnapshotAvgTime",
  "GetSnapshotDiffReportAvgTime", "GetSnapshotDiffReportListingAvgTime",
  "GetDatanodeReportAvgTime", "GetDatanodeStorageReportAvgTime",
];
const DEFAULT_METRICS = ["RpcProcessingTimeAvgTime", "RpcQueueTimeAvgTime", "ThreadsBlocked"];

// ===== DOM refs =====
const baselineFromInput = document.getElementById("baseline-from");
const baselineToInput   = document.getElementById("baseline-to");
const btnTrain          = document.getElementById("btn-train");
const trainStatus       = document.getElementById("train-status");
const trainResult       = document.getElementById("train-result");
const baselineBadge     = document.getElementById("baseline-trained-badge");

const analysisFromInput   = document.getElementById("analysis-from");
const analysisToInput     = document.getElementById("analysis-to");
const thresholdInput      = document.getElementById("threshold-override");
const modelThresholdHint  = document.getElementById("model-threshold-hint");
const btnGenerate         = document.getElementById("btn-generate");
const statusBar           = document.getElementById("status-bar");

const modelBadge        = document.getElementById("model-badge");
const summarySection    = document.getElementById("summary-section");
const reconSection      = document.getElementById("recon-section");
const metricsSection    = document.getElementById("metrics-section");
const anomalySection    = document.getElementById("anomaly-section");
const reconImg          = document.getElementById("recon-img");
const metricsImg        = document.getElementById("metrics-img");
const anomalyTbody      = document.getElementById("anomaly-tbody");
const noAnomalies       = document.getElementById("no-anomalies");
const anomalyBadge      = document.getElementById("anomaly-badge");
const metricCheckboxes  = document.getElementById("metric-checkboxes");
const btnRegenChart     = document.getElementById("btn-regen-chart");

const stepIndicators = [
  document.getElementById("step-indicator-1"),
  document.getElementById("step-indicator-2"),
  document.getElementById("step-indicator-3"),
];

// ===== Init =====
(function init() {
  buildMetricCheckboxes();
  fetchModelStatus();
  setDefaultWindows();

  btnTrain.addEventListener("click", trainOnBaseline);
  btnGenerate.addEventListener("click", analyzeWindow);
  btnRegenChart.addEventListener("click", regenMetricsChart);

  document.querySelectorAll(".baseline-preset").forEach(btn => {
    btn.addEventListener("click", () => applyPreset(btn, baselineFromInput, baselineToInput));
  });
  document.querySelectorAll(".analysis-preset").forEach(btn => {
    btn.addEventListener("click", () => applyPreset(btn, analysisFromInput, analysisToInput));
  });
})();

// ===== Helpers =====
function toLocalInputValue(date) {
  const p = n => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${p(date.getMonth()+1)}-${p(date.getDate())}T${p(date.getHours())}:${p(date.getMinutes())}`;
}

function localInputToISO(value) {
  // datetime-local input gives "YYYY-MM-DDTHH:MM" already in the user's local time.
  // The DB also stores naive local timestamps (no timezone).
  // Do NOT convert to UTC — return the string as-is with seconds appended.
  return value.length === 16 ? value + ":00" : value;
}

function applyPreset(btn, fromInput, toInput) {
  const minutes = parseInt(btn.dataset.minutes, 10);
  const now = new Date();
  fromInput.value = toLocalInputValue(new Date(now.getTime() - minutes * 60 * 1000));
  toInput.value   = toLocalInputValue(now);
}

function setDefaultWindows() {
  const now = new Date();
  // Default baseline: 2–4 hours ago (a recent "good" window)
  baselineFromInput.value = toLocalInputValue(new Date(now.getTime() - 4 * 60 * 60 * 1000));
  baselineToInput.value   = toLocalInputValue(new Date(now.getTime() - 2 * 60 * 60 * 1000));
  // Default analysis: last hour (most recent data)
  analysisFromInput.value = toLocalInputValue(new Date(now.getTime() - 60 * 60 * 1000));
  analysisToInput.value   = toLocalInputValue(now);
}

function setStep(n) {
  stepIndicators.forEach((el, i) => {
    el.classList.remove("active", "done");
    if (i + 1 < n) el.classList.add("done");
    else if (i + 1 === n) el.classList.add("active");
  });
}

function showTrainStatus(msg, type = "info") {
  trainStatus.className = "status-bar" + (type === "info" ? "" : ` ${type}`);
  const spin = type === "info" ? `<div class="spinner"></div>` : "";
  trainStatus.innerHTML = `${spin}<span>${msg}</span>`;
  trainStatus.classList.remove("hidden");
}
function hideTrainStatus() { trainStatus.classList.add("hidden"); }

function showStatus(msg, type = "info") {
  statusBar.className = "status-bar" + (type === "info" ? "" : ` ${type}`);
  const spin = type === "info" ? `<div class="spinner"></div>` : "";
  statusBar.innerHTML = `${spin}<span>${msg}</span>`;
  statusBar.classList.remove("hidden");
}
function hideStatus() { statusBar.classList.add("hidden"); }

// ===== Model Status =====
async function fetchModelStatus() {
  try {
    const res = await fetch("/api/model/status");
    const data = await res.json();
    if (data.status === "active") {
      const date = new Date(data.trained_at).toLocaleString();
      let text = `Model active · trained ${date} · threshold ${data.threshold.toFixed(4)}`;
      if (data.baseline_from) {
        text += ` · baseline ${data.baseline_from.slice(0,16)} → ${(data.baseline_to||"").slice(0,16)}`;
      }
      modelBadge.textContent = text;
      modelBadge.className = "model-badge active";
      if (modelThresholdHint) {
        modelThresholdHint.textContent = `(model default: ${data.threshold.toFixed(6)})`;
      }
      // Show that a model already exists
      baselineBadge.classList.remove("hidden");
      setStep(2);
    } else {
      modelBadge.textContent = "No trained model — complete Step 1 first";
      modelBadge.className = "model-badge error";
      setStep(1);
    }
  } catch {
    modelBadge.textContent = "Could not reach API";
    modelBadge.className = "model-badge error";
  }
}

// ===== Metric Checkboxes =====
function buildMetricCheckboxes() {
  metricCheckboxes.innerHTML = "";
  ALL_METRICS.forEach(m => {
    const label = document.createElement("label");
    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.value = m;
    cb.checked = DEFAULT_METRICS.includes(m);
    label.appendChild(cb);
    label.appendChild(document.createTextNode(" " + m));
    metricCheckboxes.appendChild(label);
  });
}

function getSelectedMetrics() {
  return [...metricCheckboxes.querySelectorAll("input:checked")].map(cb => cb.value);
}

// ===== Step 1: Train on Baseline =====
async function trainOnBaseline() {
  if (!baselineFromInput.value || !baselineToInput.value) {
    showTrainStatus("Please select both From and To for the baseline window.", "error");
    return;
  }

  const from_ts = localInputToISO(baselineFromInput.value);
  const to_ts   = localInputToISO(baselineToInput.value);

  btnTrain.disabled = true;
  trainResult.classList.add("hidden");
  baselineBadge.classList.add("hidden");
  setStep(1);
  showTrainStatus("Training model on baseline window… this may take 1–3 minutes.", "info");

  try {
    const res = await fetch("/api/model/train", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ from_ts, to_ts }),
    });
    const data = await res.json();

    if (!res.ok) {
      showTrainStatus(`Training failed: ${data.detail || JSON.stringify(data)}`, "error");
      return;
    }

    hideTrainStatus();
    showTrainResult(data, from_ts, to_ts);
    baselineBadge.classList.remove("hidden");
    setStep(2);
    fetchModelStatus();

  } catch (err) {
    showTrainStatus(`Network error: ${err.message}`, "error");
  } finally {
    btnTrain.disabled = false;
  }
}

function showTrainResult(data, from_ts, to_ts) {
  document.getElementById("tr-rows").textContent      = (data.rows_trained_on || "—").toLocaleString();
  document.getElementById("tr-epochs").textContent    = data.epochs_run ?? "—";
  document.getElementById("tr-threshold").textContent = data.threshold != null ? data.threshold.toFixed(6) : "—";
  document.getElementById("tr-window").textContent    = `${from_ts.replace("T"," ")} → ${to_ts.replace("T"," ")}`;
  trainResult.classList.remove("hidden");
  // Update the threshold hint in Step 2 so the user knows the new default
  if (modelThresholdHint && data.threshold != null) {
    modelThresholdHint.textContent = `(model default: ${data.threshold.toFixed(6)})`;
  }
}

// ===== Step 2: Analyze Window =====
async function analyzeWindow() {
  if (!analysisFromInput.value || !analysisToInput.value) {
    showStatus("Please select both From and To for the analysis window.", "error");
    return;
  }

  const from_ts = localInputToISO(analysisFromInput.value);
  const to_ts   = localInputToISO(analysisToInput.value);

  btnGenerate.disabled = true;
  setStep(2);
  showStatus("Scoring analysis window against baseline model…", "info");
  hideSection(summarySection, reconSection, metricsSection, anomalySection);

  const overrideVal = thresholdInput.value.trim();
  const threshold_override = overrideVal !== "" ? parseFloat(overrideVal) : null;

  try {
    const res = await fetch("/api/report", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ from_ts, to_ts, key_metrics: getSelectedMetrics(), threshold_override }),
    });
    const data = await res.json();

    if (!res.ok) {
      showStatus(`Error ${res.status}: ${data.detail || JSON.stringify(data)}`, "error");
      return;
    }

    renderReport(data, from_ts, to_ts);
    hideStatus();
    setStep(3);

  } catch (err) {
    showStatus(`Network error: ${err.message}`, "error");
  } finally {
    btnGenerate.disabled = false;
  }
}

// ===== Re-generate metrics chart =====
async function regenMetricsChart() {
  if (!analysisFromInput.value || !analysisToInput.value) return;
  const from_ts = localInputToISO(analysisFromInput.value);
  const to_ts   = localInputToISO(analysisToInput.value);
  btnRegenChart.disabled = true;
  const overrideVal2 = thresholdInput.value.trim();
  const threshold_override2 = overrideVal2 !== "" ? parseFloat(overrideVal2) : null;
  try {
    const res = await fetch("/api/report", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ from_ts, to_ts, key_metrics: getSelectedMetrics(), threshold_override: threshold_override2 }),
    });
    const data = await res.json();
    if (res.ok && data.metrics_chart) {
      metricsImg.src = "data:image/png;base64," + data.metrics_chart;
    }
  } finally {
    btnRegenChart.disabled = false;
  }
}

// ===== Render Full Report =====
function renderReport(data, from_ts, to_ts) {
  document.getElementById("val-total").textContent     = data.total_scored.toLocaleString();
  document.getElementById("val-anomalies").textContent = data.anomaly_count.toLocaleString();

  const usedThreshold = data.threshold;
  const modelThreshold = data.model_threshold;
  let threshText = usedThreshold != null ? usedThreshold.toFixed(6) : "—";
  if (modelThreshold != null && Math.abs(usedThreshold - modelThreshold) > 1e-9) {
    threshText += ` (override; model default: ${modelThreshold.toFixed(6)})`;
  }
  document.getElementById("val-threshold").textContent = threshText;

  document.getElementById("val-window").textContent =
    `${from_ts.replace("T"," ")} → ${to_ts.replace("T"," ")}`;
  showSection(summarySection);

  if (data.reconstruction_error_chart) {
    reconImg.src = "data:image/png;base64," + data.reconstruction_error_chart;
    showSection(reconSection);
  }
  if (data.metrics_chart) {
    metricsImg.src = "data:image/png;base64," + data.metrics_chart;
    showSection(metricsSection);
  }

  renderAnomalyTable(data.anomalies || []);
  showSection(anomalySection);
}

// ===== Anomaly Table =====
function renderAnomalyTable(anomalies) {
  anomalyTbody.innerHTML = "";
  anomalyBadge.textContent = anomalies.length;

  if (anomalies.length === 0) {
    noAnomalies.classList.remove("hidden");
    return;
  }
  noAnomalies.classList.add("hidden");

  anomalies.forEach((a, idx) => {
    const metrics = (a.explanation || {}).metrics || [];
    const top = metrics[0] || null;

    const tr = document.createElement("tr");
    tr.className = "anomaly-row";
    tr.innerHTML = `
      <td>${idx + 1}</td>
      <td>${a.timestamp.replace("T", " ")}</td>
      <td>${a.reconstruction_error.toFixed(6)}</td>
      <td>${top ? `<span class="metric-name">${top.metric}</span>` : "—"}</td>
      <td>${top ? `<span class="impact-score">${top.impact_score.toFixed(4)}</span>` : "—"}</td>
    `;

    const expandTr = document.createElement("tr");
    expandTr.className = "expand-row hidden";
    const expandTd = document.createElement("td");
    expandTd.colSpan = 5;
    const content = document.createElement("div");
    content.className = "expand-content";
    content.innerHTML = buildExplanationHTML(a.explanation || {});
    expandTd.appendChild(content);
    expandTr.appendChild(expandTd);

    tr.addEventListener("click", () => expandTr.classList.toggle("hidden"));

    anomalyTbody.appendChild(tr);
    anomalyTbody.appendChild(expandTr);
  });
}

function buildExplanationHTML(explanation) {
  const metrics = explanation.metrics || [];
  if (!metrics.length) {
    return `<p class="metric-desc">${explanation.summary || "No explanation available."}</p>`;
  }
  let html = `<h3>${explanation.summary || "Anomaly explanation"}</h3>`;
  metrics.forEach(m => {
    const causes = (m.possible_causes || []).map(c => `<li>${c}</li>`).join("");
    const val = typeof m.actual_value === "number" ? m.actual_value.toFixed(2) : m.actual_value;
    html += `
      <div class="metric-entry">
        <div class="metric-name">${m.metric}</div>
        <div class="metric-meta">
          <span>Actual: <strong>${val}</strong></span>
          <span>Impact: <span class="impact-score">${m.impact_score.toFixed(4)}</span></span>
        </div>
        ${m.description ? `<div class="metric-desc">${m.description}</div>` : ""}
        ${m.high_impact ? `<div class="metric-impact">⚠ ${m.high_impact}</div>` : ""}
        ${causes ? `<div class="metric-causes"><strong>Possible causes:</strong><ul>${causes}</ul></div>` : ""}
      </div>`;
  });
  return html;
}

// ===== Section Visibility Helpers =====
function showSection(...els) { els.forEach(el => el.classList.remove("hidden")); }
function hideSection(...els) { els.forEach(el => el.classList.add("hidden")); }
