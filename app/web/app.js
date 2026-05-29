const state = {
  cases: [],
  reviewCases: [],
  audit: [],
  samples: [],
  selectedCaseId: null,
  selectedReviewId: null,
  view: "inbox",
};

const $ = (id) => document.getElementById(id);

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Request failed");
  return data;
}

function severityClass(severity) {
  return ["critical", "high", "medium", "low"].includes(severity) ? severity : "";
}

function truncate(text, max = 120) {
  if (!text) return "";
  return text.length > max ? `${text.slice(0, max)}...` : text;
}

function riskBadge(c) {
  return `<span class="badge ${severityClass(c.severity)}">${c.severity} · ${c.risk_score}</span>`;
}

function renderCaseCard(c, activeId) {
  const labels = (c.risk_labels || []).slice(0, 2).map((l) => `<span class="badge">${l}</span>`).join("");
  return `
    <article class="case-card ${c.id === activeId ? "active" : ""}" data-case-id="${c.id}">
      <h4>${c.title}</h4>
      <p>${truncate(c.message)}</p>
      <div class="badges">
        ${riskBadge(c)}
        <span class="badge">${c.category}</span>
        ${labels}
      </div>
    </article>
  `;
}

function detailHtml(c, mode = "inbox") {
  if (!c) return `<div class="empty-state">Select a case.</div>`;
  const labels = (c.risk_labels || []).map((l) => `<span class="badge">${l}</span>`).join("");
  const reviewForm = mode === "review" ? reviewFormHtml(c) : "";
  return `
    <div class="detail-header">
      <div>
        <h3>${c.title}</h3>
        <p class="muted">${c.template_type} · ${c.source_type} · ${c.status}</p>
      </div>
      ${riskBadge(c)}
    </div>
    <div class="detail-grid">
      <div class="kv"><strong>Customer</strong>${c.customer_name || "Unknown"}</div>
      <div class="kv"><strong>Order / Source</strong>${c.order_id || c.source_id || "None"}</div>
      <div class="kv"><strong>Suggested owner</strong>${c.suggested_owner}</div>
      <div class="kv"><strong>Suggested action</strong>${c.suggested_action}</div>
    </div>
    <h3>Original Signal</h3>
    <div class="message-box">${c.message}</div>
    <h3>AI Reasoning</h3>
    <div class="ai-box">
      <p><strong>Category:</strong> ${c.category}</p>
      <p><strong>Sentiment:</strong> ${c.sentiment}</p>
      <p><strong>Confidence:</strong> ${Math.round((c.confidence_score || 0) * 100)}%</p>
      <p><strong>Policy basis:</strong> ${c.policy_basis}</p>
      <p><strong>Reason:</strong> ${c.reason}</p>
      <div class="badges">${labels}</div>
    </div>
    <h3>Reply Draft</h3>
    <div class="message-box">${c.reply_draft || "No reply draft generated."}</div>
    ${reviewForm}
  `;
}

function reviewFormHtml(c) {
  return `
    <h3>Human Review</h3>
    <form class="review-form" id="reviewForm">
      <input type="hidden" name="case_id" value="${c.id}" />
      <input type="hidden" name="analysis_id" value="${c.analysis_id}" />
      <label>Category<input name="corrected_category" value="${c.category}" /></label>
      <label>Severity
        <select name="corrected_severity">
          ${["low", "medium", "high", "critical"].map((s) => `<option value="${s}" ${s === c.severity ? "selected" : ""}>${s}</option>`).join("")}
        </select>
      </label>
      <label>Risk score<input name="corrected_risk_score" type="number" min="0" max="100" value="${c.risk_score}" /></label>
      <label>Owner<input name="corrected_owner" value="${c.suggested_owner}" /></label>
      <label class="full">Action
        <select name="corrected_action">
          ${["reply_draft", "refund_review", "create_issue", "slack_escalation", "assign_owner"].map((a) => `<option value="${a}" ${a === c.suggested_action ? "selected" : ""}>${a}</option>`).join("")}
        </select>
      </label>
      <label class="full">Reply draft<textarea name="corrected_reply">${c.reply_draft || ""}</textarea></label>
      <label class="full">Correction reason<textarea name="correction_reason" placeholder="What did the AI miss or get right?"></textarea></label>
      <label class="full"><input name="add_to_eval_dataset" type="checkbox" /> Add this correction to eval dataset</label>
      <div class="actions">
        <button class="danger" type="button" data-decision="reject">Reject</button>
        <button class="primary" type="button" data-decision="approve">Approve</button>
      </div>
    </form>
  `;
}

function renderCases() {
  const search = $("caseSearch").value.toLowerCase();
  const risk = $("riskFilter").value;
  const filtered = state.cases.filter((c) => {
    const blob = `${c.title} ${c.message} ${c.customer_name} ${c.category} ${(c.risk_labels || []).join(" ")}`.toLowerCase();
    return (!search || blob.includes(search)) && (!risk || c.severity === risk);
  });
  $("caseList").innerHTML = filtered.map((c) => renderCaseCard(c, state.selectedCaseId)).join("") || `<div class="empty-state">No cases yet.</div>`;
  const selected = state.cases.find((c) => c.id === state.selectedCaseId) || filtered[0];
  if (selected) state.selectedCaseId = selected.id;
  $("caseDetail").innerHTML = selected ? detailHtml(selected) : `<div class="empty-state">Import a CSV or select a case.</div>`;
}

function renderReviewQueue() {
  $("reviewList").innerHTML = state.reviewCases.map((c) => renderCaseCard(c, state.selectedReviewId)).join("") || `<div class="empty-state">No cases need review.</div>`;
  const selected = state.reviewCases.find((c) => c.id === state.selectedReviewId) || state.reviewCases[0];
  if (selected) state.selectedReviewId = selected.id;
  $("reviewDetail").innerHTML = selected ? detailHtml(selected, "review") : `<div class="empty-state">No pending review items.</div>`;
}

