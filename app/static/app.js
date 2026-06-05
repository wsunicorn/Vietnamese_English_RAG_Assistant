/* ═══════════════════════════════════════════════
   RAG ASSISTANT - APP.JS
   SPA Router, Particle Canvas, Scroll Reveal,
   Chat/Document/Source/Evidence Logic
   ═══════════════════════════════════════════════ */

const state = {
  documents: [],
  sources: [],
  selectedDocumentIds: new Set(),
  lastChatId: null,
  pendingFile: null,
  theme: "dark",
  railCollapsed: false,
  railOpen: false,
  evidenceCloseTimer: null,
  activeRailTab: "sources",
  chatHistory: [],
  realtimeSocket: null,
  realtimeReconnectTimer: null,
  realtimeRefreshTimer: null,
  pendingRealtimeRefresh: new Set(),
  currentPage: "landing",
  particleAnimFrame: null,
};

/* ═══════════════════════════════════════════════
   DOM REFERENCES
   ═══════════════════════════════════════════════ */

const els = {
  landingPage: document.querySelector("#landing-page"),
  appPage: document.querySelector("#app-page"),
  heroSection: document.querySelector("#hero-section"),
  particleCanvas: document.querySelector("#particle-canvas"),
  metrics: document.querySelector("#metrics"),
  documents: document.querySelector("#document-list"),
  sources: document.querySelector("#source-list"),
  citations: document.querySelector("#citations"),
  trace: document.querySelector("#retrieval-trace"),
  evidenceSummary: document.querySelector("#evidence-summary"),
  messages: document.querySelector("#messages"),
  uploadForm: document.querySelector("#upload-form"),
  uploadStatus: document.querySelector("#upload-status"),
  urlForm: document.querySelector("#url-ingest-form"),
  urlStatus: document.querySelector("#url-status"),
  sourceUrl: document.querySelector("#source-url"),
  sourceMode: document.querySelector("#source-mode"),
  sourceMaxPages: document.querySelector("#source-max-pages"),
  sourceSyncInterval: document.querySelector("#source-sync-interval"),
  fileInput: document.querySelector("#file-input"),
  question: document.querySelector("#question"),
  chatForm: document.querySelector("#chat-form"),
  refreshDocuments: document.querySelector("#refresh-documents"),
  clearChat: document.querySelector("#clear-chat"),
  selectedCount: document.querySelector("#selected-count"),
  clearSelection: document.querySelector("#clear-selection"),
  reindexAll: document.querySelector("#reindex-all"),
  scopeLabel: document.querySelector("#scope-label"),
  charCount: document.querySelector("#char-count"),
  topK: document.querySelector("#top-k"),
  toastStack: document.querySelector("#toast-stack"),
  evidenceToggle: document.querySelector("#evidence-toggle"),
  evidenceToggleLabel: document.querySelector("#evidence-toggle-label"),
  evidenceToggleMeta: document.querySelector("#evidence-toggle-meta"),
  evidenceDrawer: document.querySelector("#evidence-drawer"),
  closeEvidence: document.querySelector("#close-evidence"),
  railToggle: document.querySelector("#rail-toggle"),
  closeRail: document.querySelector("#close-rail"),
  railScrim: document.querySelector("#rail-scrim"),
  realtimeStatus: document.querySelector("#realtime-status"),
  railTabButtons: document.querySelectorAll("[data-rail-tab]"),
  railPanels: document.querySelectorAll("[data-rail-panel]"),
  historyList: document.querySelector("#history-list"),
  clearHistory: document.querySelector("#clear-history"),
  themeToggle: document.querySelector("#theme-toggle"),
  landingThemeToggle: document.querySelector("#landing-theme-toggle"),
  themeColor: document.querySelector('meta[name="theme-color"]'),
  navLinks: document.querySelectorAll("[data-nav]"),
};

/* ═══════════════════════════════════════════════
   EVENT LISTENERS
   ═══════════════════════════════════════════════ */

