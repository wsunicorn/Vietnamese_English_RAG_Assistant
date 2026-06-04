const state = {
  documents: [],
  selectedDocumentIds: new Set(),
  lastChatId: null,
  pendingFile: null,
};

const els = {
  metrics: document.querySelector("#metrics"),
  documents: document.querySelector("#document-list"),
  citations: document.querySelector("#citations"),
  trace: document.querySelector("#retrieval-trace"),
  evidenceSummary: document.querySelector("#evidence-summary"),
  messages: document.querySelector("#messages"),
  uploadForm: document.querySelector("#upload-form"),
  uploadStatus: document.querySelector("#upload-status"),
  fileInput: document.querySelector("#file-input"),
  question: document.querySelector("#question"),
  chatForm: document.querySelector("#chat-form"),
  refreshDocuments: document.querySelector("#refresh-documents"),
  clearChat: document.querySelector("#clear-chat"),
  selectedCount: document.querySelector("#selected-count"),
  clearSelection: document.querySelector("#clear-selection"),
  scopeLabel: document.querySelector("#scope-label"),
  charCount: document.querySelector("#char-count"),
  topK: document.querySelector("#top-k"),
  toastStack: document.querySelector("#toast-stack"),
  evidenceToggle: document.querySelector("#evidence-toggle"),
  evidenceToggleLabel: document.querySelector("#evidence-toggle-label"),
  evidenceToggleMeta: document.querySelector("#evidence-toggle-meta"),
  evidenceDrawer: document.querySelector("#evidence-drawer"),
  closeEvidence: document.querySelector("#close-evidence"),
};

els.uploadForm.addEventListener("submit", uploadDocument);
els.chatForm.addEventListener("submit", sendQuestion);
els.refreshDocuments.addEventListener("click", () => loadDocuments({ quiet: false }));
els.clearSelection.addEventListener("click", clearDocumentSelection);
els.clearChat.addEventListener("click", clearChat);
els.fileInput.addEventListener("change", handleFilePick);
els.question.addEventListener("input", updateCharacterCount);
els.evidenceToggle.addEventListener("click", openEvidence);
els.closeEvidence.addEventListener("click", closeEvidence);
els.evidenceDrawer.querySelector("[data-evidence-close]").addEventListener("click", closeEvidence);

for (const eventName of ["dragenter", "dragover"]) {
  els.uploadForm.addEventListener(eventName, (event) => {
    event.preventDefault();
    els.uploadForm.classList.add("dragging");
  });
}

for (const eventName of ["dragleave", "drop"]) {
  els.uploadForm.addEventListener(eventName, (event) => {
    event.preventDefault();
    els.uploadForm.classList.remove("dragging");
  });
}

els.uploadForm.addEventListener("drop", (event) => {
  const file = event.dataTransfer?.files?.[0];
  if (!file) return;
  state.pendingFile = file;
  els.fileInput.value = "";
  setUploadStatus(`${file.name} selected`, "success");
});

document.querySelectorAll("[data-tab]").forEach((button) => {
  button.addEventListener("click", () => activateEvidenceTab(button.dataset.tab));
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !els.evidenceDrawer.hidden) {
    closeEvidence();
  }
});

await init();

async function init() {
  configureMarkdown();
  renderMetricSkeleton();
  renderDocumentSkeleton();
  updateCharacterCount();
  await Promise.all([loadDocuments({ quiet: true }), loadMetrics()]);
  refreshIcons();
}

async function uploadDocument(event) {
  event.preventDefault();
  const file = state.pendingFile || els.fileInput.files[0];
  if (!file) {
    setUploadStatus("Choose a file first.", "error");
    toast("Upload blocked", "Choose a PDF, DOCX, or TXT file first.", "error");
    return;
  }

  const extension = file.name.split(".").pop()?.toLowerCase();
  if (!["pdf", "docx", "txt"].includes(extension)) {
    setUploadStatus("Unsupported file type.", "error");
    toast("Unsupported file", "Only PDF, DOCX, and TXT files can be indexed.", "error");
    return;
  }

  setUploadStatus("Indexing document...", "");
  els.uploadForm.querySelector("button[type='submit']").disabled = true;

  try {
    const formData = new FormData();
    formData.append("file", file);
    const response = await fetch("/documents/upload", {
      method: "POST",
      body: formData,
    });
    const payload = await readJson(response);
    state.pendingFile = null;
    els.fileInput.value = "";
    setUploadStatus(`${payload.filename} indexed with ${payload.chunk_count} chunks.`, "success");
    toast("Indexed", `${payload.chunk_count} chunks are ready for retrieval.`, "success");
    await Promise.all([loadDocuments({ quiet: true }), loadMetrics()]);
  } catch (error) {
    setUploadStatus(error.message, "error");
    toast("Upload failed", error.message, "error");
  } finally {
    els.uploadForm.querySelector("button[type='submit']").disabled = false;
  }
}

