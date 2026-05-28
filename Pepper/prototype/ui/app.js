const STORAGE_KEY = "pepperWizardState";

const stepPanels = {
  1: document.getElementById("step-1"),
  2: document.getElementById("step-2"),
};
const stepPills = document.querySelectorAll(".step-pill");
const configForm = document.getElementById("config-form");
const customerSelect = document.getElementById("customer");
const reportTypeSelect = document.getElementById("report-type");
const instructionsInput = document.getElementById("instructions");
const typeCardsContainer = document.getElementById("report-type-cards");
const reportPreview = document.getElementById("report-preview");
const editPanel = document.getElementById("edit-panel");
const reportEditor = document.getElementById("report-editor");
const generateBtn = document.getElementById("generate-btn");
const feedbackPanel = document.getElementById("feedback-panel");
const toggleFeedbackBtn = document.getElementById("toggle-feedback");
const feedbackUpBtn = document.getElementById("feedback-up");
const feedbackDownBtn = document.getElementById("feedback-down");
const feedbackText = document.getElementById("feedback-text");
const submitFeedbackBtn = document.getElementById("submit-feedback");
const feedbackMessage = document.getElementById("feedback-message");

let wizardState = loadWizardState();
let reportResult = null;
let selectedFeedback = null;

const REPORT_TYPE_DESCRIPTIONS = {
  weekly:
    "Operational updates, deliverables, and ranking changes.",
  monthly:
    "Performance trends, learnings, and growth insights.",
  quarterly:
    "Business impact, strategic positioning, and KPI review.",
};

function loadWizardState() {
  try {
    return JSON.parse(sessionStorage.getItem(STORAGE_KEY) || "{}");
  } catch {
    return {};
  }
}

function saveWizardState() {
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(wizardState));
}

function goToStep(step) {
  Object.entries(stepPanels).forEach(([n, panel]) => {
    if (!panel) return;
    panel.classList.toggle("active", Number(n) === step);
  });
  stepPills.forEach((pill) => {
    pill.classList.toggle("active", Number(pill.dataset.step) === step);
    pill.classList.toggle("done", Number(pill.dataset.step) < step);
  });
  wizardState.currentStep = step;
  saveWizardState();
}

function showError(el, message) {
  if (!el) return;
  if (!message) {
    el.hidden = true;
    el.textContent = "";
    return;
  }
  el.hidden = false;
  el.textContent = message;
}

async function loadCustomers() {
  const response = await fetch("/api/customers");
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Failed to load customers.");
  customerSelect.innerHTML = "";
  data.customers.forEach((c) => {
    const opt = document.createElement("option");
    opt.value = c.id;
    opt.textContent = c.name;
    customerSelect.appendChild(opt);
  });
  if (wizardState.customerId) {
    customerSelect.value = wizardState.customerId;
  }
  if (wizardState.reportType) {
    reportTypeSelect.value = wizardState.reportType;
  }
  if (wizardState.instructions) {
    instructionsInput.value = wizardState.instructions;
  }
}

async function loadTemplates() {
  try {
    const response = await fetch("/api/report-templates");
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Failed to load templates.");

    const templates = data.templates || [];
    typeCardsContainer.innerHTML = "";
    templates.forEach((tpl) => {
      const card = document.createElement("article");
      card.className = "type-card";
      const sources = (tpl.sources || []).join(", ") || "Template-defined";
      const audience = (tpl.audience || []).join(", ") || "CSM, Marketing, Leadership";
      const objective =
        tpl.objective || REPORT_TYPE_DESCRIPTIONS[tpl.id] || "Performance reporting";
      card.innerHTML = `
        <h3>${escapeHtml(tpl.label || tpl.id)}</h3>
        <p>${escapeHtml(REPORT_TYPE_DESCRIPTIONS[tpl.id] || objective)}</p>
        <div class="mini-meta"><strong>Audience:</strong> ${escapeHtml(audience)}</div>
        <div class="mini-meta"><strong>Data sources:</strong> ${escapeHtml(sources)}</div>
      `;
      typeCardsContainer.appendChild(card);
    });
  } catch (err) {
    typeCardsContainer.innerHTML = `<p class="field-help">${escapeHtml(
      err.message || "Unable to load report template details."
    )}</p>`;
  }
}

configForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const step1Error = document.getElementById("step1-error");
  const step2Error = document.getElementById("step2-error");
  showError(step1Error, "");
  showError(step2Error, "");

  wizardState = {
    ...wizardState,
    customerId: customerSelect.value,
    reportType: reportTypeSelect.value,
    instructions: instructionsInput.value || "",
  };
  saveWizardState();

  generateBtn.disabled = true;
  const prevLabel = generateBtn.textContent;
  generateBtn.textContent = "Generating…";

  try {
    const response = await fetch("/api/reports/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        customerId: wizardState.customerId,
        reportType: wizardState.reportType,
        instructions: wizardState.instructions || "",
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Report generation failed.");

    reportResult = data;
    wizardState.reportMarkdown = data.reportMarkdown;
    wizardState.chartFilenames = (data.charts || []).map((c) => c.filename);
    saveWizardState();
    renderReportStep();
    goToStep(2);
  } catch (err) {
    showError(step1Error, err.message);
  } finally {
    generateBtn.disabled = false;
    generateBtn.textContent = prevLabel;
  }
});