els.uploadForm.addEventListener("submit", uploadDocument);
els.urlForm.addEventListener("submit", ingestUrl);
els.chatForm.addEventListener("submit", sendQuestion);
els.refreshDocuments.addEventListener("click", () =>
  Promise.all([loadDocuments({ quiet: false }), loadSources(), loadMetrics()]),
);
els.clearSelection.addEventListener("click", clearDocumentSelection);
els.clearChat.addEventListener("click", clearChat);
els.reindexAll.addEventListener("click", reindexAllSources);
els.fileInput.addEventListener("change", handleFilePick);
els.question.addEventListener("input", updateCharacterCount);
els.question.addEventListener("keydown", handleComposerKeydown);
els.evidenceToggle.addEventListener("click", openEvidence);
els.closeEvidence.addEventListener("click", closeEvidence);
els.evidenceDrawer.querySelector("[data-evidence-close]").addEventListener("click", closeEvidence);
els.railToggle.addEventListener("click", toggleRail);
els.closeRail.addEventListener("click", () => setRailOpen(false));
els.railScrim.addEventListener("click", () => setRailOpen(false));
els.railTabButtons.forEach((button) => {
  button.addEventListener("click", () => setRailTab(button.dataset.railTab));
});
els.clearHistory.addEventListener("click", clearChatHistory);

// Theme toggles (single icon button)
els.themeToggle.addEventListener("click", () => toggleTheme());
els.landingThemeToggle.addEventListener("click", () => toggleTheme());

// Landing nav links
els.navLinks.forEach((link) => {
  link.addEventListener("click", (e) => {
    e.preventDefault();
    navigateTo(link.dataset.nav === "app" ? "app" : "landing");
  });
});

// Hash navigation links (hero CTAs, etc.)
document.querySelectorAll('a[href="#app"]').forEach((link) => {
  link.addEventListener("click", (e) => {
    e.preventDefault();
    navigateTo("app");
  });
});
document.querySelectorAll('a[href="#home"]').forEach((link) => {
  link.addEventListener("click", (e) => {
    e.preventDefault();
    navigateTo("landing");
  });
});

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
  } else if (event.key === "Escape" && state.railOpen) {
    setRailOpen(false);
  }
});

window.matchMedia("(max-width: 780px)").addEventListener("change", () => {
  setRailOpen(false);
  updateShellControls();
});

window.addEventListener("beforeunload", () => {
  state.realtimeSocket?.close();
});

window.addEventListener("hashchange", handleHashNavigation);

await init();

/* ═══════════════════════════════════════════════
   INIT
   ═══════════════════════════════════════════════ */

async function init() {
  window.scrollTo({ top: 0, left: 0, behavior: "auto" });
  initTheme();
  initShellPreferences();
  loadChatHistory();
  configureMarkdown();
  renderMetricSkeleton();
  renderDocumentSkeleton();
  renderSourceSkeleton();
  renderChatHistory();
  updateCharacterCount();
  connectRealtime();
  initScrollReveal();
  initParticleCanvas();
  handleHashNavigation();
  await Promise.all([loadDocuments({ quiet: true }), loadSources(), loadMetrics()]);
  window.scrollTo({ top: 0, left: 0, behavior: "auto" });
  refreshIcons();
}

/* ═══════════════════════════════════════════════
   SPA PAGE ROUTER
   ═══════════════════════════════════════════════ */

function navigateTo(page) {
  const target = page === "app" ? "app" : "landing";
  if (state.currentPage === target) return;

  window.location.hash = target === "app" ? "app" : "home";
}

function handleHashNavigation() {
  const hash = window.location.hash.replace("#", "") || "home";
  const target = hash === "app" ? "app" : "landing";
  showPage(target);
}

function showPage(page) {
  state.currentPage = page;

  if (page === "app") {
    els.landingPage.hidden = true;
    els.appPage.hidden = false;
    document.body.classList.remove("on-landing");
    document.body.style.overflow = "hidden";
    cancelAnimationFrame(state.particleAnimFrame);
    updateNavActive("app");
  } else {
    els.landingPage.hidden = false;
    els.appPage.hidden = true;
    document.body.classList.add("on-landing");
    document.body.style.overflow = "";
    initParticleCanvas();
    updateNavActive("home");
  }

  window.scrollTo({ top: 0, left: 0, behavior: "auto" });
  refreshIcons();
}

function updateNavActive(current) {
  els.navLinks.forEach((link) => {
    link.classList.toggle("active", link.dataset.nav === current);
  });
}

/* ═══════════════════════════════════════════════
   SCROLL REVEAL OBSERVER
   ═══════════════════════════════════════════════ */

function initScrollReveal() {
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("revealed");
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.1, rootMargin: "0px 0px -40px 0px" },
  );

  document.querySelectorAll(".reveal").forEach((el) => observer.observe(el));
}

/* ═══════════════════════════════════════════════
   PARTICLE CANVAS
   ═══════════════════════════════════════════════ */