async function loadDocuments({ quiet }) {
  if (!quiet) renderDocumentSkeleton();
  try {
    const response = await fetch("/documents");
    state.documents = await readJson(response);
    syncSelectedDocumentIds();
    renderDocuments();
    updateScopeLabels();
  } catch (error) {
    els.documents.innerHTML = emptyState("folder-x", "Documents unavailable", error.message);
    toast("Document list failed", error.message, "error");
  } finally {
    refreshIcons();
  }
}

function renderDocuments() {
  if (!state.documents.length) {
    els.documents.innerHTML = emptyState(
      "folder-open",
      "No documents",
      "Corpus is empty.",
    );
    return;
  }

  els.documents.innerHTML = state.documents.map(renderDocumentCard).join("");
  els.documents.querySelectorAll("[data-select-document]").forEach((checkbox) => {
    checkbox.addEventListener("change", () => toggleDocument(checkbox.dataset.selectDocument));
  });
  els.documents.querySelectorAll("[data-delete-document]").forEach((button) => {
    button.addEventListener("click", () => deleteDocument(button.dataset.deleteDocument));
  });
}

function renderDocumentCard(doc) {
  const selected = state.selectedDocumentIds.has(doc.document_id);
  const statusClass = normalizeStatus(doc.status);
  const created = formatDate(doc.created_at);
  return `
    <article class="document-card ${selected ? "selected" : ""}">
      <input
        class="document-checkbox"
        type="checkbox"
        ${selected ? "checked" : ""}
        data-select-document="${escapeHtml(doc.document_id)}"
        aria-label="Select ${escapeHtml(doc.filename)}"
      />
      <div class="document-main">
        <strong class="document-title">${escapeHtml(doc.filename)}</strong>
        <span class="document-subline">${escapeHtml(doc.content_type || "document")} · ${created}</span>
        <div class="document-meta">
          <span class="status-pill ${statusClass}">${escapeHtml(doc.status)}</span>
          <span class="doc-pill">${doc.chunk_count} chunks</span>
          <span class="doc-pill">${escapeHtml(doc.language || "unknown")}</span>
        </div>
        <button class="delete-button" type="button" data-delete-document="${escapeHtml(doc.document_id)}">
          <i data-lucide="trash-2"></i>
          <span>Delete</span>
        </button>
      </div>
    </article>
  `;
}

async function deleteDocument(documentId) {
  try {
    const response = await fetch(`/documents/${documentId}`, { method: "DELETE" });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.detail || "Delete failed.");
    }
    state.selectedDocumentIds.delete(documentId);
    toast("Deleted", "Document and vectors were removed.", "success");
    await Promise.all([loadDocuments({ quiet: true }), loadMetrics()]);
  } catch (error) {
    toast("Delete failed", error.message, "error");
  }
}

function toggleDocument(documentId) {
  if (state.selectedDocumentIds.has(documentId)) {
    state.selectedDocumentIds.delete(documentId);
  } else {
    state.selectedDocumentIds.add(documentId);
  }
  renderDocuments();
  updateScopeLabels();
  refreshIcons();
}

function clearDocumentSelection() {
  state.selectedDocumentIds.clear();
  renderDocuments();
  updateScopeLabels();
  refreshIcons();
}

async function sendQuestion(event) {
  event.preventDefault();
  const question = els.question.value.trim();
  if (!question) return;

  appendMessage("user", question);
  const loading = appendLoadingMessage();
  els.question.value = "";
  updateCharacterCount();
  els.chatForm.querySelector("button[type='submit']").disabled = true;

  try {
    const body = {
      question,
      top_k: Number(els.topK.value),
    };
    if (state.selectedDocumentIds.size) {
      body.document_ids = [...state.selectedDocumentIds];
    }

    const response = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const payload = await readJson(response);
    state.lastChatId = payload.chat_id;
    loading.remove();
    appendMessage("assistant", payload.answer, {
      noAnswer: payload.no_answer,
      payload,
    });
    renderEvidence(payload);
    await loadMetrics();
  } catch (error) {
    loading.remove();
    appendMessage("assistant", error.message, { noAnswer: true });
    toast("Chat failed", error.message, "error");
  } finally {
    els.chatForm.querySelector("button[type='submit']").disabled = false;
    refreshIcons();
  }
}

