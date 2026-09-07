const apiRoot = "/api/v1";

const state = {
  session: null,
  overview: null,
  projects: [],
  view: "overview",
  project: null,
  projectTab: "summary",
  projectResults: [],
  jobs: [],
  evidence: [],
  audit: [],
  report: null,
  reviewQueue: [],
  query: "",
  status: "ALL",
  resultPriority: "ALL",
};

const workspace = document.querySelector("#workspace");
const mutatingMethods = new Set(["POST", "PATCH", "DELETE"]);

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function humanize(value) {
  return String(value ?? "—").replaceAll("_", " ").toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatDate(value) {
  if (!value) return "Not yet";
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

async function api(path, options = {}) {
  const method = options.method || "GET";
  const headers = { Accept: "application/json", ...(options.headers || {}) };
  if (options.body) headers["Content-Type"] = "application/json";
  if (mutatingMethods.has(method)) headers["X-ArchaeoAI-Demo"] = "1";
  const response = await fetch(`${apiRoot}${path}`, { ...options, method, headers });
  if (!response.ok) {
    let error = { error: "REQUEST_FAILED" };
    try { error = await response.json(); } catch { /* controlled fallback */ }
    throw new Error(error.error || "REQUEST_FAILED");
  }
  return response.status === 204 ? null : response.json();
}

function toast(message, isError = false) {
  const element = document.querySelector("#toast");
  element.textContent = message;
  element.classList.toggle("error", isError);
  element.hidden = false;
  window.clearTimeout(toast.timeout);
  toast.timeout = window.setTimeout(() => { element.hidden = true; }, 3600);
}

function statusBadge(status) {
  return `<span class="status-badge status-${escapeHtml(String(status).toLowerCase())}">${escapeHtml(humanize(status))}</span>`;
}

function approvedRuntimeAvailable() {
  return state.session?.runtime_status?.model_execution_available === true;
}

function applyRuntimeChrome() {
  const approved = approvedRuntimeAvailable();
  const badge = approved ? "REAL FROZEN MODEL · SYNTHETIC TERRAIN · LOCAL PRIVATE" : "SYNTHETIC DEMO · MODEL NOT EXECUTED";
  const copy = approved ? "E001 frozen Random Forest verified; real terrain, coordinates, and remote access remain disabled." : "No production authentication, real terrain, coordinates, or archaeological determination.";
  document.querySelector("#entry-runtime-badge").textContent = badge;
  document.querySelector("#entry-runtime-copy").textContent = copy;
  document.querySelector("#runtime-chip").textContent = badge;
  document.querySelector("#sidebar-runtime-title").textContent = approved ? "Approved runtime ready" : "Demo runtime ready";
  document.querySelector("#sidebar-runtime-copy").textContent = approved ? "Real model · synthetic input only" : "Approved model disabled";
}

function emptyState(title, copy, action = "") {
  return `<section class="empty-state"><div class="empty-icon" aria-hidden="true">◇</div><h3>${escapeHtml(title)}</h3><p>${escapeHtml(copy)}</p>${action}</section>`;
}

function setNavigation(view) {
  document.querySelectorAll(".nav-item").forEach((item) => item.classList.toggle("active", item.dataset.view === view));
  document.querySelector(".sidebar").classList.remove("open");
}

async function refreshBase() {
  [state.overview, state.projects, state.reviewQueue] = await Promise.all([
    api("/overview"), api("/projects"), api("/review-queue"),
  ]);
}

async function openProject(projectId, tab = "summary") {
  state.project = await api(`/projects/${encodeURIComponent(projectId)}`);
  state.projectTab = tab;
  [state.projectResults, state.jobs, state.evidence, state.audit, state.report] = await Promise.all([
    api(`/projects/${projectId}/results`),
    api(`/projects/${projectId}/jobs`),
    api(`/projects/${projectId}/evidence`),
    api(`/projects/${projectId}/audit`),
    api(`/projects/${projectId}/report`),
  ]);
  state.view = "project";
  setNavigation("");
  render();
}

function projectRow(project) {
  return `<tr>
    <td><button class="text-link" data-open-project="${escapeHtml(project.id)}"><strong>${escapeHtml(project.name)}</strong><small>${escapeHtml(project.project_reference)}</small></button></td>
    <td>${statusBadge(project.status)}</td>
    <td>${escapeHtml(humanize(project.review_status))}</td>
    <td>${escapeHtml(humanize(project.retention_policy))}</td>
    <td>${escapeHtml(formatDate(project.updated_at))}</td>
  </tr>`;
}

function overviewView() {
  const o = state.overview;
  const approved = approvedRuntimeAvailable();
  return `<header class="page-heading"><div><p class="eyebrow">Workspace overview</p><h1>Good evidence starts with a controlled workflow.</h1><p>Manage bounded synthetic demonstrations while preserving the boundary between machine hypotheses and human interpretation.</p></div><button class="primary-action" data-new-project>New project</button></header>
  <section class="metric-grid">
    <article class="metric-card"><span>Active projects</span><strong>${o.active_projects}</strong><small>Local demonstration workspace</small></article>
    <article class="metric-card"><span>Awaiting review</span><strong>${o.awaiting_review}</strong><small>Human attention required</small></article>
    <article class="metric-card"><span>Reports ready</span><strong>${o.reports_ready}</strong><small>Coordinate-safe summaries</small></article>
    <article class="metric-card guarded"><span>Approved model</span><strong>${approved ? "Ready" : "Disabled"}</strong><small>${approved ? "Verified · local synthetic input only" : "No artifact loaded or executed"}</small></article>
  </section>
  <div class="two-column">
    <section class="panel"><div class="panel-heading"><div><p class="eyebrow">Recent work</p><h2>Projects</h2></div><button class="text-button" data-view-target="projects">View all</button></div>
      ${o.recent_projects.length ? `<div class="table-wrap"><table><thead><tr><th>Project</th><th>Status</th><th>Review</th><th>Retention</th><th>Updated</th></tr></thead><tbody>${o.recent_projects.map(projectRow).join("")}</tbody></table></div>` : emptyState("No projects", "Create a synthetic demonstration project to begin.")}
    </section>
    <aside class="panel workflow-panel"><p class="eyebrow">Evidence-led workflow</p><h2>Designed for accountable screening</h2>
      <ol class="workflow-list"><li><span>1</span><div><strong>Authorize</strong><small>Record scope and synthetic-data attestation.</small></div></li><li><span>2</span><div><strong>Screen</strong><small>Run canonical feature preparation on mathematical terrain.</small></div></li><li><span>3</span><div><strong>Review</strong><small>Record separately attributed human observations.</small></div></li><li><span>4</span><div><strong>Report</strong><small>Generate a limitations-first, coordinate-safe summary.</small></div></li></ol>
    </aside>
  </div>
  <section class="boundary-banner"><div><strong>Demonstration boundary</strong><p>${approved ? "The frozen E001 model may score synthetic mathematical terrain. Scores are terrain-pattern similarity—not archaeological probabilities." : "Scores are deterministic interface values—not archaeological probabilities. No real terrain or approved private model is used."}</p></div><span>${approved ? "MODEL AVAILABLE · SYNTHETIC ONLY" : "MODEL EXECUTION: NOT PERFORMED"}</span></section>`;
}

function projectsView() {
  const query = state.query.toLowerCase();
  const projects = state.projects.filter((project) => {
    const matchesText = `${project.name} ${project.project_reference}`.toLowerCase().includes(query);
    return matchesText && (state.status === "ALL" || project.status === state.status);
  });
  return `<header class="page-heading compact"><div><p class="eyebrow">Portfolio</p><h1>Projects</h1><p>Project-scoped synthetic screening records and review state.</p></div><button class="primary-action" data-new-project>New project</button></header>
  <section class="panel"><div class="toolbar"><label class="search-field"><span class="sr-only">Search projects</span><input id="project-search" type="search" placeholder="Search name or reference" value="${escapeHtml(state.query)}"></label><label><span class="sr-only">Filter by status</span><select id="project-status"><option value="ALL">All statuses</option>${["DRAFT","AUTHORIZED_FOR_DEMO","REVIEW_REQUIRED","REVIEWED","REPORT_READY"].map((s) => `<option value="${s}" ${state.status === s ? "selected" : ""}>${humanize(s)}</option>`).join("")}</select></label><span>${projects.length} shown</span></div>
  ${projects.length ? `<div class="table-wrap"><table><thead><tr><th>Project</th><th>Status</th><th>Review</th><th>Retention</th><th>Updated</th></tr></thead><tbody>${projects.map(projectRow).join("")}</tbody></table></div>` : emptyState("No matching projects", "Adjust the search or status filter.")}</section>`;
}

function terrainThumb(result) {
  const style = ["mound", "ridge", "hollow", "wave"][Number.parseInt(result.thumbnail_id.slice(-1), 16) % 4];
  return `<div class="terrain-thumb ${style}" role="img" aria-label="Abstract mathematical terrain thumbnail"><i></i><i></i><i></i></div>`;
}

function resultCard(result) {
  const realModel = result.model_execution === "PERFORMED_APPROVED_PRIVATE_MODEL";
  return `<article class="result-card">
    ${terrainThumb(result)}
    <div class="result-body"><div class="result-top"><span class="priority priority-${escapeHtml(result.priority.toLowerCase())}">${escapeHtml(humanize(result.priority))}</span><small>${escapeHtml(result.id)}</small></div>
    <div class="score-row"><strong>${Number(result.score).toFixed(3)}</strong><span>${realModel ? "terrain similarity score" : "demonstration score"}</span></div>
    <p><strong>${escapeHtml(humanize(result.evidence_level))}</strong><br>${escapeHtml(humanize(result.review_state))}</p>
    <p class="result-warning">${realModel ? "Real frozen model on synthetic terrain. AI output; human review required." : "Terrain-similarity hypothesis only. Not archaeology."}</p>
    <div class="result-actions"><button class="quiet-action" data-inspect-result="${escapeHtml(result.id)}">Inspect result</button><button class="secondary-action" data-review-result="${escapeHtml(result.id)}" ${["REVIEWED","ESCALATED"].includes(result.review_state) ? "disabled" : ""}>${result.review_state === "IN_REVIEW" ? "Continue review" : result.review_state === "UNREVIEWED" ? "Review observation" : "Review recorded"}</button></div></div>
  </article>`;
}

function projectTabs() {
  const tabs = ["summary", "processing", "results", "review", "report", "audit", "settings"];
  return `<div class="tab-list" role="tablist">${tabs.map((tab) => `<button role="tab" data-project-tab="${tab}" aria-selected="${state.projectTab === tab}">${humanize(tab)}</button>`).join("")}</div>`;
}

function projectSummary() {
  const p = state.project;
  return `<div class="two-column"><section class="panel"><p class="eyebrow">Project brief</p><h2>${escapeHtml(p.name)}</h2><dl class="detail-grid"><div><dt>Reference</dt><dd>${escapeHtml(p.project_reference)}</dd></div><div><dt>Owner</dt><dd>${escapeHtml(p.owner)}</dd></div><div><dt>Purpose</dt><dd>${escapeHtml(p.purpose)}</dd></div><div><dt>Retention</dt><dd>${escapeHtml(humanize(p.retention_policy))}</dd></div><div><dt>Processing mode</dt><dd>Synthetic mathematical terrain</dd></div><div><dt>Authorization</dt><dd>${escapeHtml(humanize(p.authorization_state))}</dd></div></dl></section>
  <aside class="panel"><p class="eyebrow">Next action</p><h2>${p.status === "DRAFT" ? "Authorize demonstration" : p.status === "AUTHORIZED_FOR_DEMO" ? "Run bounded workflow" : "Continue professional review"}</h2><p>${p.status === "DRAFT" ? "Record the two required synthetic-only acknowledgements before processing." : p.status === "AUTHORIZED_FOR_DEMO" ? "Select a mathematical scenario. Canonical features are prepared and immediately discarded." : "Inspect hypotheses and record human observations separately."}</p>${projectAction(p)}</aside></div>
  <section class="boundary-banner"><div><strong>Scope and interpretation</strong><p>${approvedRuntimeAvailable() ? "The verified private model may execute only on generated mathematical terrain. No coordinates, archaeological probability, or discovery claim is present." : "No real terrain, coordinates, private model, archaeological probability, or discovery claim is present."}</p></div><span>${escapeHtml(humanize(p.status))}</span></section>`;
}

function projectAction(project) {
  if (project.status === "DRAFT") return `<button class="primary-action" data-authorize="${project.id}">Record demo authorization</button>`;
  if (project.status === "AUTHORIZED_FOR_DEMO") return `<div class="inline-form"><select id="scenario"><option value="MOUND_LIKE">Mound-like mathematical surface</option><option value="DEPRESSION_LIKE">Depression-like surface</option><option value="PLANAR">Planar surface</option><option value="SINUSOIDAL">Sinusoidal surface</option><option value="MIXED_MATHEMATICAL">Mixed mathematical terrain</option></select>${approvedRuntimeAvailable() ? '<select id="runtime"><option value="SYNTHETIC_DEMO">Synthetic demonstration scorer</option><option value="APPROVED_PRIVATE_MODEL">Real frozen E001 model</option></select>' : ''}<button class="primary-action" data-run-demo="${project.id}">Run synthetic terrain</button></div>`;
  return `<button class="primary-action" data-project-tab="results">Open screening results</button>`;
}

function processingTab() {
  const job = state.jobs.at(-1);
  return `<section class="panel"><p class="eyebrow">Processing provenance</p><h2>Bounded synthetic pipeline</h2><div class="process-track">${["Authorization","Input validation","Terrain preparation","Representation generation","Screening demonstration","Result contract","Review queue"].map((label) => `<div class="process-step done"><span>✓</span><strong>${label}</strong></div>`).join("")}</div>${job ? `<dl class="detail-grid"><div><dt>Runtime</dt><dd>${escapeHtml(job.runtime)}</dd></div><div><dt>Model execution</dt><dd>${escapeHtml(job.model_execution)}</dd></div><div><dt>Scenario</dt><dd>${escapeHtml(humanize(job.scenario))}</dd></div><div><dt>Completed</dt><dd>${escapeHtml(formatDate(job.completed_at))}</dd></div></dl>` : emptyState("Not processed", "Authorize and run a synthetic scenario first.")}</section>`;
}

function resultsTab() {
  const filtered = state.projectResults.filter((result) => state.resultPriority === "ALL" || result.priority === state.resultPriority);
  return `<section class="panel"><div class="panel-heading"><div><p class="eyebrow">Screening output</p><h2>Terrain-similarity hypotheses</h2></div><label class="compact-filter"><span>Review priority</span><select id="result-priority"><option value="ALL">All priorities</option>${["HIGHER_REVIEW_PRIORITY","STANDARD_REVIEW_PRIORITY","LOWER_REVIEW_PRIORITY"].map((x) => `<option value="${x}" ${state.resultPriority === x ? "selected" : ""}>${humanize(x)}</option>`).join("")}</select></label></div>${state.projectResults.length ? `<div class="result-grid">${filtered.map(resultCard).join("")}</div><p class="result-count">Showing ${filtered.length} of ${state.projectResults.length} synthetic units</p>` : emptyState("No results", "This project has not run the synthetic workflow.")}</section>`;
}

function reviewTab() {
  const pending = state.projectResults.filter((r) => !["REVIEWED", "ESCALATED"].includes(r.review_state));
  return `<section class="panel"><div class="panel-heading"><div><p class="eyebrow">Professional review</p><h2>Human observation queue</h2></div><span>${pending.length} remaining</span></div><p class="callout">Human observations are attributed separately and remain below archaeological interpretation or confirmation.</p>${pending.length ? `<div class="result-grid">${pending.map(resultCard).join("")}</div>` : emptyState("Review queue complete", "All synthetic hypotheses in this project have a recorded human observation.")}</section><section class="panel evidence-panel"><p class="eyebrow">Evidence record</p><h2>Attributed evidence timeline</h2>${timeline(state.evidence, true)}</section>`;
}

function reportTab() {
  const r = state.report;
  if (r.status !== "READY") return `<section class="panel">${emptyState("Report not generated", "Generate a coordinate-safe, limitations-first demonstration report.", `<button class="primary-action" data-generate-report>Generate report</button>`)}</section>`;
  return `<article class="report-sheet"><div class="report-kicker">ArchaeoAI · Synthetic demonstration report</div><h2>${escapeHtml(r.project.name)}</h2><p class="report-lead">A bounded record of mathematical terrain screening and human workflow—not a professional archaeological assessment.</p><section class="report-metrics"><div><strong>${r.screening_summary.synthetic_hypotheses}</strong><span>Synthetic hypotheses</span></div><div><strong>${r.screening_summary.reviewed}</strong><span>Human reviewed</span></div><div><strong>${escapeHtml(r.screening_summary.model_execution)}</strong><span>Approved model</span></div></section><h3>Provenance</h3><p>${escapeHtml(r.provenance)}</p><h3>Limitations</h3><ul>${r.limitations.map((x) => `<li>${escapeHtml(x)}</li>`).join("")}</ul><h3>Human observations</h3><p>${r.human_observations.length} separately attributed observation(s) recorded.</p><footer><span>Generated ${escapeHtml(formatDate(r.generated_at))}</span><span>${escapeHtml(r.retention_statement)}</span></footer><button class="secondary-action print-button" data-print>Print / save locally</button></article>`;
}

function timeline(items, evidence = false) {
  if (!items.length) return emptyState("No records yet", "Workflow events will appear here.");
  return `<ol class="timeline">${items.map((item) => `<li><span></span><div><small>${escapeHtml(formatDate(item.created_at))}</small><strong>${escapeHtml(humanize(evidence ? item.evidence_level : item.event_type))}</strong><p>${escapeHtml(evidence ? item.rationale : item.safe_detail)}</p>${evidence ? `<em>${escapeHtml(item.actor)} · ${escapeHtml(item.actor_type)}</em>` : ""}</div></li>`).join("")}</ol>`;
}

function settingsTab() {
  const p = state.project;
  return `<div class="two-column"><section class="panel"><p class="eyebrow">Retention</p><h2>Local project storage</h2><p>Change the declared retention policy for this demonstration record.</p><div class="inline-form"><select id="retention-policy">${["SESSION_ONLY","SEVEN_DAYS","THIRTY_DAYS"].map((x) => `<option value="${x}" ${p.retention_policy === x ? "selected" : ""}>${humanize(x)}</option>`).join("")}</select><button class="secondary-action" data-save-retention>Save</button></div><dl class="detail-grid"><div><dt>Demo member</dt><dd>${escapeHtml(p.owner)}</dd></div><div><dt>Role</dt><dd>Demo reviewer</dd></div><div><dt>Processing</dt><dd>${escapeHtml(humanize(p.status))}</dd></div><div><dt>Export</dt><dd>Browser print only</dd></div></dl></section><section class="panel danger-panel"><p class="eyebrow">Project deletion</p><h2>Delete local record</h2><p>Cascade-delete this project and all associated workflow records.</p><button class="danger-action" data-delete-project="${escapeHtml(p.id)}">Delete project</button></section></div>`;
}

function projectView() {
  const p = state.project;
  let body = projectSummary();
  if (state.projectTab === "processing") body = processingTab();
  if (state.projectTab === "results") body = resultsTab();
  if (state.projectTab === "review") body = reviewTab();
  if (state.projectTab === "report") body = reportTab();
  if (state.projectTab === "audit") body = `<section class="panel"><p class="eyebrow">Accountability trail</p><h2>Project audit</h2>${timeline(state.audit)}</section>`;
  if (state.projectTab === "settings") body = settingsTab();
  return `<header class="page-heading compact"><div><button class="back-link" data-view-target="projects">← Projects</button><div class="heading-line"><h1>${escapeHtml(p.name)}</h1>${statusBadge(p.status)}</div><p>${escapeHtml(p.project_reference)} · ${escapeHtml(p.organization_name)}</p></div></header>${projectTabs()}${body}`;
}

function reviewQueueView() {
  return `<header class="page-heading compact"><div><p class="eyebrow">Professional review</p><h1>Review queue</h1><p>Human attention remains distinct from machine-generated hypotheses.</p></div></header><section class="panel">${state.reviewQueue.length ? `<div class="result-grid">${state.reviewQueue.map(resultCard).join("")}</div>` : emptyState("Nothing awaiting review", "All current synthetic hypotheses have been reviewed.")}</section>`;
}

function reportsView() {
  const ready = state.projects.filter((p) => p.status === "REPORT_READY");
  return `<header class="page-heading compact"><div><p class="eyebrow">Coordinate-safe outputs</p><h1>Reports</h1><p>Limitations-first summaries retained inside this local workspace.</p></div></header><section class="panel">${ready.length ? `<div class="project-cards">${ready.map((p) => `<article><span class="report-icon">▤</span><h3>${escapeHtml(p.name)}</h3><p>${escapeHtml(p.project_reference)}</p><button class="secondary-action" data-open-project="${p.id}" data-tab="report">Open report</button></article>`).join("")}</div>` : emptyState("No reports ready", "Generate a report from a project after synthetic processing.")}</section>`;
}

function auditView() {
  return `<header class="page-heading compact"><div><p class="eyebrow">Accountability</p><h1>Audit records</h1><p>Select a project to inspect its isolated, coordinate-safe event trail.</p></div></header><section class="panel"><div class="project-cards">${state.projects.map((p) => `<article><h3>${escapeHtml(p.name)}</h3><p>${escapeHtml(p.project_reference)}</p><button class="secondary-action" data-open-project="${p.id}" data-tab="audit">View audit</button></article>`).join("")}</div></section>`;
}

function globalSettingsView() {
  const approved = approvedRuntimeAvailable();
  return `<header class="page-heading compact"><div><p class="eyebrow">System boundaries</p><h1>Settings</h1><p>Fixed safeguards for this local demonstration build.</p></div></header><div class="settings-grid"><section class="panel"><span class="setting-icon">⌂</span><h2>Local-only service</h2><p>Bound to loopback. No production authentication, remote deployment, analytics, telemetry, or uploads.</p><strong class="safe-state">ACTIVE</strong></section><section class="panel"><span class="setting-icon">◇</span><h2>Approved model runtime</h2><p>${approved ? "Verified frozen E001 Random Forest. Execution is limited to synthetic terrain on this local server." : "Fail-closed boundary. No artifact path, loading, deserialization, or execution is available."}</p><strong class="${approved ? "safe-state" : "guard-state"}">${approved ? "VERIFIED" : "DISABLED"}</strong></section><section class="panel"><span class="setting-icon">▱</span><h2>Private storage</h2><p>Minimal SQLite state under an ignored private directory. No coordinates, rasters, paths, or feature vectors.</p><strong class="safe-state">LOCAL</strong></section><section class="panel"><span class="setting-icon">◎</span><h2>Evidence ceiling</h2><p>Automatic results stop at machine evidence. Demo human review can record only a human-vetted observation.</p><strong class="safe-state">ENFORCED</strong></section></div>`;
}

function render() {
  setNavigation(state.view);
  const views = { overview: overviewView, projects: projectsView, review: reviewQueueView, reports: reportsView, audit: auditView, settings: globalSettingsView, project: projectView };
  workspace.innerHTML = (views[state.view] || overviewView)();
  workspace.focus({ preventScroll: true });
}

async function navigate(view) {
  state.view = view;
  state.project = null;
  await refreshBase();
  render();
}

function formJson(form) {
  return Object.fromEntries(new FormData(form).entries());
}

document.querySelector("#enter-workspace").addEventListener("click", async () => {
  try {
    state.session = await api("/session");
    applyRuntimeChrome();
    await refreshBase();
    document.querySelector("#organization-name").textContent = state.session.organization.name;
    document.querySelector("#entry-view").hidden = true;
    document.querySelector("#app-shell").hidden = false;
    render();
  } catch { toast("The local portal service is unavailable.", true); }
});

document.addEventListener("click", async (event) => {
  const button = event.target.closest("button");
  if (!button) return;
  try {
    if (button.dataset.view) await navigate(button.dataset.view);
    if (button.dataset.viewTarget) await navigate(button.dataset.viewTarget);
    if (button.hasAttribute("data-new-project")) document.querySelector("#project-dialog").showModal();
    if (button.dataset.close) document.querySelector(`#${button.dataset.close}`).close();
    if (button.dataset.openProject) await openProject(button.dataset.openProject, button.dataset.tab || "summary");
    if (button.dataset.projectTab) { state.projectTab = button.dataset.projectTab; render(); }
    if (button.dataset.authorize) {
      await api(`/projects/${button.dataset.authorize}/authorize-demo`, { method: "POST", body: JSON.stringify({ authorized_data_confirmation: true, reviewer_requirement_acknowledgement: true }) });
      toast("Synthetic-only authorization recorded."); await openProject(button.dataset.authorize);
    }
    if (button.dataset.runDemo) {
      button.disabled = true; button.textContent = "Preparing synthetic terrain…";
      const runtime = document.querySelector("#runtime")?.value || "SYNTHETIC_DEMO";
      await api(`/projects/${button.dataset.runDemo}/run-demo`, { method: "POST", body: JSON.stringify({ scenario: document.querySelector("#scenario").value, runtime }) });
      toast(runtime === "APPROVED_PRIVATE_MODEL" ? "Frozen E001 model executed on synthetic terrain. Human review required." : "Synthetic workflow completed. No model was executed."); await refreshBase(); await openProject(button.dataset.runDemo, "results");
    }
    if (button.dataset.reviewResult) {
      const resultId = button.dataset.reviewResult;
      const result = await api(`/results/${resultId}`);
      if (result.review_state === "UNREVIEWED") await api(`/results/${resultId}/review/start`, { method: "POST" });
      document.querySelector("#review-form [name=result_id]").value = resultId;
      document.querySelector("#review-dialog").showModal();
    }
    if (button.dataset.inspectResult) {
      const result = await api(`/results/${button.dataset.inspectResult}`);
      document.querySelector("#result-detail").innerHTML = `${terrainThumb(result)}<dl class="detail-grid"><div><dt>Opaque result ID</dt><dd>${escapeHtml(result.id)}</dd></div><div><dt>Terrain similarity score</dt><dd>${Number(result.score).toFixed(3)}</dd></div><div><dt>Review priority</dt><dd>${escapeHtml(humanize(result.priority))}</dd></div><div><dt>Evidence level</dt><dd>${escapeHtml(humanize(result.evidence_level))}</dd></div><div><dt>Runtime</dt><dd>${escapeHtml(result.runtime)}</dd></div><div><dt>Model execution</dt><dd>${escapeHtml(result.model_execution)}</dd></div></dl><p class="callout">Terrain morphology prioritized for specialist review. Synthetic terrain only—not archaeology or archaeological probability.</p>`;
      document.querySelector("#result-dialog").showModal();
    }
    if (button.hasAttribute("data-generate-report")) {
      await api(`/projects/${state.project.id}/report`, { method: "POST" });
      toast("Coordinate-safe demonstration report generated."); await openProject(state.project.id, "report");
    }
    if (button.hasAttribute("data-print")) window.print();
    if (button.hasAttribute("data-save-retention")) {
      await api(`/projects/${state.project.id}/retention`, { method: "PATCH", body: JSON.stringify({ retention_policy: document.querySelector("#retention-policy").value }) });
      toast("Retention declaration updated."); await openProject(state.project.id, "settings");
    }
    if (button.dataset.deleteProject) {
      document.querySelector("#delete-form [name=project_id]").value = button.dataset.deleteProject;
      document.querySelector("#delete-dialog").showModal();
    }
  } catch (error) { toast(humanize(error.message), true); }
});

document.querySelector("#project-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const form = event.currentTarget;
    const values = formJson(form);
    values.authorized_data_confirmation = form.elements.authorized_data_confirmation.checked;
    values.reviewer_requirement_acknowledgement = form.elements.reviewer_requirement_acknowledgement.checked;
    const project = await api("/projects", { method: "POST", body: JSON.stringify(values) });
    form.reset(); document.querySelector("#project-dialog").close(); toast("Project created.");
    await refreshBase(); await openProject(project.id);
  } catch (error) { toast(humanize(error.message), true); }
});