function initParticleCanvas() {
  const canvas = els.particleCanvas;
  if (!canvas || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  cancelAnimationFrame(state.particleAnimFrame);

  const heroRect = els.heroSection.getBoundingClientRect();
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  canvas.width = heroRect.width * dpr;
  canvas.height = heroRect.height * dpr;
  canvas.style.width = heroRect.width + "px";
  canvas.style.height = heroRect.height + "px";
  ctx.scale(dpr, dpr);

  const w = heroRect.width;
  const h = heroRect.height;
  const particleCount = Math.min(Math.floor((w * h) / 12000), 80);
  const particles = [];
  const connectionDistance = 120;
  const isDark = () => document.documentElement.dataset.theme === "dark";

  for (let i = 0; i < particleCount; i++) {
    particles.push({
      x: Math.random() * w,
      y: Math.random() * h,
      vx: (Math.random() - 0.5) * 0.5,
      vy: (Math.random() - 0.5) * 0.5,
      radius: Math.random() * 1.5 + 0.8,
    });
  }

  function animate() {
    if (state.currentPage !== "landing") return;
    ctx.clearRect(0, 0, w, h);

    const dark = isDark();
    const dotColor = dark ? "rgba(52, 211, 153, 0.5)" : "rgba(8, 127, 91, 0.35)";
    const lineColor = dark ? "rgba(52, 211, 153, 0.08)" : "rgba(8, 127, 91, 0.06)";

    for (const p of particles) {
      p.x += p.vx;
      p.y += p.vy;

      if (p.x < 0) p.x = w;
      if (p.x > w) p.x = 0;
      if (p.y < 0) p.y = h;
      if (p.y > h) p.y = 0;

      ctx.beginPath();
      ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
      ctx.fillStyle = dotColor;
      ctx.fill();
    }

    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const dx = particles[i].x - particles[j].x;
        const dy = particles[i].y - particles[j].y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < connectionDistance) {
          ctx.beginPath();
          ctx.moveTo(particles[i].x, particles[i].y);
          ctx.lineTo(particles[j].x, particles[j].y);
          ctx.strokeStyle = lineColor;
          ctx.lineWidth = 0.5;
          ctx.stroke();
        }
      }
    }

    state.particleAnimFrame = requestAnimationFrame(animate);
  }

  animate();

  // Resize handler
  const resizeObserver = new ResizeObserver(() => {
    const rect = els.heroSection.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    canvas.style.width = rect.width + "px";
    canvas.style.height = rect.height + "px";
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.scale(dpr, dpr);
  });
  resizeObserver.observe(els.heroSection);
}

/* ═══════════════════════════════════════════════
   SHELL PREFERENCES
   ═══════════════════════════════════════════════ */

function initShellPreferences() {
  const savedRail = localStorage.getItem("rag-rail-collapsed");
  setRailCollapsed(savedRail === "true", { persist: false });

  const savedTab = localStorage.getItem("rag-rail-tab");
  setRailTab(["sources", "documents", "history"].includes(savedTab) ? savedTab : "sources", { persist: false });

  updateShellControls();
}

/* ═══════════════════════════════════════════════
   THEME
   ═══════════════════════════════════════════════ */

function initTheme() {
  const param = new URLSearchParams(location.search).get("theme");
  if (param === "light" || param === "dark") {
    setTheme(param, { persist: false });
    return;
  }
  const saved = localStorage.getItem("rag-theme");
  const current = saved === "light" || saved === "dark" ? saved : document.documentElement.dataset.theme || "dark";
  setTheme(current, { persist: false });
}

function setTheme(theme, options = {}) {
  const nextTheme = theme === "light" ? "light" : "dark";
  state.theme = nextTheme;
  document.documentElement.dataset.theme = nextTheme;
  if (options.persist !== false) {
    localStorage.setItem("rag-theme", nextTheme);
  }
  if (els.themeColor) {
    els.themeColor.setAttribute("content", nextTheme === "dark" ? "#0a0d0b" : "#f5f4f2");
  }
}

function toggleTheme() {
  setTheme(state.theme === "dark" ? "light" : "dark");
  refreshIcons();
}

/* ═══════════════════════════════════════════════
   LAYOUT CONTROLS
   ═══════════════════════════════════════════════ */

function isMobileLayout() {
  return window.matchMedia("(max-width: 780px)").matches;
}

function toggleRail() {
  if (isMobileLayout()) {
    setRailOpen(!state.railOpen);
  } else {
    setRailCollapsed(!state.railCollapsed);
  }
}

function setRailCollapsed(collapsed, options = {}) {
  state.railCollapsed = Boolean(collapsed);
  if (options.persist !== false) {
    localStorage.setItem("rag-rail-collapsed", String(state.railCollapsed));
  }
  updateShellControls();
}