function appendMessage(role, content, options = {}) {
  const node = document.createElement("article");
  const isUser = role === "user";
  node.className = `message ${isUser ? "user-message" : "assistant-message"}${options.noAnswer ? " no-answer" : ""}`;
  node.innerHTML = `
    <div class="avatar">
      <i data-lucide="${isUser ? "user" : options.noAnswer ? "circle-alert" : "sparkles"}"></i>
    </div>
    <div class="message-body">
      <div class="message-content ${isUser ? "plain-content" : "markdown-content"}">
        ${renderMessageContent(content, isUser)}
      </div>
      ${options.payload ? renderAssistantMeta(options.payload) : ""}
    </div>
  `;

  enhanceMessageNode(node);
  if (options.payload) {
    node.querySelectorAll("[data-rating]").forEach((button) => {
      button.addEventListener("click", () => sendFeedback(Number(button.dataset.rating), node));
    });
  }

  els.messages.appendChild(node);
  els.messages.scrollTop = els.messages.scrollHeight;
  refreshIcons();
  return node;
}

function appendLoadingMessage() {
  const node = document.createElement("article");
  node.className = "message assistant-message";
  node.innerHTML = `
    <div class="avatar"><i data-lucide="search"></i></div>
    <div class="message-body loading-card">
      <div class="message-content plain-content">Retrieving evidence and drafting a grounded answer...</div>
    </div>
  `;
  els.messages.appendChild(node);
  els.messages.scrollTop = els.messages.scrollHeight;
  refreshIcons();
  return node;
}

function renderAssistantMeta(payload) {
  const citationCount = payload.citations?.length || 0;
  const tokens = payload.usage?.total_tokens || 0;
  return `
    <div class="message-meta">
      <span class="doc-pill">${payload.latency_ms} ms</span>
      <span class="doc-pill">${citationCount} citations</span>
      <span class="doc-pill">${tokens} tokens</span>
      <div class="feedback-row">
        <button class="feedback-button" type="button" data-rating="1">
          <i data-lucide="thumbs-up"></i>
          <span>Helpful</span>
        </button>
        <button class="feedback-button" type="button" data-rating="-1">
          <i data-lucide="thumbs-down"></i>
          <span>Needs work</span>
        </button>
        <span class="feedback-status" aria-live="polite"></span>
      </div>
    </div>
  `;
}

async function sendFeedback(rating, messageNode) {
  if (!state.lastChatId) return;
  const buttons = messageNode.querySelectorAll("[data-rating]");
  const status = messageNode.querySelector(".feedback-status");
  buttons.forEach((button) => (button.disabled = true));
  status.textContent = "Saving...";
  try {
    const response = await fetch("/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ chat_id: state.lastChatId, rating }),
    });
    await readJson(response);
    buttons.forEach((button) => button.classList.add("sent"));
    status.textContent = "Feedback saved";
    await loadMetrics();
  } catch (error) {
    buttons.forEach((button) => (button.disabled = false));
    status.textContent = "Save failed";
    toast("Feedback failed", error.message, "error");
  }
}

function renderEvidence(payload) {
  renderCitations(payload.citations || []);
  renderTrace(payload.retrieval_trace || []);
  renderEvidenceSummary(payload);
  activateEvidenceTab("citations");
  refreshIcons();
}

function renderCitations(citations) {
  if (!citations.length) {
    els.citations.innerHTML = emptyState("quote", "No citations", "This answer did not return source snippets.");
    return;
  }
  els.citations.innerHTML = citations.map(renderCitationCard).join("");
}

function renderCitationCard(citation) {
  return `
    <article class="citation-card">
      <strong class="citation-title">${escapeHtml(citation.citation_id)} · ${escapeHtml(citation.filename)}</strong>
      <div class="citation-meta">
        <span class="doc-pill">Page ${escapeHtml(citation.page || "unknown")}</span>
        <span class="score-pill">Score ${Number(citation.score || 0).toFixed(4)}</span>
      </div>
      <p class="quote-text">${escapeHtml(citation.quote)}</p>
    </article>
  `;
}

function renderTrace(trace) {
  if (!trace.length) {
    els.trace.innerHTML = emptyState("route", "No trace", "No retrieval trace yet.");
    return;
  }
  els.trace.innerHTML = trace
    .map(
      (item, index) => `
        <article class="trace-card">
          <strong class="citation-title">Rank ${index + 1} · ${escapeHtml(item.filename || "Unknown file")}</strong>
          <div class="citation-meta">
            <span class="doc-pill">Page ${escapeHtml(item.page || "unknown")}</span>
            <span class="score-pill">Score ${Number(item.score || 0).toFixed(4)}</span>
          </div>
          <pre>${escapeHtml((item.text || "").slice(0, 900))}</pre>
        </article>
      `,
    )
    .join("");
}