function renderReportStep() {
  reportPreview.innerHTML = "";
  const iframe = document.createElement("iframe");
  iframe.className = "report-iframe";
  iframe.title = "Report preview";
  reportPreview.appendChild(iframe);
  iframe.srcdoc = reportResult.reportHtml;

  reportEditor.value = reportResult.reportMarkdown;
  editPanel.hidden = true;
  resetFeedbackUi();
}

function resetFeedbackUi() {
  selectedFeedback = null;
  feedbackUpBtn.classList.remove("active");
  feedbackUpBtn.setAttribute("aria-pressed", "false");
  feedbackDownBtn.classList.remove("active");
  feedbackDownBtn.setAttribute("aria-pressed", "false");
  feedbackText.value = "";
  feedbackMessage.hidden = true;
  feedbackMessage.textContent = "";
  feedbackPanel.hidden = true;
  toggleFeedbackBtn.textContent = "Share feedback";
}

function setFeedbackSelection(value) {
  selectedFeedback = value;
  const upActive = value === "up";
  const downActive = value === "down";
  feedbackUpBtn.classList.toggle("active", upActive);
  feedbackUpBtn.setAttribute("aria-pressed", String(upActive));
  feedbackDownBtn.classList.toggle("active", downActive);
  feedbackDownBtn.setAttribute("aria-pressed", String(downActive));
}

document.getElementById("toggle-edit").addEventListener("click", () => {
  const hidden = editPanel.hidden;
  editPanel.hidden = !hidden;
  document.getElementById("toggle-edit").textContent = hidden
    ? "Hide editor"
    : "Edit report";
});

document.getElementById("save-preview").addEventListener("click", () => {
  reportResult.reportMarkdown = reportEditor.value;
  wizardState.reportMarkdown = reportEditor.value;
  saveWizardState();

  const narrativeHtml = simpleMarkdownToHtml(reportEditor.value);
  const parser = new DOMParser();
  const doc = parser.parseFromString(reportResult.reportHtml, "text/html");
  const narrative = doc.querySelector(".narrative");
  if (narrative) {
    narrative.innerHTML = narrativeHtml;
    reportResult.reportHtml = doc.documentElement.outerHTML;
  }

  const iframe = reportPreview.querySelector("iframe");
  if (iframe) iframe.srcdoc = reportResult.reportHtml;
});

toggleFeedbackBtn.addEventListener("click", () => {
  const opening = feedbackPanel.hidden;
  feedbackPanel.hidden = !opening;
  toggleFeedbackBtn.textContent = opening ? "Hide feedback" : "Share feedback";
  if (opening) {
    feedbackText.focus();
  }
});

feedbackUpBtn.addEventListener("click", () => {
  setFeedbackSelection("up");
});

feedbackDownBtn.addEventListener("click", () => {
  setFeedbackSelection("down");
});

submitFeedbackBtn.addEventListener("click", () => {
  if (!selectedFeedback) {
    feedbackMessage.hidden = false;
    feedbackMessage.textContent = "Please choose thumbs up or thumbs down before submitting.";
    feedbackMessage.classList.remove("success");
    return;
  }

  const payload = {
    sentiment: selectedFeedback,
    text: feedbackText.value.trim(),
    reportType: reportResult?.reportType,
    customerName: reportResult?.customerName,
  };
  console.info("Feedback captured (not persisted):", payload);

  feedbackMessage.hidden = false;
  feedbackMessage.textContent = "Thanks for the feedback. It is shared for this session only.";
  feedbackMessage.classList.add("success");
  submitFeedbackBtn.disabled = true;
  setTimeout(() => {
    submitFeedbackBtn.disabled = false;
    resetFeedbackUi();
  }, 1400);
});

document.getElementById("download-pdf").addEventListener("click", async () => {
  const step2Error = document.getElementById("step2-error");
  showError(step2Error, "");

  try {
    const response = await fetch("/api/reports/pdf", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        reportMarkdown: reportResult.reportMarkdown,
        customerName: reportResult.customerName,
        reportType: reportResult.reportTypeLabel || reportResult.reportType,
        chartFilenames: wizardState.chartFilenames || [],
      }),
    });
    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.error || "PDF export failed.");
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${reportResult.customerName || "customer"}_report.pdf`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  } catch (err) {
    showError(step2Error, err.message);
  }
});

document.getElementById("start-over").addEventListener("click", () => {
  sessionStorage.removeItem(STORAGE_KEY);
  wizardState = {};
  reportResult = null;
  configForm.reset();
  resetFeedbackUi();
  goToStep(1);
});

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function simpleMarkdownToHtml(md) {
  return md
    .split("\n")
    .map((line) => {
      const t = line.trim();
      if (!t) return "";
      if (t.startsWith("### ")) return `<h3>${escapeHtml(t.slice(4))}</h3>`;
      if (t.startsWith("## ")) return `<h2>${escapeHtml(t.slice(3))}</h2>`;
      if (t.startsWith("# ")) return `<h1>${escapeHtml(t.slice(2))}</h1>`;
      if (t.startsWith("- ")) return `<li>${escapeHtml(t.slice(2))}</li>`;
      return `<p>${escapeHtml(t)}</p>`;
    })
    .join("\n");
}

loadCustomers().catch((err) => {
  console.error(err);
});
loadTemplates();

if (wizardState.currentStep === 2 && wizardState.reportMarkdown) {
  goToStep(1);
} else {
  goToStep(wizardState.currentStep || 1);
}