function setRailOpen(open) {
  state.railOpen = Boolean(open);
  document.body.classList.toggle("rail-open", state.railOpen);
  updateShellControls();
}

function setRailTab(tabName, options = {}) {
  const nextTab = ["sources", "documents", "history"].includes(tabName) ? tabName : "sources";
  state.activeRailTab = nextTab;
  els.railTabButtons.forEach((button) => {
    const active = button.dataset.railTab === nextTab;
    button.classList.toggle("active", active);
    button.setAttribute("aria-selected", String(active));
  });
  els.railPanels.forEach((panel) => {
    panel.classList.toggle("active", panel.dataset.railPanel === nextTab);
  });
  if (options.persist !== false) {
    localStorage.setItem("rag-rail-tab", nextTab);
  }
  refreshIcons();
}

function updateShellControls() {
  document.body.classList.toggle("rail-collapsed", state.railCollapsed && !isMobileLayout());

  const railVisible = isMobileLayout() ? state.railOpen : !state.railCollapsed;
  els.railToggle.classList.toggle("active", railVisible);
  els.railToggle.setAttribute("aria-expanded", String(railVisible));
}

/* ═══════════════════════════════════════════════
   REALTIME WEBSOCKET
   ═══════════════════════════════════════════════ */

function connectRealtime() {
  if (!("WebSocket" in window)) {
    setRealtimeStatus("offline", "No WS");
    return;
  }
  clearTimeout(state.realtimeReconnectTimer);
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const socket = new WebSocket(`${protocol}//${window.location.host}/ws/realtime`);
  state.realtimeSocket = socket;
  setRealtimeStatus("connecting", "Connecting");

  socket.addEventListener("open", () => {
    setRealtimeStatus("live", "Live");
  });

  socket.addEventListener("message", (event) => {
    try {
      handleRealtimeEvent(JSON.parse(event.data));
    } catch {
      // Ignore malformed realtime events.
    }
  });

  socket.addEventListener("close", () => {
    if (state.realtimeSocket !== socket) return;
    setRealtimeStatus("offline", "Reconnecting");
    state.realtimeReconnectTimer = setTimeout(connectRealtime, 1800);
  });

  socket.addEventListener("error", () => {
    setRealtimeStatus("offline", "Offline");
  });
}

function setRealtimeStatus(status, label) {
  els.realtimeStatus.classList.toggle("live", status === "live");
  els.realtimeStatus.classList.toggle("offline", status === "offline");
  els.realtimeStatus.querySelector("span:last-child").textContent = label;
}

function handleRealtimeEvent(event) {
  if (!event?.type || event.type === "heartbeat" || event.type === "connected") return;
  pulseElement(els.realtimeStatus);

  if (event.type === "realtime.degraded") {
    setRealtimeStatus("offline", "Paused");
    toast("Realtime paused", event.message || "Realtime updates are temporarily unavailable.", "error");
    return;
  }

  const refreshTargets = Array.isArray(event.refresh) ? event.refresh : [];
  refreshTargets.forEach((target) => state.pendingRealtimeRefresh.add(target));
  scheduleRealtimeRefresh();
  announceRealtimeEvent(event);
}

function scheduleRealtimeRefresh() {
  clearTimeout(state.realtimeRefreshTimer);
  state.realtimeRefreshTimer = setTimeout(async () => {
    const targets = new Set(state.pendingRealtimeRefresh);
    state.pendingRealtimeRefresh.clear();
    const tasks = [];
    if (targets.has("documents")) tasks.push(loadDocuments({ quiet: true }).then(() => pulseElement(els.documents)));
    if (targets.has("sources")) tasks.push(loadSources().then(() => pulseElement(els.sources)));
    if (targets.has("metrics")) tasks.push(loadMetrics().then(() => pulseElement(els.metrics)));
    await Promise.allSettled(tasks);
  }, 180);
}

function announceRealtimeEvent(event) {
  const quietEvents = new Set(["chat.completed", "feedback.stored"]);
  if (quietEvents.has(event.type)) return;
  const messages = {
    "document.uploaded": "Document indexed.",
    "document.deleted": "Document removed.",
    "source.queued": "Source queued for indexing.",
    "source.sync_queued": "Source sync queued.",
    "source.running": "Worker is indexing a source.",
    "source.indexed": "Source indexed.",
    "source.deleted": "Source removed.",
    "job.running": "Worker job started.",
    "job.completed": "Worker job completed.",
    "job.failed": "Worker job failed.",
    "reindex.queued": "Reindex queued.",
  };
  const message = messages[event.type];
  if (!message) return;
  toast("Realtime", message, event.type.includes("failed") ? "error" : "success");
}