function renderEvidenceSummary(payload) {
  const citationCount = payload.citations?.length || 0;
  const traceCount = payload.retrieval_trace?.length || 0;
  const latency = Number(payload.latency_ms || 0);
  const className = payload.no_answer ? "summary-pill no-answer" : "summary-pill ready";
  const label = payload.no_answer ? "No answer" : "Grounded";
  els.evidenceSummary.innerHTML = `
    <span class="${className}">${label}</span>
    <strong>${citationCount} citations · ${traceCount} trace items</strong>
  `;
  updateEvidenceToggle({
    citationCount,
    traceCount,
    latency,
    noAnswer: Boolean(payload.no_answer),
  });
}

function activateEvidenceTab(tabName) {
  document.querySelectorAll("[data-tab]").forEach((button) => {
    button.classList.toggle("active", button.dataset.tab === tabName);
  });
  document.querySelectorAll("[data-panel]").forEach((panel) => {
    panel.classList.toggle("active", panel.dataset.panel === tabName);
  });
}

async function loadMetrics() {
  try {
    const response = await fetch("/metrics");
    const metrics = await readJson(response);
    els.metrics.innerHTML = `
      ${metricCard("Documents", metrics.documents)}
      ${metricCard("Chunks", metrics.chunks)}
      ${metricCard("Chats", metrics.chats)}
      ${metricCard("Latency", `${metrics.avg_chat_latency_ms} ms`)}
    `;
  } catch {
    renderMetricSkeleton();
  } finally {
    refreshIcons();
  }
}

function metricCard(label, value) {
  return `
    <article class="metric-card">
      <span>${label}</span>
      <strong>${value}</strong>
    </article>
  `;
}

function clearChat() {
  state.lastChatId = null;
  els.messages.innerHTML = `
    <article class="message assistant-message">
      <div class="avatar"><i data-lucide="sparkles"></i></div>
      <div class="message-body">
        <div class="message-content plain-content">Chat cleared. Ready for new questions.</div>
      </div>
    </article>
  `;
  els.citations.innerHTML = emptyState("quote", "No citations", "No source snippets yet.");
  els.trace.innerHTML = emptyState("route", "No trace", "No retrieval trace yet.");
  els.evidenceSummary.innerHTML = `
    <span class="summary-pill">Awaiting answer</span>
    <strong>0 citations</strong>
  `;
  updateEvidenceToggle({ citationCount: 0, traceCount: 0, latency: 0, noAnswer: false });
  closeEvidence();
  refreshIcons();
}

function handleFilePick() {
  state.pendingFile = null;
  const file = els.fileInput.files[0];
  setUploadStatus(file ? `${file.name} selected` : "Ready", file ? "success" : "");
}

function setUploadStatus(message, kind) {
  els.uploadStatus.textContent = message;
  els.uploadStatus.className = `status-text ${kind || ""}`.trim();
}

function syncSelectedDocumentIds() {
  const existingIds = new Set(state.documents.map((doc) => doc.document_id));
  state.selectedDocumentIds.forEach((id) => {
    if (!existingIds.has(id)) state.selectedDocumentIds.delete(id);
  });
}

function updateScopeLabels() {
  const count = state.selectedDocumentIds.size;
  els.selectedCount.textContent = count ? `${count} selected` : "All documents";
  els.scopeLabel.textContent = count
    ? `Scope: ${count} selected document${count === 1 ? "" : "s"}`
    : "Scope: all indexed documents";
}

function updateCharacterCount() {
  els.charCount.textContent = `${els.question.value.length} / 4000`;
}

function updateEvidenceToggle({ citationCount, traceCount, latency, noAnswer }) {
  const hasEvidence = citationCount > 0 || traceCount > 0;
  els.evidenceToggle.classList.toggle("has-evidence", hasEvidence);
  els.evidenceToggleLabel.textContent = `${citationCount} citation${citationCount === 1 ? "" : "s"}`;

  if (noAnswer) {
    els.evidenceToggleMeta.textContent = "No-answer trace";
  } else if (hasEvidence) {
    els.evidenceToggleMeta.textContent = `${traceCount} trace · ${latency || 0} ms`;
  } else {
    els.evidenceToggleMeta.textContent = "View evidence";
  }
}