function renderInsights() {
  const groups = new Map();
  for (const c of state.cases) groups.set(c.category, (groups.get(c.category) || 0) + 1);
  const sorted = [...groups.entries()].sort((a, b) => b[1] - a[1]);
  $("clusterList").innerHTML = sorted.map(([name, count]) => `
    <div class="kv"><strong>${name}</strong>${count} case${count === 1 ? "" : "s"}</div>
  `).join("") || `<p class="muted">Import cases to see clusters.</p>`;

  const highRisk = state.cases.filter((c) => c.risk_score >= 60);
  $("rootCauses").innerHTML = highRisk.slice(0, 5).map((c) => `
    <div class="kv"><strong>${c.category}</strong>${c.reason}</div>
  `).join("") || `<p class="muted">No high-risk patterns yet.</p>`;

  const report = [
    "SellerOps Weekly Report",
    "",
    `Total cases: ${state.cases.length}`,
    `Cases needing review: ${state.reviewCases.length}`,
    `Average risk score: ${averageRisk()}`,
    "",
    "Top clusters:",
    ...sorted.map(([name, count]) => `- ${name}: ${count}`),
    "",
    "Recommended focus:",
    ...highRisk.slice(0, 3).map((c) => `- ${c.title}: ${c.suggested_action} (${c.risk_score})`),
  ].join("\n");
  $("weeklyReport").value = report;
}

function renderAudit() {
  $("auditList").innerHTML = state.audit.map((log) => `
    <article class="audit-item">
      <strong>${log.action_type}</strong> · ${log.status}
      <p>${log.title}</p>
      <p class="muted">${log.executed_by} · ${log.executed_at}</p>
    </article>
  `).join("") || `<div class="empty-state">No review actions yet.</div>`;
}

function averageRisk() {
  if (!state.cases.length) return 0;
  return Math.round(state.cases.reduce((sum, c) => sum + c.risk_score, 0) / state.cases.length);
}

function updateMetrics() {
  $("caseCount").textContent = state.cases.length;
  $("reviewCount").textContent = state.reviewCases.length;
  $("avgRisk").textContent = averageRisk();
}

function renderAll() {
  updateMetrics();
  renderCases();
  renderReviewQueue();
  renderInsights();
  renderAudit();
}

async function refresh() {
  const [cases, review, audit] = await Promise.all([
    api("/api/cases"),
    api("/api/review-queue"),
    api("/api/audit"),
  ]);
  state.cases = cases.cases;
  state.reviewCases = review.cases;
  state.audit = audit.logs;
  renderAll();
}

async function loadSamples() {
  const data = await api("/api/samples");
  state.samples = data.samples;
  $("sampleSelect").innerHTML = `<option value="">Choose a sample...</option>` + state.samples.map((s, i) => `<option value="${i}">${s.path}</option>`).join("");
}

async function importCsv() {
  const csvText = $("csvText").value;
  if (!csvText.trim()) {
    $("importStatus").textContent = "Paste or load a CSV first.";
    return;
  }
  $("importStatus").textContent = "Importing...";
  const result = await api("/api/import/csv", {
    method: "POST",
    body: JSON.stringify({
      template_type: $("templateType").value,
      source_type: "csv",
      csv_text: csvText,
    }),
  });
  $("importStatus").textContent = `Imported ${result.imported} case(s).`;
  await refresh();
}

async function submitReview(decision) {
  const form = $("reviewForm");
  if (!form) return;
  const data = Object.fromEntries(new FormData(form).entries());
  data.case_id = Number(data.case_id);
  data.analysis_id = Number(data.analysis_id);
  data.corrected_risk_score = Number(data.corrected_risk_score);
  data.corrected_risk_labels = [];
  data.add_to_eval_dataset = Boolean(form.elements.add_to_eval_dataset.checked);
  data.decision = decision;
  await api("/api/reviews", { method: "POST", body: JSON.stringify(data) });
  state.selectedReviewId = null;
  await refresh();
}

function setView(view) {
  state.view = view;
  document.querySelectorAll(".nav-item").forEach((b) => b.classList.toggle("active", b.dataset.view === view));
  document.querySelectorAll(".view").forEach((v) => v.classList.remove("active"));
  $(`${view}View`).classList.add("active");
  $("viewTitle").textContent = {
    inbox: "Inbox",
    review: "Review Queue",
    insights: "Insights",
    audit: "Audit Log",
  }[view];
}

document.addEventListener("click", async (event) => {
  const nav = event.target.closest(".nav-item");
  if (nav) setView(nav.dataset.view);

  const card = event.target.closest(".case-card");
  if (card) {
    const id = Number(card.dataset.caseId);
    if (state.view === "review") state.selectedReviewId = id;
    else state.selectedCaseId = id;
    renderAll();
  }

  const reviewButton = event.target.closest("[data-decision]");
  if (reviewButton) await submitReview(reviewButton.dataset.decision);
});

$("caseSearch").addEventListener("input", renderCases);
$("riskFilter").addEventListener("change", renderCases);
$("importCsv").addEventListener("click", importCsv);
$("sampleSelect").addEventListener("change", (event) => {
  const sample = state.samples[Number(event.target.value)];
  if (!sample) return;
  $("csvText").value = sample.text;
  $("templateType").value = sample.path.includes("saas") ? "saas_support" : "seller_support";
});

loadSamples().then(refresh).catch((error) => {
  console.error(error);
  $("importStatus").textContent = error.message;
});