function pulseElement(element) {
  if (!element) return;
  element.classList.remove("realtime-updated");
  void element.offsetWidth;
  element.classList.add("realtime-updated");
  setTimeout(() => element.classList.remove("realtime-updated"), 760);
}

/* ═══════════════════════════════════════════════
   DOCUMENT UPLOAD
   ═══════════════════════════════════════════════ */

async function uploadDocument(event) {
  event.preventDefault();
  const file = state.pendingFile || els.fileInput.files[0];
  if (!file) {
    setUploadStatus("Choose a file first.", "error");
    toast("Upload blocked", "Choose a source file first.", "error");
    return;
  }

  const extension = file.name.split(".").pop()?.toLowerCase();
  if (!["pdf", "docx", "txt", "md", "markdown", "zip"].includes(extension)) {
    setUploadStatus("Unsupported file type.", "error");
    toast("Unsupported file", "Use PDF, DOCX, TXT, Markdown, or Notion ZIP.", "error");
    return;
  }

  setUploadStatus("Indexing document...", "");
  const submitButton = els.uploadForm.querySelector("button[type='submit']");
  setButtonBusy(submitButton, true);

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
    toast("Indexed", `${payload.documents?.length || 1} document(s) are ready.`, "success");
    await Promise.all([loadDocuments({ quiet: true }), loadSources(), loadMetrics()]);
    setRailTab("documents");
  } catch (error) {
    setUploadStatus(error.message, "error");
    toast("Upload failed", error.message, "error");
  } finally {
    setButtonBusy(submitButton, false);
  }
}

/* ═══════════════════════════════════════════════
   URL INGESTION
   ═══════════════════════════════════════════════ */