document.querySelector("#review-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const form = event.currentTarget;
    const values = formJson(form); const resultId = values.result_id; delete values.result_id;
    values.evidence_level = "HUMAN_VETTED_OBSERVATION";
    await api(`/results/${resultId}/review`, { method: "POST", body: JSON.stringify(values) });
    form.reset(); document.querySelector("#review-dialog").close(); toast("Human observation recorded separately.");
    await refreshBase();
    if (state.project) await openProject(state.project.id, "review"); else await navigate("review");
  } catch (error) { toast(humanize(error.message), true); }
});

document.querySelector("#delete-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const projectId = new FormData(event.currentTarget).get("project_id");
    await api(`/projects/${projectId}`, { method: "DELETE" });
    document.querySelector("#delete-dialog").close(); toast("Project and associated local records deleted."); await navigate("projects");
  } catch (error) { toast(humanize(error.message), true); }
});

workspace.addEventListener("input", (event) => {
  if (event.target.id === "project-search") { state.query = event.target.value; render(); document.querySelector("#project-search")?.focus(); }
  if (event.target.id === "project-status") { state.status = event.target.value; render(); }
  if (event.target.id === "result-priority") { state.resultPriority = event.target.value; render(); }
});

document.querySelector("#mobile-menu").addEventListener("click", () => document.querySelector(".sidebar").classList.toggle("open"));

api("/session").then((session) => { state.session = session; applyRuntimeChrome(); }).catch(() => {});

// Optional local browser-agent affordances. These mirror the same bounded APIs and
// never expose terrain, coordinates, features, model paths, or authorization controls.
if (navigator.modelContext?.registerTool) {
  navigator.modelContext.registerTool({
    name: "list_demo_projects",
    description: "List coordinate-safe projects in the local synthetic ArchaeoAI demonstration.",
    inputSchema: { type: "object", properties: {}, additionalProperties: false },
    execute: async () => ({ content: [{ type: "text", text: JSON.stringify(await api("/projects")) }] }),
  });
}