function openEvidence() {
  els.evidenceDrawer.hidden = false;
  els.evidenceDrawer.setAttribute("aria-hidden", "false");
  document.body.classList.add("drawer-open");
  requestAnimationFrame(() => {
    els.closeEvidence.focus();
  });
}

function closeEvidence() {
  els.evidenceDrawer.hidden = true;
  els.evidenceDrawer.setAttribute("aria-hidden", "true");
  document.body.classList.remove("drawer-open");
}

function renderMetricSkeleton() {
  els.metrics.innerHTML = `
    ${metricCard("Documents", "--")}
    ${metricCard("Chunks", "--")}
    ${metricCard("Chats", "--")}
    ${metricCard("Latency", "--")}
  `;
}

function renderDocumentSkeleton() {
  els.documents.innerHTML = Array.from({ length: 3 })
    .map(
      () => `
        <article class="document-card loading-card">
          <span class="document-checkbox"></span>
          <div class="document-main">
            <strong class="document-title">Loading document</strong>
            <span class="document-subline">Refreshing corpus</span>
            <div class="document-meta">
              <span class="doc-pill">--</span>
              <span class="doc-pill">--</span>
            </div>
          </div>
        </article>
      `,
    )
    .join("");
}

function emptyState(icon, title, text) {
  return `
    <article class="empty-state">
      <i data-lucide="${icon}"></i>
      <strong>${escapeHtml(title)}</strong>
      <span>${escapeHtml(text)}</span>
    </article>
  `;
}

function toast(title, message, kind = "") {
  const node = document.createElement("div");
  node.className = `toast ${kind}`.trim();
  node.innerHTML = `
    <i data-lucide="${kind === "error" ? "circle-alert" : "circle-check"}"></i>
    <div>
      <strong>${escapeHtml(title)}</strong>
      <p>${escapeHtml(message)}</p>
    </div>
  `;
  els.toastStack.appendChild(node);
  refreshIcons();
  setTimeout(() => node.remove(), 4200);
}

async function readJson(response) {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail || `Request failed with status ${response.status}`);
  }
  return payload;
}

function normalizeStatus(status) {
  return String(status || "").trim().toLowerCase().replaceAll(" ", "-");
}

function formatDate(value) {
  if (!value) return "unknown date";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "unknown date";
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function configureMarkdown() {
  if (!window.marked) return;
  window.marked.setOptions({
    gfm: true,
    breaks: true,
  });
}

function renderMessageContent(value, isUser) {
  if (isUser) {
    return renderPlainText(value);
  }
  return renderMarkdown(value);
}

function renderPlainText(value) {
  return escapeHtml(value).replaceAll("\n", "<br>");
}

function renderMarkdown(value) {
  const source = String(value ?? "");
  if (!window.marked) {
    return highlightCitations(renderPlainText(source));
  }

  const rawHtml = window.marked.parse(source, {
    gfm: true,
    breaks: true,
  });
  const cleanHtml = window.DOMPurify
    ? window.DOMPurify.sanitize(rawHtml, {
        USE_PROFILES: { html: true },
      })
    : rawHtml;
  return highlightCitations(cleanHtml);
}

function highlightCitations(html) {
  return String(html).replaceAll(/\[(C\d+)\]/g, '<span class="citation-token">[$1]</span>');
}

function enhanceMessageNode(node) {
  node.querySelectorAll(".markdown-content a").forEach((link) => {
    link.setAttribute("target", "_blank");
    link.setAttribute("rel", "noreferrer noopener");
  });

  node.querySelectorAll(".markdown-content pre").forEach((pre) => {
    if (pre.querySelector(".copy-code-button")) return;
    const button = document.createElement("button");
    button.className = "copy-code-button";
    button.type = "button";
    button.innerHTML = '<i data-lucide="copy"></i><span>Copy</span>';
    button.addEventListener("click", async () => {
      await copyToClipboard(pre.querySelector("code")?.innerText || pre.innerText || "");
      button.innerHTML = '<i data-lucide="check"></i><span>Copied</span>';
      refreshIcons();
      setTimeout(() => {
        button.innerHTML = '<i data-lucide="copy"></i><span>Copy</span>';
        refreshIcons();
      }, 1400);
    });
    pre.appendChild(button);
  });
}

async function copyToClipboard(value) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(value);
    return;
  }
  const textarea = document.createElement("textarea");
  textarea.value = value;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.opacity = "0";
  document.body.appendChild(textarea);
  textarea.select();
  document.execCommand("copy");
  textarea.remove();
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function refreshIcons() {
  if (window.lucide) {
    window.lucide.createIcons();
  }
}

window.addEventListener("load", refreshIcons);