async function ingestUrl(event) {
  event.preventDefault();
  const url = els.sourceUrl.value.trim();
  if (!url) return;

  setUrlStatus("Queueing source...", "");
  const submitButton = els.urlForm.querySelector("button[type='submit']");
  setButtonBusy(submitButton, true);
  try {
    const syncValue = els.sourceSyncInterval.value.trim();
    const body = {
      url,
      mode: els.sourceMode.value,
      max_pages: Number(els.sourceMaxPages.value || 20),
      sync_interval_minutes: syncValue ? Number(syncValue) : null,
    };
    const response = await fetch("/documents/ingest-url", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const payload = await readJson(response);
    els.sourceUrl.value = "";
    setUrlStatus(`Queued job ${payload.queued_job_id.slice(0, 8)}.`, "success");
    toast("Source queued", "The worker will ingest this source.", "success");
    await Promise.all([loadSources(), loadMetrics()]);
  } catch (error) {
    setUrlStatus(error.message, "error");
    toast("URL ingest failed", error.message, "error");
  } finally {
    setButtonBusy(submitButton, false);
    refreshIcons();
  }
}

/* ═══════════════════════════════════════════════
   DOCUMENTS & SOURCES
   ═══════════════════════════════════════════════ */

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

async function loadSources() {
  try {
    const response = await fetch("/sources");
    state.sources = await readJson(response);
    renderSources();
  } catch (error) {
    els.sources.innerHTML = emptyState("database-x", "Sources unavailable", error.message);
  } finally {
    refreshIcons();
  }
}

function renderDocuments() {
  if (!state.documents.length) {
    els.documents.innerHTML = emptyState("folder-open", "No documents", "Corpus is empty.");
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

function renderSources() {
  if (!state.sources.length) {
    els.sources.innerHTML = emptyState("database", "No sources", "Upload or ingest a source.");
    return;
  }
  els.sources.innerHTML = state.sources.map(renderSourceCard).join("");
  els.sources.querySelectorAll("[data-sync-source]").forEach((button) => {
    button.addEventListener("click", () => syncSource(button.dataset.syncSource));
  });
  els.sources.querySelectorAll("[data-delete-source]").forEach((button) => {
    button.addEventListener("click", () => deleteSource(button.dataset.deleteSource));
  });
}

function renderDocumentCard(doc, index) {
  const selected = state.selectedDocumentIds.has(doc.document_id);
  const statusClass = normalizeStatus(doc.status);
  const created = formatDate(doc.created_at);
  return `
    <article class="document-card ${selected ? "selected" : ""} ${statusClass}" style="--i: ${index}">
      <input
        class="document-checkbox"
        type="checkbox"
        ${selected ? "checked" : ""}
        data-select-document="${escapeHtml(doc.document_id)}"
        aria-label="Select ${escapeHtml(doc.filename)}"
      />
      <div class="document-main">
        <strong class="document-title">${escapeHtml(doc.filename)}</strong>
        <span class="document-subline">${escapeHtml(doc.content_type || "document")} | ${created}</span>
        <div class="document-meta">
          <span class="source-pill ${normalizeStatus(doc.source_type)}">${escapeHtml(doc.source_type || "file")}</span>
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

function renderSourceCard(source, index) {
  const type = normalizeStatus(source.source_type);
  const statusClass = normalizeStatus(source.status);
  const lastSync = source.last_synced_at ? formatDate(source.last_synced_at) : "never synced";
  const title = formatSourceLabel(source.name || source.uri || source.source_id);
  const uri = formatSourceLabel(source.uri || "local file");
  return `
    <article class="source-card ${statusClass}" style="--i: ${index}">
      <strong class="source-title">${escapeHtml(title)}</strong>
      <span class="document-subline">${escapeHtml(uri)} | ${lastSync}</span>
      <div class="document-meta">
        <span class="source-pill ${type}">${escapeHtml(source.source_type)}</span>
        <span class="status-pill ${statusClass}">${escapeHtml(source.status)}</span>
        <span class="doc-pill">${source.document_count} docs</span>
        <span class="doc-pill">${source.chunk_count} chunks</span>
      </div>
      ${source.last_error ? `<p class="status-text error">${escapeHtml(source.last_error)}</p>` : ""}
      <div class="source-actions">
        <button class="ghost-button" type="button" data-sync-source="${escapeHtml(source.source_id)}">
          <i data-lucide="refresh-cw"></i>
          <span>Sync</span>
        </button>
        <button class="delete-button" type="button" data-delete-source="${escapeHtml(source.source_id)}">
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
    await Promise.all([loadDocuments({ quiet: true }), loadSources(), loadMetrics()]);
  } catch (error) {
    toast("Delete failed", error.message, "error");
  }
}

async function syncSource(sourceId) {
  try {
    const response = await fetch(`/sources/${sourceId}/sync`, { method: "POST" });
    const payload = await readJson(response);
    toast("Sync queued", `Job ${payload.queued_job_id.slice(0, 8)} is waiting for the worker.`, "success");
    await loadSources();
  } catch (error) {
    toast("Sync failed", error.message, "error");
  }
}

async function deleteSource(sourceId) {
  try {
    const response = await fetch(`/sources/${sourceId}`, { method: "DELETE" });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.detail || "Delete failed.");
    }
    toast("Source deleted", "Source, documents, and vectors were removed.", "success");
    await Promise.all([loadSources(), loadDocuments({ quiet: true }), loadMetrics()]);
  } catch (error) {
    toast("Delete failed", error.message, "error");
  }
}

async function reindexAllSources() {
  setButtonBusy(els.reindexAll, true);
  try {
    const response = await fetch("/reindex", { method: "POST" });
    const payload = await readJson(response);
    toast("Reindex queued", `Job ${payload.queued_job_id.slice(0, 8)} will enqueue all sources.`, "success");
    await loadSources();
  } catch (error) {
    toast("Reindex failed", error.message, "error");
  } finally {
    setButtonBusy(els.reindexAll, false);
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

/* ═══════════════════════════════════════════════
   CHAT
   ═══════════════════════════════════════════════ */

function handleComposerKeydown(event) {
  if (event.key !== "Enter" || event.shiftKey || event.isComposing) return;
  event.preventDefault();
  if (els.chatForm.querySelector("button[type='submit']").disabled) return;
  if (!els.question.value.trim()) return;
  els.chatForm.requestSubmit();
}

async function sendQuestion(event) {
  event.preventDefault();
  const question = els.question.value.trim();
  if (!question) return;

  appendMessage("user", question);
  const loading = appendLoadingMessage();
  els.question.value = "";
  updateCharacterCount();
  const submitButton = els.chatForm.querySelector("button[type='submit']");
  setButtonBusy(submitButton, true);

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
    saveChatHistory({ question, payload });
    await loadMetrics();
  } catch (error) {
    loading.remove();
    appendMessage("assistant", error.message, { noAnswer: true });
    toast("Chat failed", error.message, "error");
  } finally {
    setButtonBusy(submitButton, false);
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
      <div class="message-content plain-content">
        <span class="thinking-line">
          <span>Retrieving evidence</span>
          <span class="thinking-dot" style="--delay: 0ms"></span>
          <span class="thinking-dot" style="--delay: 120ms"></span>
          <span class="thinking-dot" style="--delay: 240ms"></span>
        </span>
      </div>
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

/* ═══════════════════════════════════════════════
   EVIDENCE
   ═══════════════════════════════════════════════ */

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

function renderCitationCard(citation, index) {
  return `
    <article class="citation-card" style="--i: ${index}">
      <strong class="citation-title">${escapeHtml(citation.citation_id)} | ${escapeHtml(citation.source_title || citation.filename)}</strong>
      <div class="citation-meta">
        ${citation.source_type ? `<span class="source-pill ${normalizeStatus(citation.source_type)}">${escapeHtml(citation.source_type)}</span>` : ""}
        <span class="doc-pill">Page ${escapeHtml(citation.page || "unknown")}</span>
        <span class="score-pill">Score ${Number(citation.score || 0).toFixed(4)}</span>
      </div>
      ${citation.source_url ? `<span class="document-subline">${escapeHtml(citation.source_url)}</span>` : ""}
      ${citation.source_path && !citation.source_url ? `<span class="document-subline">${escapeHtml(citation.source_path)}</span>` : ""}
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
        <article class="trace-card" style="--i: ${index}">
          <strong class="citation-title">Rank ${index + 1} | ${escapeHtml(item.metadata?.source_title || item.filename || "Unknown file")}</strong>
          <div class="citation-meta">
            ${item.metadata?.source_type ? `<span class="source-pill ${normalizeStatus(item.metadata.source_type)}">${escapeHtml(item.metadata.source_type)}</span>` : ""}
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
    <strong>${citationCount} citations - ${traceCount} trace items</strong>
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

/* ═══════════════════════════════════════════════
   METRICS
   ═══════════════════════════════════════════════ */

async function loadMetrics() {
  try {
    const response = await fetch("/metrics");
    const metrics = await readJson(response);
    els.metrics.innerHTML = `
      ${metricCard("Sources", metrics.sources || 0)}
      ${metricCard("Documents", metrics.documents)}
      ${metricCard("Chunks", metrics.chunks)}
      ${metricCard("Latency", `${metrics.avg_chat_latency_ms} ms`)}
    `;
    animateCounters();
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
      <strong data-counter-target="${value}">${value}</strong>
    </article>
  `;
}

function animateCounters() {
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

  document.querySelectorAll("[data-counter-target]").forEach((el) => {
    const raw = el.dataset.counterTarget;
    const target = parseInt(raw, 10);
    if (isNaN(target) || target <= 0) return;

    const suffix = raw.replace(String(target), "");
    const duration = 600;
    const start = performance.now();
    let current = 0;

    function step(now) {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      current = Math.round(eased * target);
      el.textContent = current + suffix;
      if (progress < 1) requestAnimationFrame(step);
    }

    requestAnimationFrame(step);
  });
}

/* ═══════════════════════════════════════════════
   CHAT HISTORY
   ═══════════════════════════════════════════════ */

function loadChatHistory() {
  try {
    const saved = JSON.parse(localStorage.getItem("rag-chat-history") || "[]");
    state.chatHistory = Array.isArray(saved) ? saved.slice(0, 30) : [];
  } catch {
    state.chatHistory = [];
  }
}

function saveChatHistory({ question, payload }) {
  const record = {
    id: payload.chat_id || randomId(),
    chat_id: payload.chat_id || null,
    question,
    answer: payload.answer,
    no_answer: Boolean(payload.no_answer),
    created_at: new Date().toISOString(),
    payload,
  };
  state.chatHistory = [record, ...state.chatHistory.filter((item) => item.id !== record.id)].slice(0, 30);
  persistChatHistory();
  renderChatHistory();
}

function persistChatHistory() {
  localStorage.setItem("rag-chat-history", JSON.stringify(state.chatHistory));
}

function renderChatHistory() {
  if (!state.chatHistory.length) {
    els.historyList.innerHTML = emptyState("history", "No saved chats", "Completed answers will appear here.");
    refreshIcons();
    return;
  }
  els.historyList.innerHTML = state.chatHistory.map(renderHistoryCard).join("");
  els.historyList.querySelectorAll("[data-load-history]").forEach((button) => {
    button.addEventListener("click", () => restoreChatHistory(button.dataset.loadHistory));
  });
  refreshIcons();
}

function renderHistoryCard(item, index) {
  const citationCount = item.payload?.citations?.length || 0;
  const label = item.no_answer ? "No answer" : `${citationCount} citations`;
  return `
    <button class="history-card" type="button" data-load-history="${escapeHtml(item.id)}" style="--i: ${index}">
      <strong>${escapeHtml(item.question)}</strong>
      <span>${escapeHtml(formatDate(item.created_at))} | ${escapeHtml(label)}</span>
    </button>
  `;
}

function restoreChatHistory(historyId) {
  const item = state.chatHistory.find((record) => record.id === historyId);
  if (!item) return;
  state.lastChatId = item.chat_id;
  els.messages.innerHTML = "";
  appendMessage("user", item.question);
  appendMessage("assistant", item.answer, {
    noAnswer: item.no_answer,
    payload: item.payload,
  });
  renderEvidence(item.payload || {});
  setRailTab("history");
  closeEvidence();
}

function clearChatHistory() {
  state.chatHistory = [];
  persistChatHistory();
  renderChatHistory();
  toast("History cleared", "Local chat history was removed.", "success");
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

/* ═══════════════════════════════════════════════
   UI HELPERS
   ═══════════════════════════════════════════════ */

function handleFilePick() {
  state.pendingFile = null;
  const file = els.fileInput.files[0];
  setUploadStatus(file ? `${file.name} selected` : "Ready", file ? "success" : "");
}

function setUploadStatus(message, kind) {
  els.uploadStatus.textContent = message;
  els.uploadStatus.className = `status-text ${kind || ""}`.trim();
}

function setUrlStatus(message, kind) {
  els.urlStatus.textContent = message;
  els.urlStatus.className = `status-text ${kind || ""}`.trim();
}

function setButtonBusy(button, isBusy) {
  if (!button) return;
  button.disabled = Boolean(isBusy);
  button.classList.toggle("is-busy", Boolean(isBusy));
  button.setAttribute("aria-busy", String(Boolean(isBusy)));
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
    els.evidenceToggleMeta.textContent = `${traceCount} trace - ${latency || 0} ms`;
  } else {
    els.evidenceToggleMeta.textContent = "View evidence";
  }
}

function openEvidence() {
  if (state.evidenceCloseTimer) {
    clearTimeout(state.evidenceCloseTimer);
    state.evidenceCloseTimer = null;
  }
  els.evidenceDrawer.classList.remove("closing");
  els.evidenceDrawer.hidden = false;
  els.evidenceDrawer.setAttribute("aria-hidden", "false");
  document.body.classList.add("drawer-open");
  requestAnimationFrame(() => {
    els.closeEvidence.focus();
  });
}

function closeEvidence() {
  if (els.evidenceDrawer.hidden) return;
  els.evidenceDrawer.classList.add("closing");
  els.evidenceDrawer.setAttribute("aria-hidden", "true");
  document.body.classList.remove("drawer-open");
  state.evidenceCloseTimer = setTimeout(() => {
    els.evidenceDrawer.hidden = true;
    els.evidenceDrawer.classList.remove("closing");
    state.evidenceCloseTimer = null;
  }, 240);
}

/* ═══════════════════════════════════════════════
   SKELETONS & EMPTY STATES
   ═══════════════════════════════════════════════ */

function renderMetricSkeleton() {
  els.metrics.innerHTML = `
    ${metricCard("Sources", "--")}
    ${metricCard("Documents", "--")}
    ${metricCard("Chunks", "--")}
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

function renderSourceSkeleton() {
  els.sources.innerHTML = `
    <article class="source-card loading-card">
      <strong class="source-title">Loading sources</strong>
      <span class="document-subline">Refreshing sync dashboard</span>
      <div class="document-meta">
        <span class="doc-pill">--</span>
        <span class="doc-pill">--</span>
      </div>
    </article>
  `;
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

/* ═══════════════════════════════════════════════
   TOAST NOTIFICATIONS
   ═══════════════════════════════════════════════ */

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
  setTimeout(() => {
    node.classList.add("leaving");
    setTimeout(() => node.remove(), 170);
  }, 4200);
}

/* ═══════════════════════════════════════════════
   UTILITIES
   ═══════════════════════════════════════════════ */

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

function formatSourceLabel(value) {
  const raw = String(value || "");
  try {
    const url = new URL(raw);
    const path = decodeURIComponent(url.pathname).split("/").filter(Boolean).join(" / ");
    return path ? `${url.hostname} ${path}` : url.hostname;
  } catch {
    try {
      return decodeURIComponent(raw);
    } catch {
      return raw;
    }
  }
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

function randomId() {
  if (window.crypto?.randomUUID) {
    return window.crypto.randomUUID();
  }
  return `local-${Date.now()}-${Math.random().toString(16).slice(2)}`;
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
