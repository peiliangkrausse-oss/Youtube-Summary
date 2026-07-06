const api = {
  models: "/api/models",
  modelLoad: "/api/models/load",
  modelUnload: "/api/models/unload",
  prompt: "/api/prompt",
  promptReset: "/api/prompt/reset",
  promptPresets: "/api/prompt/presets",
  videoMetadata: "/api/videos/metadata",
  donation: "/api/support/donation",
  chat: "/api/chat",
  chatStream: "/api/chat/stream",
  animeNarration: "/api/narration/anime",
  animeNarrationStream: "/api/narration/anime/stream",
  animeVoice: "/api/narration/anime/voice",
  elevenLabsVoices: "/api/narration/elevenlabs/voices",
  localVoiceNarration: "/api/narration/local",
  localVoiceStatus: "/api/narration/local/status",
  localVoiceCatalog: "/api/narration/local/catalog",
  localVoiceDownload: "/api/narration/local/download",
  jobs: "/api/jobs",
  history: "/api/history"
};

const layout = document.getElementById("layout");
const sidebar = document.getElementById("sidebar");
const sidebarContent = document.getElementById("sidebarContent");
const content = document.querySelector(".content");
const resizer = document.getElementById("resizer");
const sidebarRailActions = [...document.querySelectorAll("[data-sidebar-target]")];
const sidebarSections = [...document.querySelectorAll("[data-sidebar-section]")];
const chatResizer = document.getElementById("chatResizer");
const sidebarToggleBtn = document.getElementById("sidebarToggleBtn");
const summaryPanel = document.getElementById("summaryPanel");
const summary = document.getElementById("summary");
const status = document.getElementById("status");
const summarizeBtn = document.getElementById("summarizeBtn");
const copyBtn = document.getElementById("copyBtn");
const guideBtn = document.getElementById("guideBtn");
const speakBtn = document.getElementById("speakBtn");
const voiceSettingsBtn = document.getElementById("voiceSettingsBtn");
const animeVoiceFileInput = document.getElementById("animeVoiceFileInput");
const chatBtn = document.getElementById("chatBtn");
const chatPanel = document.getElementById("chatPanel");
const chatCloseBtn = document.getElementById("chatCloseBtn");
const chatMessages = document.getElementById("chatMessages");
const chatForm = document.getElementById("chatForm");
const chatInput = document.getElementById("chatInput");
const chatSendBtn = document.getElementById("chatSendBtn");
const chatSubtitle = document.getElementById("chatSubtitle");
const chatFileBtn = document.getElementById("chatFileBtn");
const chatImageBtn = document.getElementById("chatImageBtn");
const chatFileInput = document.getElementById("chatFileInput");
const chatImageInput = document.getElementById("chatImageInput");
const donationBtn = document.getElementById("donationBtn");
const feedbackEmailBtn = document.getElementById("feedbackEmailBtn");
const zoomInBtn = document.getElementById("zoomInBtn");
const zoomOutBtn = document.getElementById("zoomOutBtn");
const toast = document.getElementById("toast");
const providerSelect = document.getElementById("provider");
const modelSelect = document.getElementById("model");
const lmStudioPortInput = document.getElementById("lmStudioPort");
const testConnectionBtn = document.getElementById("testConnectionBtn");
const modelStatus = document.getElementById("modelStatus");
const loadModelBtn = document.getElementById("loadModelBtn");
const unloadModelBtn = document.getElementById("unloadModelBtn");
const advancedHint = document.getElementById("advancedHint");
const promptEditor = document.getElementById("promptEditor");
const promptStatus = document.getElementById("promptStatus");
const viewPresetsBtn = document.getElementById("viewPresetsBtn");
const presetDrawer = document.getElementById("presetDrawer");
const presetNameInput = document.getElementById("presetNameInput");
const savePresetBtn = document.getElementById("savePresetBtn");
const presetList = document.getElementById("presetList");
const chromeTabs = document.getElementById("chromeTabs");
const newTabBtn = document.getElementById("newTabBtn");
const queueList = document.getElementById("queueList");
const progressTrack = document.getElementById("progressTrack");
const progressFill = document.getElementById("progressFill");
const narrationProgress = document.getElementById("narrationProgress");
const narrationProgressText = document.getElementById("narrationProgressText");
const narrationProgressFill = document.getElementById("narrationProgressFill");
const summaryTitleText = document.getElementById("summaryTitleText");
const urlInput = document.getElementById("url");

const state = {
  tabs: [],
  activeTabId: "",
  jobs: new Map(),
  pollTimer: null,
  progressTimer: null,
  modelInventory: null,
  provider: "lm_studio",
  promptPresets: [],
  activePromptPresetId: "",
  chatHistory: new Map(),
  closedTabs: [],
  voiceStatus: null,
  localVoiceStatus: null,
  localVoiceCatalog: [],
  localVoiceModels: []
};
state.defaultPrompt = "";

const attachedFiles = [];
const moduleState = {
  readEventStream: null,
  formatFileLabel: null,
  text: null,
  guideHtml: null
};

let dragging = false;
let chatDragging = false;
let speechActive = false;
let activeNarrationAudio = null;
let activeNarrationAudioUrl = "";
let activeNarrationController = null;
let narrationProgressTimer = null;
let localVoiceWarmupTimer = null;
let localVoiceWarmupPromise = null;
let warmedLocalVoiceKey = "";
let warmingLocalVoiceKey = "";
const allowedAnimeVoiceExtensions = [".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".webm"];
const animeVoiceFileTypeMessage = "Upload an audio file in one of these formats: MP3, WAV, M4A, AAC, FLAC, OGG, or WEBM.";
const defaultLocalVoiceServer = "http://127.0.0.1:5000";
let summaryZoom = Number(localStorage.getItem("ytSummaryZoom")) || 1;
let appZoom = Number(localStorage.getItem("ytAppZoom")) || 1;
let sidebarWidth = Number(localStorage.getItem("ytSidebarWidth")) || 420;
let sidebarCollapsed = localStorage.getItem("ytSidebarCollapsed") === "1";
let sidebarActiveSection = localStorage.getItem("ytSidebarActiveSection") || "";
let chatWidth = Number(localStorage.getItem("ytChatWidth")) || 448;

function constrainedSidebarWidth(value = sidebarWidth) {
  const viewportWidth = window.innerWidth || 1280;
  const maxWidth = Math.max(420, Math.min(620, viewportWidth - 640));
  return Math.max(420, Math.min(maxWidth, Number(value) || 420));
}

function constrainedChatWidth(value = chatWidth) {
  const viewportWidth = window.innerWidth || 1280;
  const maxWidth = Math.max(360, Math.min(720, viewportWidth - 520));
  return Math.max(320, Math.min(maxWidth, Number(value) || 448));
}

function uid(prefix) {
  return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`;
}

function activeTab() {
  return state.tabs.find((tab) => tab.id === state.activeTabId) || state.tabs[0];
}

function applyZoom() {
  document.documentElement.style.setProperty("--summary-zoom", summaryZoom.toFixed(2));
  localStorage.setItem("ytSummaryZoom", summaryZoom.toFixed(2));
  const zoomLabel = `${Math.round(summaryZoom * 100)}%`;
  if (zoomInBtn) zoomInBtn.title = `Zoom in (${zoomLabel})`;
  if (zoomOutBtn) zoomOutBtn.title = `Zoom out (${zoomLabel})`;
}

function applyAppZoom() {
  appZoom = Math.max(.86, Math.min(1.22, appZoom || 1));
  document.documentElement.style.setProperty("--app-zoom", appZoom.toFixed(2));
  localStorage.setItem("ytAppZoom", appZoom.toFixed(2));
}

function setAppZoom(nextZoom) {
  appZoom = Math.max(.86, Math.min(1.22, nextZoom));
  applyAppZoom();
  showToast(`Zoom ${Math.round(appZoom * 100)}%`);
}

function applySidebarLayout() {
  if (window.innerWidth <= 1150) {
    layout.classList.remove("sidebar-collapsed");
    layout.classList.remove("sidebar-section-open");
    layout.style.gridTemplateColumns = "1fr";
    layout.style.removeProperty("--sidebar-grid-columns");
    if (content) content.style.gridColumn = "";
    if (sidebar) sidebar.hidden = false;
    if (resizer) resizer.hidden = true;
    if (sidebarToggleBtn) {
      sidebarToggleBtn.setAttribute("aria-label", "Collapse sidebar");
      sidebarToggleBtn.title = "Collapse sidebar";
    }
    return;
  }
  sidebarWidth = constrainedSidebarWidth();
  if (sidebarActiveSection && !sidebarSections.some((section) => section.dataset.sidebarSection === sidebarActiveSection)) {
    setSidebarActiveSection("", { apply: false });
  }
  layout.classList.toggle("sidebar-collapsed", sidebarCollapsed);
  const hasSectionPanel = sidebarCollapsed && Boolean(sidebarActiveSection);
  layout.classList.toggle("sidebar-section-open", hasSectionPanel);
  if (sidebar) {
    sidebar.hidden = false;
    sidebar.dataset.activeSection = hasSectionPanel ? sidebarActiveSection : "";
  }
  if (resizer) resizer.hidden = sidebarCollapsed;
  const gridColumns = sidebarCollapsed
    ? `${hasSectionPanel ? sidebarWidth : 74}px 0 minmax(0,1fr)`
    : `${sidebarWidth}px .22rem minmax(0,1fr)`;
  layout.style.gridTemplateColumns = gridColumns;
  layout.style.setProperty("--sidebar-grid-columns", gridColumns);
  if (content) content.style.gridColumn = sidebarCollapsed ? "3" : "";
  if (sidebarToggleBtn) {
    const actionLabel = sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar";
    sidebarToggleBtn.setAttribute("aria-label", actionLabel);
    sidebarToggleBtn.title = actionLabel;
  }
  applySidebarSections();
}

function setSidebarCollapsed(nextValue) {
  sidebarCollapsed = Boolean(nextValue);
  if (!sidebarCollapsed) setSidebarActiveSection("", { apply: false });
  localStorage.setItem("ytSidebarCollapsed", sidebarCollapsed ? "1" : "0");
  applySidebarLayout();
}

function toggleSidebar() {
  setSidebarCollapsed(!sidebarCollapsed);
}

function setSidebarActiveSection(section, { apply = true } = {}) {
  sidebarActiveSection = section || "";
  if (sidebarActiveSection) localStorage.setItem("ytSidebarActiveSection", sidebarActiveSection);
  else localStorage.removeItem("ytSidebarActiveSection");
  if (apply) applySidebarLayout();
}

function openSidebarSection(section) {
  sidebarCollapsed = true;
  localStorage.setItem("ytSidebarCollapsed", "1");
  setSidebarActiveSection(sidebarActiveSection === section ? "" : section);
}

function applySidebarSections() {
  const hasActiveSection = sidebarCollapsed && Boolean(sidebarActiveSection);
  sidebarRailActions.forEach((button) => {
    button.classList.toggle("is-active", hasActiveSection && button.dataset.sidebarTarget === sidebarActiveSection);
  });
  sidebarSections.forEach((section) => {
    section.classList.toggle("is-selected", hasActiveSection && section.dataset.sidebarSection === sidebarActiveSection);
  });
  const advanced = document.getElementById("advanced");
  const promptSection = document.getElementById("promptPresetSection");
  if (hasActiveSection && ["model", "prompt", "queue"].includes(sidebarActiveSection) && advanced) advanced.open = true;
  if (hasActiveSection && sidebarActiveSection === "prompt" && promptSection) promptSection.open = true;
  if (hasActiveSection && sidebarContent) sidebarContent.scrollTop = 0;
}

function applyChatLayout() {
  chatWidth = constrainedChatWidth();
  content.style.setProperty("--chat-width", `${chatWidth}px`);
}

function showToast(message) {
  toast.textContent = message;
  toast.classList.add("show");
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => toast.classList.remove("show"), 1500);
}

function setButtonLabel(btn, label) {
  const span = btn.querySelector("span");
  if (span) span.textContent = label;
}

function playFinishAnimation() {
  summaryPanel.classList.remove("finish-flash");
  void summaryPanel.offsetWidth;
  summaryPanel.classList.add("finish-flash");
  clearTimeout(playFinishAnimation.timer);
  playFinishAnimation.timer = setTimeout(() => summaryPanel.classList.remove("finish-flash"), 1200);
}

async function requestJson(url, options = {}) {
  let response;
  try {
    response = await fetch(url, {
      headers: { "Content-Type": "application/json" },
      ...options
    });
  } catch (error) {
    const friendly = new Error(
      window.location.protocol === "file:"
        ? "WatchLess is open as a file instead of through its local app server. Close this window and reopen WatchLess from the app launcher."
        : "WatchLess could not reach its own local app server. Close every WatchLess window, reopen the app from the WatchLess folder, then try again."
    );
    friendly.errorType = "watchless_backend_unreachable";
    friendly.cause = error;
    throw friendly;
  }
  const data = await response.json().catch(() => ({}));
  if (!response.ok || data.ok === false) {
    const error = new Error(data.error || `Request failed: ${response.status}`);
    error.errorType = data.error_type || "request_error";
    throw error;
  }
  return data;
}

async function loadFrontendModules() {
  const [streamModule, fileModule, textModule, guideModule] = await Promise.all([
    import("/static/js/modules/stream_reader.js"),
    import("/static/js/modules/files.js"),
    import("/static/js/modules/text.js"),
    import("/static/js/modules/guide.js")
  ]);
  moduleState.readEventStream = streamModule.readEventStream;
  moduleState.formatFileLabel = fileModule.formatFileLabel;
  moduleState.text = textModule;
  moduleState.guideHtml = guideModule.guideHtml;
}

function escapeHtml(value) {
  if (moduleState.text) return moduleState.text.escapeHtml(value);
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function cleanElevenLabsApiKey(value = "") {
  return String(value)
    .replace(/[\u200B-\u200D\uFEFF]/g, "")
    .trim()
    .replace(/^["']|["']$/g, "")
    .replace(/^xi-api-key\s*:\s*/i, "")
    .replace(/^bearer\s+/i, "")
    .trim()
    .replace(/^["']|["']$/g, "");
}

function markdownToHtml(markdown) {
  if (moduleState.text) return moduleState.text.markdownToHtml(markdown);
  if (window.marked) return marked.parse(escapeHtml(markdown || ""));
  return `<pre>${escapeHtml(markdown)}</pre>`;
}

function cleanSummaryText(markdown = "") {
  if (moduleState.text) return moduleState.text.cleanSummaryText(markdown);
  return String(markdown || "")
    .replace(/^Source:\s+\S+\s*/gim, "")
    .replace(/^Model:\s+.+\s*/gim, "")
    .trim();
}

function plainNarrationText(markdown = "") {
  return cleanSummaryText(markdown)
    .replace(/```[\s\S]*?```/g, " ")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/!\[[^\]]*]\([^)]*\)/g, " ")
    .replace(/\[([^\]]+)]\([^)]*\)/g, "$1")
    .replace(/^#{1,6}\s+/gm, "")
    .replace(/^\s*[-*+]\s+/gm, "")
    .replace(/^\s*\d+\.\s+/gm, "")
    .replace(/[>*_~#]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function summaryMarkdownWithTitle(title = "", markdown = "") {
  const cleaned = cleanSummaryText(markdown);
  const safeTitle = String(title || "").trim();
  if (!cleaned || !safeTitle) return cleaned;
  if (/^#\s+.+/m.test(cleaned)) return cleaned;
  return `# ${safeTitle}\n\n${cleaned}`;
}

function chatContentHtml(markdown = "") {
  if (moduleState.text) return moduleState.text.chatMarkdownToHtml(markdown);
  return escapeHtml(markdown).replaceAll("\n", "<br>");
}

function chatKeyForTab(tab = activeTab()) {
  return tab?.historyId || "";
}

function selectedModelSupportsUploads() {
  const selected = modelSelect.value;
  const models = state.modelInventory?.models || [];
  const model = models.find((item) => item.key === selected) || {};
  const label = `${selected} ${model.display_name || ""}`.toLowerCase();
  return /\b(vl|vision|visual|llava|bakllava|moondream|pixtral|qwen2-vl|qwen-vl|gemma-3|gemma 3|oss|gpt-oss)\b/.test(label);
}

function updateChatUploadControls() {
  const enabled = selectedModelSupportsUploads();
  chatFileBtn.disabled = !enabled;
  chatImageBtn.disabled = true;
  chatFileBtn.title = enabled ? "Attach a readable file" : "File upload unavailable for this model";
  chatImageBtn.title = "Image upload is not supported yet";
}

function setZoom(nextZoom) {
  summaryZoom = Math.max(.82, Math.min(1.55, nextZoom));
  applyZoom();
}

function parseUrls(value = urlInput.value) {
  const matches = value.match(/https?:\/\/[^\s,]+/g) || [];
  return [...new Set(matches.map((url) => url.trim()))];
}

function titleFromUrl(url) {
  try {
    const parsed = new URL(url);
    const id = parsed.searchParams.get("v") || parsed.pathname.split("/").filter(Boolean).pop();
    return id ? `Resolving title for ${id}` : "New Summary";
  } catch {
    return "New Summary";
  }
}

async function fetchVideoMetadata(urls) {
  try {
    const data = await requestJson(api.videoMetadata, {
      method: "POST",
      body: JSON.stringify({ urls })
    });
    const titleMap = {};
    for (const item of data.items || []) {
      if (item.url && item.title) titleMap[item.url] = item.title;
    }
    return titleMap;
  } catch {
    return {};
  }
}

function setProgress(percent, visible) {
  progressTrack.hidden = !visible;
  progressFill.style.width = `${Math.max(0, Math.min(100, Number(percent) || 0))}%`;
}

function setNarrationProgress(percent, label = "") {
  if (!narrationProgress || !narrationProgressFill) return;
  narrationProgress.hidden = false;
  narrationProgressFill.style.width = `${Math.max(0, Math.min(100, Number(percent) || 0))}%`;
  if (narrationProgressText && label) narrationProgressText.textContent = label;
}

function startNarrationProgress({ service = "local voice", connectingLabel = "", preparingLabel = "" } = {}) {
  clearInterval(narrationProgressTimer);
  const startedAt = Date.now();
  const serviceLabel = service || "local voice";
  setNarrationProgress(8, connectingLabel || `Connecting to ${serviceLabel}...`);
  narrationProgressTimer = setInterval(() => {
    const elapsed = (Date.now() - startedAt) / 1000;
    const percent = Math.min(92, 8 + elapsed * 7);
    const secondsLeft = Math.max(1, Math.ceil((92 - percent) / 7));
    setNarrationProgress(percent, `${preparingLabel || `Preparing ${serviceLabel}`}... about ${secondsLeft}s`);
  }, 450);
}

function finishNarrationProgress(label = "Voice ready") {
  clearInterval(narrationProgressTimer);
  setNarrationProgress(100, label);
  setTimeout(() => {
    if (narrationProgress) narrationProgress.hidden = true;
  }, 650);
}

function stopNarrationProgress() {
  clearInterval(narrationProgressTimer);
  if (narrationProgress) narrationProgress.hidden = true;
}

function visibleProgress(tab) {
  if (!tab) return 0;
  const raw = Number(tab.progress) || 0;
  return raw;
}

function progressMeta(tab) {
  if (!tab) return "";
  const statusName = tab.jobStatus || tab.status;
  const pieces = [];
  if (statusName === "queued") pieces.push("Queued");
  if (statusName === "running") pieces.push(tab.statusText || tab.message || "Generating summary");
  if (statusName === "succeeded") pieces.push("Done");
  if (statusName === "failed") pieces.push("Failed");
  if (tab.tokensPerSecond || tab.tokens_per_second) pieces.push(`${tab.tokensPerSecond || tab.tokens_per_second} tok/s`);
  return pieces.join(" · ");
}

function updateProgressViews() {
  const tab = activeTab();
  const show = tab && ["queued", "running"].includes(tab.jobStatus);
  if (show) {
    const percent = visibleProgress(tab);
    setProgress(percent, true);
    const loadingBar = summary.querySelector(".summary-loading__bar span");
    const loadingPercent = summary.querySelector(".summary-loading__top span");
    const loadingMeta = summary.querySelector(".summary-loading__meta");
    if (loadingBar) loadingBar.style.width = `${Math.max(5, Math.min(100, percent))}%`;
    if (loadingPercent) loadingPercent.textContent = `${Math.round(percent)}%`;
    if (loadingMeta) loadingMeta.textContent = progressMeta(tab) || "Queued";
  } else {
    setProgress(0, false);
  }
  chromeTabs.querySelectorAll("[data-tab-id]").forEach((button) => {
    const item = state.tabs.find((candidate) => candidate.id === button.dataset.tabId);
    const bar = button.querySelector(".tab-progress span");
    if (item && bar) bar.style.width = `${Math.max(4, Math.min(100, visibleProgress(item)))}%`;
  });
}

function startProgressTicker() {
  updateProgressViews();
}

function guideHtml() {
  if (moduleState.guideHtml) return moduleState.guideHtml();
  return `<div class="setup-guide"><div class="hero"><h2>WatchLess Setup</h2><p>Guide content is loading.</p></div></div>`;
}

function emptyHtml(message) {
  return `<div class="empty"><svg viewBox="0 0 24 24" fill="none"><path d="M8 5.5v13l10-6.5-10-6.5Z" fill="currentColor"/><path d="M4 5h1M4 12h1M4 19h1" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg><div>${escapeHtml(message)}</div></div>`;
}

function loadingHtml(tab) {
  const percent = visibleProgress(tab);
  return `
    <div class="summary-loading">
      <div class="summary-loading__top">
        <strong>${escapeHtml(tab.title || "Preparing summary")}</strong>
        <span>${Math.round(percent)}%</span>
      </div>
      <div class="summary-loading__bar"><span style="width:${Math.max(5, Math.min(100, percent))}%"></span></div>
      <div class="summary-loading__meta">${escapeHtml(progressMeta(tab) || "Queued")}</div>
    </div>`;
}

function normalizedErrorType(type, message = "") {
  const rawType = type || "";
  const lower = String(message || "").toLowerCase();
  if (rawType) return rawType;
  if (lower.includes("too long") || lower.includes("timeout")) return "model_timeout";
  if (lower.includes("cannot connect") || lower.includes("not connected")) return "model_disconnected";
  if (lower.includes("ram") || lower.includes("memory") || lower.includes("could not run")) return "model_memory";
  if (lower.includes("empty summary")) return "empty_summary";
  return "app_error";
}

function errorGuidance(type, message = "") {
  const providerLabel = state.provider === "ollama" ? "Ollama" : "LM Studio";
  const normalized = normalizedErrorType(type, message);
  const commonTimeout = [
    `The selected model is too heavy for this computer right now. Use a smaller or more compressed model.`,
    "The video transcript was still too large for the selected local model to read quickly.",
    `${providerLabel} is busy, stalled, or still warming up the model. Restart the local server and try again.`,
    "Other apps are using too much memory or processor power. Close heavy apps before running the summary."
  ];
  const guidance = {
    model_timeout: {
      title: `${providerLabel} took too long to answer.`,
      causes: commonTimeout,
      fix: "Fastest fix: try again so WatchLess can process the video in smaller parts, or use a smaller model if it still fails."
    },
    model_memory: {
      title: `${providerLabel} model or memory issue.`,
      causes: [
        "The selected model does not fit comfortably in your RAM or VRAM.",
        "More than one large model is loaded at the same time.",
        "The model format or quantization is not supported well by the current local server."
      ],
      fix: "Fastest fix: unload extra models and pick a smaller quantized model."
    },
    model_disconnected: {
      title: `${providerLabel} is not connected.`,
      causes: [
        `${providerLabel} is closed or its local server is turned off.`,
        "The port number is wrong. LM Studio commonly uses 1234.",
        "Another app is using the same port."
      ],
      fix: `Fastest fix: open ${providerLabel}, start its local server, then press Test Connection.`
    },
    empty_summary: {
      title: "The model returned an empty summary.",
      causes: [
        "The model stopped before producing text.",
        "The transcript was empty or too messy to summarize.",
        "The selected model struggled with the prompt."
      ],
      fix: "Fastest fix: try again with a smaller model or a different video."
    },
    missing_url: {
      title: "No YouTube URL was entered.",
      causes: ["The URL box is empty.", "The pasted text did not contain a readable YouTube link."],
      fix: "Paste one YouTube link per line and try again."
    }
  };
  return guidance[normalized] || {
    title: "Something needs attention.",
    causes: [
      "The local model server returned an unexpected error.",
      "The app could not finish one step of the summary.",
      "The video, transcript, or selected model may need a retry."
    ],
    fix: "Fastest fix: try again once, then test the model connection if it repeats."
  };
}

function errorHtml(message, type = "") {
  const guidance = errorGuidance(type, message);
  return `
    <div class="error-card error-card--with-help">
      <strong>${escapeHtml(guidance.title)}</strong>
      <p>${escapeHtml(message || guidance.title)}</p>
      <div class="error-help">
        <span>Most likely causes, ranked:</span>
        <ol>${guidance.causes.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ol>
        <p>${escapeHtml(guidance.fix)}</p>
      </div>
    </div>`;
}

function createTab({ title = "New Summary", type = "draft", url = "", markdown = "", statusText = "", jobId = "", historyId = "", activate = true } = {}) {
  const tab = {
    id: uid("tab"),
    title,
    type,
    url,
    markdown,
    statusText,
    jobId,
    historyId,
    progress: 0,
    jobStatus: "",
    startedAt: 0,
    tokensPerSecond: null,
    completionTokens: null,
    elapsedSeconds: null,
    error: "",
    errorType: ""
  };
  state.tabs.push(tab);
  if (activate) activateTab(tab.id);
  renderTabs();
  return tab;
}

function restorableTab(tab) {
  return {
    ...tab,
    id: uid("tab"),
    jobStatus: ["queued", "running"].includes(tab.jobStatus) ? "" : tab.jobStatus,
    jobId: ["queued", "running"].includes(tab.jobStatus) ? "" : tab.jobId,
    statusText: ["queued", "running"].includes(tab.jobStatus) ? "Restored closed tab." : tab.statusText,
    startedAt: 0
  };
}

function rememberClosedTab(tab) {
  if (!tab) return;
  state.closedTabs.push(restorableTab(tab));
  state.closedTabs = state.closedTabs.slice(-10);
}

function reopenClosedTab() {
  const restored = state.closedTabs.pop();
  if (!restored) {
    showToast("No closed tab to reopen");
    return;
  }
  const activeIndex = state.tabs.findIndex((tab) => tab.id === state.activeTabId);
  const insertAt = activeIndex === -1 ? state.tabs.length : activeIndex + 1;
  state.tabs.splice(insertAt, 0, restored);
  activateTab(restored.id);
  showToast("Tab reopened");
}

function createGuideTab() {
  const existing = state.tabs.find((tab) => tab.type === "guide");
  if (existing) {
    activateTab(existing.id);
    return existing;
  }
  return createTab({ title: "WatchLess Setup", type: "guide" });
}

function createVoiceSettingsTab() {
  ensureLocalVoiceCatalog().then(() => {
    if (activeTab()?.type === "voice-settings") refreshVoiceSettingsTab();
  });
  const existing = state.tabs.find((tab) => tab.type === "voice-settings");
  if (existing) {
    activateTab(existing.id);
    return existing;
  }
  return createTab({ title: "Voice Settings", type: "voice-settings" });
}

function scrollActiveTabIntoView() {
  chromeTabs.querySelector(".chrome-tab.is-active")?.scrollIntoView({ block: "nearest", inline: "nearest" });
}

function normalizedWheelPixels(event) {
  const unit = event.deltaMode === WheelEvent.DOM_DELTA_LINE ? 16 : event.deltaMode === WheelEvent.DOM_DELTA_PAGE ? chromeTabs.clientWidth : 1;
  return {
    x: event.deltaX * unit,
    y: event.deltaY * unit
  };
}

function handleChromeTabsWheel(event) {
  if (chromeTabs.scrollWidth <= chromeTabs.clientWidth) return;
  const { x, y } = normalizedWheelPixels(event);
  const primaryDelta = Math.abs(x) > Math.abs(y) ? x : y * 0.5;
  if (!primaryDelta) return;
  event.preventDefault();
  chromeTabs.scrollLeft += primaryDelta;
}

function activateTab(tabId, { scrollActive = true } = {}) {
  saveActiveDraft();
  state.activeTabId = tabId;
  const tab = activeTab();
  if (!tab) return;
  summaryTitleText.textContent = tab.type === "guide"
    ? "Guide"
    : tab.type === "voice-settings"
      ? "Voice Settings"
      : "Summary";
  if (["draft", "job"].includes(tab.type)) {
    urlInput.value = tab.url || "";
  }
  setProgress(visibleProgress(tab), ["queued", "running"].includes(tab.jobStatus));
  if (tab.type === "guide") {
    summary.innerHTML = guideHtml();
  } else if (tab.type === "voice-settings") {
    summary.innerHTML = voiceSettingsHtml();
    ensureLocalVoiceCatalog().then(() => {
      if (activeTab()?.type === "voice-settings") refreshVoiceSettingsTab();
    });
  } else if (tab.error) {
    summary.innerHTML = errorHtml(tab.error, tab.errorType);
  } else if (tab.markdown) {
    summary.innerHTML = markdownToHtml(cleanSummaryText(tab.markdown));
  } else if (["queued", "running"].includes(tab.jobStatus)) {
    summary.innerHTML = loadingHtml(tab);
  } else if (tab.statusText) {
    summary.innerHTML = emptyHtml(tab.statusText);
  } else {
    summary.innerHTML = emptyHtml("Paste a YouTube URL in this tab, or press Ctrl+N for another tab.");
  }
  renderTabs({ scrollActive, preserveScroll: !scrollActive });
  renderQueue();
  updateProgressViews();
  if (!chatPanel.hidden) {
    loadChatMemory(tab).finally(renderChatMessages);
  }
}

function closeTab(tabId, event) {
  if (event) event.stopPropagation();
  if (state.tabs.length === 1) {
    const only = state.tabs[0];
    rememberClosedTab(only);
    only.title = "New Summary";
    only.type = "draft";
    only.url = "";
    only.markdown = "";
    only.error = "";
    only.statusText = "";
    activateTab(only.id);
    return;
  }
  const index = state.tabs.findIndex((tab) => tab.id === tabId);
  if (index === -1) return;
  rememberClosedTab(state.tabs[index]);
  state.tabs.splice(index, 1);
  if (state.activeTabId === tabId) {
    const next = state.tabs[Math.max(0, index - 1)];
    state.activeTabId = next.id;
  }
  activateTab(state.activeTabId);
}

function saveActiveDraft() {
  const tab = activeTab();
  if (!tab || !["draft", "job"].includes(tab.type)) return;
  tab.url = urlInput.value.trim();
  if (tab.type === "draft" && tab.url && tab.title === "New Summary") tab.title = titleFromUrl(tab.url);
}

function renderTabs({ scrollActive = false, preserveScroll = true } = {}) {
  const previousScrollLeft = chromeTabs.scrollLeft;
  chromeTabs.innerHTML = "";
  state.tabs.forEach((tab) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.dataset.tabId = tab.id;
    btn.className = `chrome-tab ${tab.id === state.activeTabId ? "is-active" : ""} ${tab.jobStatus === "running" || tab.jobStatus === "queued" ? "is-running" : ""} ${tab.jobStatus === "failed" || tab.error ? "is-failed" : ""} ${tab.type === "history" ? "is-saved" : ""}`;
    btn.title = tab.title;
    btn.innerHTML = `
      <span class="tab-label">${escapeHtml(tab.title)}</span>
      ${["queued", "running"].includes(tab.jobStatus) ? `<span class="tab-progress"><span style="width:${Math.max(4, Math.min(100, visibleProgress(tab)))}%"></span></span>` : ""}
      <span class="tab-close" title="Close tab">x</span>`;
    btn.addEventListener("click", () => activateTab(tab.id));
    btn.querySelector(".tab-close").addEventListener("click", (event) => closeTab(tab.id, event));
    chromeTabs.appendChild(btn);
  });
  if (preserveScroll) {
    chromeTabs.scrollLeft = previousScrollLeft;
    requestAnimationFrame(() => {
      chromeTabs.scrollLeft = previousScrollLeft;
    });
  }
  if (scrollActive) requestAnimationFrame(scrollActiveTabIntoView);
}

function syncTabButton(tab) {
  const button = chromeTabs.querySelector(`[data-tab-id="${tab.id}"]`);
  if (!button) return;
  button.className = `chrome-tab ${tab.id === state.activeTabId ? "is-active" : ""} ${tab.jobStatus === "running" || tab.jobStatus === "queued" ? "is-running" : ""} ${tab.jobStatus === "failed" || tab.error ? "is-failed" : ""} ${tab.type === "history" ? "is-saved" : ""}`;
  button.title = tab.title;
  const label = button.querySelector(".tab-label");
  if (label) label.textContent = tab.title;
  let progress = button.querySelector(".tab-progress");
  if (["queued", "running"].includes(tab.jobStatus)) {
    if (!progress) {
      progress = document.createElement("span");
      progress.className = "tab-progress";
      progress.innerHTML = "<span></span>";
      button.querySelector(".tab-close")?.before(progress);
    }
    progress.querySelector("span").style.width = `${Math.max(4, Math.min(100, visibleProgress(tab)))}%`;
  } else {
    progress?.remove();
  }
}

function renderQueue() {
  const jobs = [...state.jobs.values()].filter((job) => ["queued", "running", "failed"].includes(job.status));
  if (!jobs.length) {
    queueList.innerHTML = '<div class="queue-empty">No active jobs.</div>';
    return;
  }
  queueList.innerHTML = jobs.map((job) => `
    <button class="queue-item" type="button" data-job-id="${job.id}">
      <strong>${escapeHtml(job.title || titleFromUrl(job.url))}</strong>
      ${escapeHtml(job.status)} · ${Math.round(visibleProgress(job))}% · ${escapeHtml(job.message || job.error || "")}${job.tokens_per_second ? ` · ${escapeHtml(job.tokens_per_second)} tok/s` : ""}
    </button>
  `).join("");
  queueList.querySelectorAll("[data-job-id]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const tab = state.tabs.find((item) => item.jobId === btn.dataset.jobId);
      if (tab) activateTab(tab.id);
    });
  });
}

function showError(message, type) {
  const providerLabel = state.provider === "ollama" ? "Ollama" : "LM Studio";
  const title = type === "model_memory" ? `${providerLabel} model/memory issue.` : "Something needs attention.";
  status.innerHTML = type ? errorHtml(message, type) : `<div class="error-card"><strong>${escapeHtml(title)}</strong><br>${escapeHtml(message)}</div>`;
}

function updateTabFromJob(job) {
  const tab = state.tabs.find((item) => item.jobId === job.id);
  if (!tab) return;
  const previousStatus = tab.jobStatus;
  tab.title = job.title || titleFromUrl(job.url);
  tab.url = job.url;
  tab.jobStatus = job.status;
  tab.progress = job.progress;
  if (job.status === "running" && !tab.startedAt) tab.startedAt = Date.now();
  tab.statusText = job.message || "";
  tab.tokensPerSecond = job.tokens_per_second || tab.tokensPerSecond;
  tab.completionTokens = job.completion_tokens || tab.completionTokens;
  tab.elapsedSeconds = job.elapsed_seconds || tab.elapsedSeconds;
  tab.language = job.language || tab.language || "";
  tab.error = job.error || "";
  tab.errorType = job.error_type || "";
  if (job.summary) {
    tab.markdown = summaryMarkdownWithTitle(job.title, job.summary);
    tab.type = "history";
    tab.historyId = job.history_id || tab.historyId;
    refreshVoiceSettingsTab();
  }
  syncTabButton(tab);
  const reachedFinalState = ["succeeded", "failed"].includes(job.status) && previousStatus !== job.status;
  if (tab.id === state.activeTabId && reachedFinalState) activateTab(tab.id, { scrollActive: false });
  else if (tab.id === state.activeTabId) updateProgressViews();
}

async function refreshModels() {
  modelStatus.className = "model-status";
  modelStatus.textContent = "Checking local model server...";
  modelSelect.innerHTML = '<option value="">Loading models...</option>';
  loadModelBtn.disabled = true;
  unloadModelBtn.disabled = true;
  try {
    const response = await fetch(api.models);
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || `Request failed: ${response.status}`);
    }
    state.modelInventory = data;
    state.provider = data.provider || providerSelect.value || "lm_studio";
    providerSelect.value = state.provider;
    modelSelect.innerHTML = "";
    const available = data.models || [];
    if (!available.length) {
      modelSelect.innerHTML = '<option value="">No local chat models found</option>';
    }
    for (const model of available) {
      const option = document.createElement("option");
      option.value = model.key;
      const details = [model.params_string, model.quantization && model.quantization.name].filter(Boolean).join(" ");
      option.textContent = `${model.loaded ? "Loaded: " : ""}${model.display_name || model.key}${details ? ` (${details})` : ""}`;
      modelSelect.appendChild(option);
    }
    if (data.current_model && available.some((model) => model.key === data.current_model)) modelSelect.value = data.current_model;
    if (data.provider === "ollama" && available.length && !modelSelect.value) {
      modelSelect.value = available[0].key;
    }
    if (data.provider === "ollama" && data.ok) {
      modelStatus.textContent = `🟢 Ollama connected. Selected model: ${modelSelect.value || data.current_model}`;
      advancedHint.textContent = "Ollama ready";
    } else if (data.current_model) {
      modelStatus.textContent = `🟢 Model loaded: ${data.current_model}`;
      advancedHint.textContent = "Model loaded";
    } else if (data.status === "no_model") {
      modelStatus.textContent = "🟡 LM Studio is connected. Choose a model and click Load model.";
      advancedHint.textContent = "Load a model";
      modelStatus.classList.add("warning");
    } else if (data.status === "multiple_models") {
      modelStatus.textContent = "🔴 Multiple models are loaded. Unload extras before summarizing.";
      advancedHint.textContent = "Too many models";
      modelStatus.classList.add("error");
    } else {
      modelStatus.textContent = `🔴 ${data.message || "Local model server needs attention."}`;
      advancedHint.textContent = state.provider === "ollama" ? "Needs Ollama" : "Needs LM Studio";
      modelStatus.classList.add("error");
    }
    updateModelButtons();
  } catch (error) {
    state.modelInventory = null;
    modelSelect.innerHTML = '<option value="">Model server unavailable</option>';
    modelStatus.textContent = state.provider === "ollama"
      ? "🔴 Ollama is not connected. Open Ollama or run 'ollama serve'."
      : "🔴 LM Studio is not connected. Start the local server at http://127.0.0.1:1234.";
    modelStatus.classList.add("error");
    advancedHint.textContent = state.provider === "ollama" ? "Needs Ollama" : "Needs LM Studio";
    summarizeBtn.disabled = true;
  }
}

async function loadSettings() {
  try {
    const data = await requestJson("/api/settings");
    state.provider = data.settings?.provider || "lm_studio";
    providerSelect.value = state.provider;
    lmStudioPortInput.value = data.settings?.lm_studio_port_saved ? data.settings?.lm_studio_port : "";
  } catch {
    state.provider = "lm_studio";
    providerSelect.value = "lm_studio";
    lmStudioPortInput.value = "";
  }
  syncProviderUi();
}

async function testConnection() {
  const port = lmStudioPortInput.value.trim() || "1234";
  testConnectionBtn.disabled = true;
  modelStatus.textContent = state.provider === "ollama"
    ? "Testing Ollama connection..."
    : `Testing LM Studio on port ${port}...`;
  try {
    const data = await requestJson("/api/settings/test-lm-studio", {
      method: "POST",
      body: JSON.stringify({ port, provider: providerSelect.value })
    });
    state.modelInventory = data.models;
    showToast(data.models.connected ? `${providerSelect.value === "ollama" ? "Ollama" : "LM Studio"} connected` : "Connection checked");
    await refreshModels();
  } catch (error) {
    modelStatus.textContent = `🔴 ${error.message}`;
    modelStatus.classList.add("error");
  } finally {
    testConnectionBtn.disabled = false;
  }
}

function updateModelButtons() {
  const inventory = state.modelInventory;
  const selected = modelSelect.value;
  const loaded = inventory ? inventory.loaded_models || [] : [];
  const selectedLoaded = loaded.includes(selected);
  summarizeBtn.disabled = !(inventory && inventory.ok);
  const isLmStudio = state.provider === "lm_studio";
  loadModelBtn.disabled = !isLmStudio || !selected || selectedLoaded || loaded.length > 0 || !inventory || inventory.source !== "native_v1";
  unloadModelBtn.disabled = !isLmStudio || !inventory || !loaded.length || inventory.source !== "native_v1";
  updateChatUploadControls();
}

function syncProviderUi() {
  const isLmStudio = providerSelect.value !== "ollama";
  state.provider = providerSelect.value;
  lmStudioPortInput.disabled = !isLmStudio;
  lmStudioPortInput.style.opacity = isLmStudio ? "1" : ".6";
  loadModelBtn.textContent = isLmStudio ? "Load model" : "Load not needed";
  unloadModelBtn.textContent = isLmStudio ? "Unload model" : "Unload not needed";
}

function handleModelSelectionChange() {
  if (state.provider === "ollama" && modelSelect.value) {
    modelStatus.className = "model-status";
    modelStatus.textContent = `🟢 Ollama connected. Selected model: ${modelSelect.value}`;
    advancedHint.textContent = "Ollama ready";
  }
  updateModelButtons();
}

async function loadSelectedModel() {
  const selected = modelSelect.value;
  try {
    modelStatus.textContent = "Loading model into LM Studio...";
    loadModelBtn.disabled = true;
    await requestJson(api.modelLoad, { method: "POST", body: JSON.stringify({ model: selected }) });
    showToast("Model ready");
    await refreshModels();
  } catch (error) {
    showError(error.message, error.errorType || "model_load_error");
    await refreshModels();
  }
}

async function unloadLoadedModel() {
  const inventory = state.modelInventory;
  const loaded = inventory ? inventory.loaded_models || [] : [];
  const selected = loaded.includes(modelSelect.value) ? modelSelect.value : loaded[0];
  try {
    modelStatus.textContent = "Stopping current model...";
    unloadModelBtn.disabled = true;
    await requestJson(api.modelUnload, { method: "POST", body: JSON.stringify({ instance_id: selected }) });
    showToast("Model stopped");
    await refreshModels();
  } catch (error) {
    showError(error.message, error.errorType || "model_unload_error");
    await refreshModels();
  }
}

async function loadPromptPreset() {
  try {
    const data = await requestJson(api.prompt);
    promptEditor.value = data.prompt || "";
    state.defaultPrompt = data.prompt || "";
    promptStatus.textContent = data.is_default ? "Using built-in default prompt." : "Using your saved custom prompt.";
  } catch {
    promptStatus.textContent = "Could not connect to prompt preset storage.";
  }
}

async function savePromptPreset() {
  const prompt = promptEditor.value.trim();
  if (!prompt) {
    promptStatus.textContent = "Prompt cannot be empty. Reset to default instead.";
    return;
  }
  try {
    const data = await requestJson(api.prompt, {
      method: "POST",
      body: JSON.stringify({ prompt, preset_id: state.activePromptPresetId })
    });
    promptEditor.value = data.prompt;
    state.defaultPrompt = data.prompt || "";
    markDefaultPromptLive(state.activePromptPresetId, state.defaultPrompt);
    promptStatus.textContent = "Saved. This is now your default prompt.";
    showToast("Prompt saved");
    await loadPromptPresets();
  } catch (error) {
    promptStatus.textContent = error.message;
  }
}

async function resetPromptPreset() {
  try {
    const data = await requestJson(api.promptReset, { method: "POST" });
    promptEditor.value = data.prompt;
    state.defaultPrompt = data.prompt || "";
    state.activePromptPresetId = "built-in-default";
    markDefaultPromptLive("built-in-default", state.defaultPrompt);
    promptStatus.textContent = "Reset to built-in default prompt.";
    showToast("Prompt reset");
    await loadPromptPresets();
  } catch (error) {
    promptStatus.textContent = error.message;
  }
}

async function loadPromptPresets() {
  try {
    const data = await requestJson(api.promptPresets);
    state.promptPresets = data.presets || [];
    renderPromptPresets();
  } catch (error) {
    presetList.innerHTML = `<div class="queue-empty">${escapeHtml(error.message)}</div>`;
  }
}

function renderPromptPresets() {
  if (!state.promptPresets.length) {
    presetList.innerHTML = '<div class="queue-empty">No saved presets yet.</div>';
    return;
  }
  const defaultPreset = state.promptPresets.find((preset) => preset.is_default);
  if (defaultPreset && !state.activePromptPresetId) state.activePromptPresetId = defaultPreset.id;
  presetList.innerHTML = state.promptPresets.map((preset) => `
    <div class="preset-item" data-preset-id="${escapeHtml(preset.id)}">
      <button class="preset-use" type="button" data-preset-action="use">
        <strong>${escapeHtml(preset.name || "Prompt preset")}</strong>
        <span>${preset.is_default ? "default" : preset.is_builtin ? "built in" : "saved locally"}</span>
      </button>
      ${preset.is_builtin ? "" : `
        <button class="preset-icon-action" type="button" data-preset-action="rename" title="Rename preset">Rename</button>
        <button class="preset-icon-action danger" type="button" data-preset-action="delete" title="Delete preset">Delete</button>
      `}
    </div>
  `).join("");
  presetList.querySelectorAll("[data-preset-action]").forEach((button) => {
    button.addEventListener("click", (event) => {
      const item = event.currentTarget.closest("[data-preset-id]");
      const presetId = item?.dataset.presetId;
      if (!presetId) return;
      const action = event.currentTarget.dataset.presetAction;
      if (action === "use") usePromptPreset(presetId);
      if (action === "rename") renamePromptPreset(presetId);
      if (action === "delete") deletePromptPreset(presetId);
    });
  });
}

function markDefaultPromptLive(presetId = "", prompt = "") {
  const cleanedPrompt = (prompt || "").trim();
  state.promptPresets = state.promptPresets.map((preset) => ({
    ...preset,
    is_default: presetId
      ? preset.id === presetId
      : (preset.prompt || "").trim() === cleanedPrompt
  }));
  renderPromptPresets();
}

function syncActivePromptPresetFromEditor() {
  if (!state.activePromptPresetId) return;
  const preset = state.promptPresets.find((item) => item.id === state.activePromptPresetId);
  if (!preset || (preset.prompt || "").trim() !== promptEditor.value.trim()) state.activePromptPresetId = "";
}

async function usePromptPreset(presetId) {
  try {
    const data = await requestJson(`${api.promptPresets}/${encodeURIComponent(presetId)}`);
    promptEditor.value = data.preset.prompt || "";
    state.activePromptPresetId = data.preset.id || presetId;
    promptStatus.textContent = `Loaded preset: ${data.preset.name || "Prompt preset"}. Click Save as Default to make it your default.`;
    showToast("Preset loaded");
  } catch (error) {
    promptStatus.textContent = error.message;
  }
}

async function saveCurrentAsPreset() {
  const prompt = promptEditor.value.trim();
  const name = presetNameInput.value.trim();
  if (!prompt) {
    promptStatus.textContent = "Prompt cannot be empty.";
    return;
  }
  try {
    const data = await requestJson(api.promptPresets, {
      method: "POST",
      body: JSON.stringify({ name, prompt })
    });
    presetNameInput.value = "";
    promptStatus.textContent = `Saved preset: ${data.preset.name}.`;
    showToast("Preset saved");
    await loadPromptPresets();
  } catch (error) {
    promptStatus.textContent = error.message;
  }
}

async function renamePromptPreset(presetId) {
  const preset = state.promptPresets.find((item) => item.id === presetId);
  const name = window.prompt("Rename preset", preset?.name || "");
  if (name === null) return;
  try {
    const data = await requestJson(`${api.promptPresets}/${encodeURIComponent(presetId)}/rename`, {
      method: "POST",
      body: JSON.stringify({ name })
    });
    promptStatus.textContent = `Renamed preset: ${data.preset.name}.`;
    showToast("Preset renamed");
    await loadPromptPresets();
  } catch (error) {
    promptStatus.textContent = error.message;
  }
}

async function deletePromptPreset(presetId) {
  const preset = state.promptPresets.find((item) => item.id === presetId);
  if (!window.confirm(`Delete "${preset?.name || "this preset"}"?`)) return;
  try {
    await requestJson(`${api.promptPresets}/${encodeURIComponent(presetId)}/delete`, { method: "POST" });
    promptStatus.textContent = "Preset deleted.";
    showToast("Preset deleted");
    await loadPromptPresets();
  } catch (error) {
    promptStatus.textContent = error.message;
  }
}

async function loadHistoryTabs() {
  try {
    const data = await requestJson(api.history);
    for (const item of (data.items || []).slice(0, 4)) {
      state.tabs.push({
        id: uid("tab"),
        title: item.title || "Saved summary",
        type: "history",
        url: item.url || "",
        markdown: "",
        statusText: "Click to load saved Markdown history.",
        jobId: "",
        historyId: item.id,
        progress: 0,
        jobStatus: "",
        error: ""
      });
    }
    renderTabs();
  } catch {
    renderTabs();
  }
}

async function loadHistoryItem(tab) {
  if (!tab.historyId || tab.markdown) return;
  try {
    const data = await requestJson(`${api.history}/${encodeURIComponent(tab.historyId)}`);
    const item = data.item;
    tab.title = item.title || tab.title;
    tab.markdown = cleanSummaryText(item.summary || item.markdown || "");
    tab.url = item.url || tab.url;
    tab.statusText = "";
  } catch (error) {
    tab.error = error.message;
  }
}

async function summarize() {
  saveActiveDraft();
  const urls = parseUrls();
  status.innerHTML = "";
  if (!urls.length) {
    showError("Paste at least one YouTube URL first.", "missing_url");
    return;
  }
  summarizeBtn.disabled = true;
  summarizeBtn.style.opacity = ".72";
  try {
    status.innerHTML = `Reading video titles<span class="loading-dot"></span>`;
    const titleMap = await fetchVideoMetadata(urls);
    const tabMap = {};
    for (const url of urls) {
      const existingDraft = activeTab();
      const canReuseActive = urls.length === 1 && existingDraft && existingDraft.type === "draft" && !existingDraft.markdown && !existingDraft.jobId;
      const tab = canReuseActive ? existingDraft : createTab({ activate: false });
      tab.type = "job";
      tab.title = titleMap[url] || titleFromUrl(url);
      tab.url = url;
      tab.jobStatus = "queued";
      tab.statusText = "Waiting in queue...";
      tab.progress = 0;
      tab.startedAt = 0;
      tab.tokensPerSecond = null;
      tab.completionTokens = null;
      tab.elapsedSeconds = null;
      tabMap[url] = tab;
    }
    activateTab(tabMap[urls[0]].id);
    const data = await requestJson(api.jobs, {
      method: "POST",
      body: JSON.stringify({ urls, model: modelSelect.value, titles: titleMap })
    });
    for (const job of data.jobs || []) {
      state.jobs.set(job.id, job);
      const tab = tabMap[job.url] || createTab({ activate: false });
      tab.type = "job";
      tab.title = job.title || tab.title || titleFromUrl(job.url);
      tab.url = job.url;
      tab.jobId = job.id;
      tab.jobStatus = job.status;
      tab.statusText = job.message;
      tab.progress = job.progress;
      tab.startedAt = job.status === "running" ? Date.now() : 0;
    }
    if (data.jobs && data.jobs[0]) {
      const first = state.tabs.find((tab) => tab.jobId === data.jobs[0].id);
      if (first) activateTab(first.id);
    }
    status.innerHTML = queueStatusText();
    startPolling();
    showToast("Queue started");
  } catch (error) {
    showError(error.message, error.errorType || "queue_error");
  } finally {
    summarizeBtn.disabled = !(state.modelInventory && state.modelInventory.ok);
    summarizeBtn.style.opacity = "1";
  }
}

async function pollJobs() {
  const activeJobs = [...state.jobs.values()].filter((job) => ["queued", "running"].includes(job.status));
  if (!activeJobs.length) {
    clearInterval(state.pollTimer);
    state.pollTimer = null;
    status.textContent = queueStatusText(true);
    return;
  }
  await Promise.all(activeJobs.map(async (job) => {
    try {
      const data = await requestJson(`${api.jobs}/${job.id}`);
      const oldStatus = state.jobs.get(job.id)?.status;
      state.jobs.set(job.id, data.job);
      updateTabFromJob(data.job);
      if (data.job.status === "succeeded" && oldStatus !== "succeeded") {
        status.textContent = queueStatusText();
        playFinishAnimation();
        showToast(`Done: ${data.job.title || "Summary ready"}`);
      }
    } catch (error) {
      job.status = "failed";
      job.error = error.message;
      state.jobs.set(job.id, job);
      updateTabFromJob(job);
    }
  }));
  renderQueue();
  status.textContent = queueStatusText();
}

function queueStatusText(allowDone = false) {
  const jobs = [...state.jobs.values()];
  const active = jobs.filter((job) => ["queued", "running"].includes(job.status));
  const running = jobs.filter((job) => job.status === "running");
  const done = jobs.filter((job) => job.status === "succeeded");
  if (active.length) {
    const current = running[0] || active[0];
    return `${done.length}/${jobs.length} done · ${current.status}: ${current.title || titleFromUrl(current.url)}`;
  }
  if (allowDone && jobs.length) return `${done.length}/${jobs.length} done`;
  return "";
}

function startPolling() {
  if (!state.pollTimer) state.pollTimer = setInterval(pollJobs, 1000);
  startProgressTicker();
  pollJobs();
}

async function copyResult() {
  const tab = activeTab();
  const text = cleanSummaryText(tab?.markdown || summary.innerText);
  if (!text.trim()) return;
  try {
    await navigator.clipboard.writeText(text);
    setButtonLabel(copyBtn, "Copied");
    showToast("Copied");
    setTimeout(() => setButtonLabel(copyBtn, "Copy"), 1200);
  } catch {
    showToast("Copy failed");
  }
}

async function copyFeedbackEmail() {
  const email = feedbackEmailBtn?.dataset.email || feedbackEmailBtn?.innerText.trim() || "";
  if (!email) return;
  try {
    await navigator.clipboard.writeText(email);
    feedbackEmailBtn.classList.remove("copied");
    void feedbackEmailBtn.offsetWidth;
    feedbackEmailBtn.classList.add("copied");
    showToast("Email copied");
    setTimeout(() => feedbackEmailBtn.classList.remove("copied"), 1300);
  } catch {
    showToast("Copy failed");
  }
}

function renderChatMessages() {
  const tab = activeTab();
  const key = chatKeyForTab(tab) || tab?.id || "";
  const messages = state.chatHistory.get(key) || [];
  chatMessages.innerHTML = messages.length ? messages.map((message) => `
    <div class="chat-message ${message.role === "user" ? "user" : "assistant"} ${message.pending ? "thinking" : ""}">
      <div class="chat-message-content">${message.pending ? `${escapeHtml(message.content)}<span class="thinking-dots" aria-hidden="true"><span></span><span></span><span></span></span>` : chatContentHtml(message.content)}</div>
    </div>
  `).join("") : '<div class="chat-message">Ask a question about the current summary.</div>';
  if (chatSubtitle) chatSubtitle.textContent = tab?.title || "Ask about this summary";
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

async function loadChatMemory(tab = activeTab()) {
  const key = chatKeyForTab(tab);
  if (!key || state.chatHistory.has(key)) return;
  try {
    const data = await requestJson(`/api/chat/history/${encodeURIComponent(key)}`);
    state.chatHistory.set(key, data.messages || []);
  } catch {
    state.chatHistory.set(key, []);
  }
}

async function toggleChatPanel(forceOpen = null) {
  const shouldOpen = forceOpen === null ? chatPanel.hidden : forceOpen;
  chatPanel.hidden = !shouldOpen;
  content.classList.toggle("chat-open", shouldOpen);
  chatBtn.classList.toggle("is-active", shouldOpen);
  chatBtn.setAttribute("aria-pressed", shouldOpen ? "true" : "false");
  if (chatResizer) chatResizer.hidden = !shouldOpen;
  applyChatLayout();
  if (shouldOpen) {
    await loadChatMemory();
    renderChatMessages();
    chatInput.focus();
  }
}

async function sendChatMessage(event) {
  event.preventDefault();
  const tab = activeTab();
  const summaryText = cleanSummaryText(tab?.markdown || summary.innerText);
  const question = chatInput.value.trim();
  if (!question) return;
  if (!summaryText || ["queued", "running"].includes(tab?.jobStatus)) {
    showToast("Wait for the summary first");
    return;
  }
  const key = chatKeyForTab(tab) || tab.id;
  const messages = state.chatHistory.get(key) || [];
  messages.push({ role: "user", content: question });
  messages.push({ role: "assistant", content: "Thinking…", pending: true });
  state.chatHistory.set(key, messages);
  chatInput.value = "";
  chatSendBtn.disabled = true;
  renderChatMessages();
  try {
    const attachmentNote = attachedFiles.length ? `\n\nAttached file text:\n${attachedFiles.map((file) => `File: ${file.name}\n${file.text || ""}`).join("\n\n")}` : "";
    const response = await fetch(api.chatStream, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ summary: summaryText, question: `${question}${attachmentNote}`, model: modelSelect.value, history_id: chatKeyForTab(tab) })
    });
    let answer = "";
    await moduleState.readEventStream(response, {
      onDelta(delta) {
        answer += delta;
        const nextMessages = messages.filter((message) => !message.pending);
        nextMessages.push({ role: "assistant", content: answer || "Thinking…", pending: !answer });
        state.chatHistory.set(key, nextMessages);
        renderChatMessages();
      },
      onDone(eventData) {
        const nextMessages = eventData.messages?.length ? eventData.messages : [
          ...messages.filter((message) => !message.pending),
          { role: "assistant", content: eventData.answer || answer }
        ];
        state.chatHistory.set(key, nextMessages);
      }
    });
  } catch (error) {
    const nextMessages = messages.filter((message) => !message.pending);
    nextMessages.push({ role: "assistant", content: error.message });
    state.chatHistory.set(key, nextMessages);
  } finally {
    chatSendBtn.disabled = false;
    renderChatMessages();
  }
}

function celebrateDonation() {
  summaryPanel.classList.remove("donation-celebrate");
  void summaryPanel.offsetWidth;
  summaryPanel.classList.add("donation-celebrate");
  showToast("Thank you for supporting the app");
  setTimeout(() => summaryPanel.classList.remove("donation-celebrate"), 1800);
}

async function openDonation() {
  const donationUrl = donationBtn.dataset.url || "";
  if (!donationUrl) {
    showToast("Donation link is not set");
    return;
  }
  donationBtn.disabled = true;
  try {
    const data = await requestJson(api.donation, { method: "POST", body: JSON.stringify({}) });
    if (!data.opened) window.location.href = donationUrl;
    setTimeout(celebrateDonation, 350);
  } catch {
    window.location.href = donationUrl;
    showToast("Opening Ko-fi");
  } finally {
    donationBtn.disabled = false;
  }
}

async function attachChatFile(file) {
  if (!file) return;
  const key = chatKeyForTab() || activeTab()?.id || "";
  const messages = state.chatHistory.get(key) || [];
  messages.push({ role: "assistant", content: `Reading ${moduleState.formatFileLabel ? moduleState.formatFileLabel(file) : file.name}…`, pending: true });
  state.chatHistory.set(key, messages);
  renderChatMessages();
  const formData = new FormData();
  formData.append("file", file);
  try {
    const response = await fetch("/api/files/ingest", { method: "POST", body: formData });
    const data = await response.json();
    if (!response.ok || data.ok === false) throw new Error(data.error || "Could not read file.");
    attachedFiles.push(data.file);
    const nextMessages = messages.filter((message) => !message.pending);
    nextMessages.push({ role: "assistant", content: `Attached and read: ${data.file.filename}${data.file.truncated ? " (trimmed)" : ""}` });
    state.chatHistory.set(key, nextMessages);
    showToast(`Attached ${data.file.filename}`);
  } catch (error) {
    const nextMessages = messages.filter((message) => !message.pending);
    nextMessages.push({ role: "assistant", content: error.message });
    state.chatHistory.set(key, nextMessages);
  } finally {
    renderChatMessages();
  }
}

async function playAnimeNarration(text) {
  startNarrationProgress({ service: "ElevenLabs", preparingLabel: "Preparing ElevenLabs voice" });
  activeNarrationController = new AbortController();
  const payload = {
    text,
    voice_id: localStorage.getItem("ytAnimeVoiceId") || "",
    api_key: localStorage.getItem("ytElevenLabsApiKey") || ""
  };
  const supportsStreamingAudio = "MediaSource" in window && MediaSource.isTypeSupported("audio/mpeg");
  if (!supportsStreamingAudio) {
    await playAnimeNarrationBlob(payload);
    return;
  }
  const response = await fetch(api.animeNarrationStream, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal: activeNarrationController.signal
  });
  if (!response.ok) {
    let message = "Anime voice is not available right now.";
    try {
      const data = await response.json();
      message = data.error || message;
    } catch (_) {}
    throw new Error(message);
  }
  if (!response.body) {
    await playAnimeNarrationBlob(payload);
    return;
  }

  const reader = response.body.getReader();
  const mediaSource = new MediaSource();
  const audioUrl = URL.createObjectURL(mediaSource);
  activeNarrationAudioUrl = audioUrl;
  activeNarrationAudio = new Audio(audioUrl);
  activeNarrationAudio.onended = () => {
    URL.revokeObjectURL(audioUrl);
    activeNarrationAudio = null;
    activeNarrationAudioUrl = "";
    speechActive = false;
    setButtonLabel(speakBtn, "Narrate");
  };
  activeNarrationAudio.onerror = () => {
    URL.revokeObjectURL(audioUrl);
    activeNarrationAudio = null;
    activeNarrationAudioUrl = "";
    speechActive = false;
    setButtonLabel(speakBtn, "Narrate");
    showToast("Could not play anime voice audio");
  };

  await new Promise((resolve, reject) => {
    let started = false;

    function appendBuffer(sourceBuffer, chunk) {
      return new Promise((appendResolve, appendReject) => {
        sourceBuffer.addEventListener("updateend", appendResolve, { once: true });
        sourceBuffer.addEventListener("error", appendReject, { once: true });
        sourceBuffer.appendBuffer(chunk);
      });
    }

    activeNarrationAudio.onerror = () => {
      reject(new Error("Could not play ElevenLabs audio."));
    };

    mediaSource.addEventListener("sourceopen", async () => {
      let sourceBuffer;
      try {
        sourceBuffer = mediaSource.addSourceBuffer("audio/mpeg");
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          await appendBuffer(sourceBuffer, value);
          if (!started) {
            started = true;
            finishNarrationProgress("Voice ready");
            await activeNarrationAudio.play();
            resolve();
          }
        }
        if (mediaSource.readyState === "open") mediaSource.endOfStream();
        if (!started) reject(new Error("ElevenLabs did not return audio."));
      } catch (error) {
        if (mediaSource.readyState === "open") {
          try { mediaSource.endOfStream(); } catch (_) {}
        }
        if (!started) reject(error);
        else showToast(error.message || "ElevenLabs stream stopped early");
      }
    }, { once: true });
  });
}

async function playAnimeNarrationBlob(payload) {
  const response = await fetch(api.animeNarration, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal: activeNarrationController?.signal
  });
  if (!response.ok) {
    let message = "Anime voice is not available right now.";
    try {
      const data = await response.json();
      message = data.error || message;
    } catch (_) {}
    throw new Error(message);
  }
  const audioUrl = URL.createObjectURL(await response.blob());
  finishNarrationProgress("Voice ready");
  activeNarrationAudioUrl = audioUrl;
  activeNarrationAudio = new Audio(audioUrl);
  activeNarrationAudio.onended = () => {
    URL.revokeObjectURL(audioUrl);
    activeNarrationAudio = null;
    activeNarrationAudioUrl = "";
    speechActive = false;
    setButtonLabel(speakBtn, "Narrate");
  };
  activeNarrationAudio.onerror = () => {
    URL.revokeObjectURL(audioUrl);
    activeNarrationAudio = null;
    activeNarrationAudioUrl = "";
    speechActive = false;
    setButtonLabel(speakBtn, "Narrate");
    showToast("Could not play anime voice audio");
  };
  await activeNarrationAudio.play();
}

function localNarrationChunks(text, maxChars = 220) {
  const cleaned = plainNarrationText(text).replace(/\s+/g, " ").trim();
  if (!cleaned) return [];
  const sentences = cleaned.match(/[^.!?。！？]+[.!?。！？]+["')\]]*|[^.!?。！？]+$/g) || [cleaned];
  const chunks = [];
  let current = "";

  function pushWords(sentence) {
    let wordChunk = "";
    sentence.split(/\s+/).forEach((word) => {
      if (!word) return;
      if (wordChunk && `${wordChunk} ${word}`.length > maxChars) {
        chunks.push(wordChunk);
        wordChunk = word;
        return;
      }
      if (!wordChunk && word.length > maxChars) {
        for (let index = 0; index < word.length; index += maxChars) {
          chunks.push(word.slice(index, index + maxChars));
        }
        return;
      }
      wordChunk = wordChunk ? `${wordChunk} ${word}` : word;
    });
    if (wordChunk) chunks.push(wordChunk);
  }

  sentences.forEach((rawSentence) => {
    const sentence = rawSentence.trim();
    if (!sentence) return;
    const next = current ? `${current} ${sentence}` : sentence;
    if (next.length <= maxChars) {
      current = next;
      return;
    }
    if (current) chunks.push(current);
    current = "";
    if (sentence.length <= maxChars) current = sentence;
    else pushWords(sentence);
  });

  if (current) chunks.push(current);
  return chunks;
}

async function fetchLocalNarrationBlob(payload, signal) {
  const response = await fetch(api.localVoiceNarration, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal
  });
  if (!response.ok) {
    let message = "Local voice is not available right now.";
    try {
      const data = await response.json();
      message = data.error || message;
    } catch (_) {}
    throw new Error(message);
  }
  const blob = await response.blob();
  if (!blob.size) throw new Error("Local voice returned an empty audio file.");
  return blob;
}

function abortError() {
  const error = new Error("Narration stopped.");
  error.name = "AbortError";
  return error;
}

function playNarrationAudioBlob(blob, signal, errorMessage) {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(abortError());
      return;
    }
    const audioUrl = URL.createObjectURL(blob);
    const audio = new Audio(audioUrl);

    function cleanup() {
      audio.onended = null;
      audio.onerror = null;
      signal?.removeEventListener("abort", onAbort);
      URL.revokeObjectURL(audioUrl);
      if (activeNarrationAudio === audio) activeNarrationAudio = null;
      if (activeNarrationAudioUrl === audioUrl) activeNarrationAudioUrl = "";
    }

    function onAbort() {
      audio.pause();
      cleanup();
      reject(abortError());
    }

    activeNarrationAudioUrl = audioUrl;
    activeNarrationAudio = audio;
    signal?.addEventListener("abort", onAbort, { once: true });
    audio.onended = () => {
      cleanup();
      resolve();
    };
    audio.onerror = () => {
      cleanup();
      reject(new Error(errorMessage));
    };
    audio.play().catch((error) => {
      cleanup();
      reject(error);
    });
  });
}

async function playLocalNarration(text) {
  startNarrationProgress({
    service: "local Style-Bert voice",
    preparingLabel: "Preparing local Style-Bert voice"
  });
  activeNarrationController = new AbortController();
  const signal = activeNarrationController.signal;
  saveLocalVoiceDropdowns();
  const warmupKey = localVoiceSelectionKey();
  if (localVoiceWarmupPromise && warmupKey && warmupKey === warmingLocalVoiceKey) {
    setNarrationProgress(18, "Finishing local voice warm-up...");
    await localVoiceWarmupPromise.catch(() => {});
  }
  clearInterval(narrationProgressTimer);

  const chunks = localNarrationChunks(text);
  if (!chunks.length) throw new Error("There is no summary text to narrate yet.");
  const model = selectedLocalVoiceModel();
  const language = localVoiceLanguageForText(model);
  if (!localVoiceSupportsLanguage(model, language)) {
    throw new Error(localVoiceIncompatibilityMessage(model, language));
  }
  if (language === "JP" && detectedNarrationLanguage() !== "ja") {
    throw new Error(localVoiceIncompatibilityMessage(model, "EN"));
  }
  const basePayload = {
    server_url: localVoiceServerUrl(),
    model_name: localStorage.getItem("ytLocalVoiceModelName") || model?.name || "",
    speaker_name: localStorage.getItem("ytLocalVoiceSpeakerName") || model?.speakers?.[0]?.name || "",
    style: localStorage.getItem("ytLocalVoiceStyle") || model?.styles?.[0] || "Neutral",
    language
  };

  function requestChunk(index) {
    return fetchLocalNarrationBlob({ ...basePayload, text: chunks[index] }, signal);
  }

  setNarrationProgress(12, `Preparing local voice part 1 of ${chunks.length}...`);
  let nextBlobPromise = requestChunk(0);
  for (let index = 0; index < chunks.length; index += 1) {
    const blob = await nextBlobPromise;
    if (signal.aborted) throw abortError();
    const nextIndex = index + 1;
    const progress = Math.min(96, 16 + ((index + 1) / chunks.length) * 76);
    if (nextIndex < chunks.length) {
      nextBlobPromise = requestChunk(nextIndex);
      nextBlobPromise.catch(() => {});
      setNarrationProgress(progress, `Speaking local voice part ${index + 1} of ${chunks.length} while preparing part ${nextIndex + 1}...`);
    } else {
      setNarrationProgress(progress, `Speaking local voice part ${index + 1} of ${chunks.length}...`);
    }
    await playNarrationAudioBlob(blob, signal, "Could not play local voice audio");
  }
  finishNarrationProgress("Local voice finished");
  speechActive = false;
  setButtonLabel(speakBtn, "Narrate");
}

async function toggleNarration() {
  if (speechActive) {
    activeNarrationController?.abort();
    activeNarrationController = null;
    stopNarrationProgress();
    if (activeNarrationAudio) {
      activeNarrationAudio.pause();
      activeNarrationAudio = null;
    }
    if (activeNarrationAudioUrl) {
      URL.revokeObjectURL(activeNarrationAudioUrl);
      activeNarrationAudioUrl = "";
    }
    if ("speechSynthesis" in window) speechSynthesis.cancel();
    speechActive = false;
    setButtonLabel(speakBtn, "Narrate");
    return;
  }
  const text = narrationText();
  if (!text) {
    showToast("Open or create a summary before using Narrate");
    return;
  }
  if (usesLocalVoice()) {
    speechActive = true;
    setButtonLabel(speakBtn, "Stop");
    try {
      await playLocalNarration(text);
    } catch (error) {
      stopNarrationProgress();
      speechActive = false;
      setButtonLabel(speakBtn, "Narrate");
      if (error.name !== "AbortError") showToast(error.message);
    }
    return;
  }
  if (usesElevenLabsVoice()) {
    speechActive = true;
    setButtonLabel(speakBtn, "Stop");
    try {
      await playAnimeNarration(text);
    } catch (error) {
      stopNarrationProgress();
      speechActive = false;
      setButtonLabel(speakBtn, "Narrate");
      if (error.name !== "AbortError") showToast(error.message);
    }
    return;
  }
  if (!("speechSynthesis" in window)) {
    showToast("Narration is not available on this system");
    return;
  }
  const utterance = new SpeechSynthesisUtterance(text);
  const voices = speechSynthesis.getVoices();
  const preferred = selectedNarrationVoice(voices);
  if (preferred) utterance.voice = preferred;
  utterance.rate = .98;
  utterance.pitch = 1;
  utterance.onend = () => {
    speechActive = false;
    setButtonLabel(speakBtn, "Narrate");
  };
  speechSynthesis.speak(utterance);
  speechActive = true;
  setButtonLabel(speakBtn, "Stop");
}

function voiceKey(voice) {
  return `${voice.name}::${voice.lang}`;
}

function languageName(lang = "") {
  try {
    const code = lang.split("-")[0] || "und";
    return new Intl.DisplayNames([navigator.language || "en"], { type: "language" }).of(code) || lang || "Other";
  } catch (_) {
    return lang || "Other";
  }
}

function detectedNarrationLanguage() {
  const tab = activeTab();
  const tabLanguage = (tab?.language || "").toLowerCase();
  if (tabLanguage) return tabLanguage.split("-")[0];
  const text = (tab?.markdown || summary?.innerText || "").slice(0, 1200);
  if (/[\u3040-\u30ff]/.test(text)) return "ja";
  if (/[\uac00-\ud7af]/.test(text)) return "ko";
  if (/[\u4e00-\u9fff]/.test(text)) return "zh";
  if (/[\u0400-\u04ff]/.test(text)) return "ru";
  if (/\b(der|die|das|und|nicht|ist|mit)\b/i.test(text)) return "de";
  if (/\b(le|la|les|et|est|avec|pour)\b/i.test(text)) return "fr";
  if (/\b(el|la|los|las|y|para|con|que)\b/i.test(text)) return "es";
  return "en";
}

function voiceMatchesLanguage(voice, language) {
  if (!language) return true;
  return (voice.lang || "").toLowerCase().split("-")[0] === language;
}

function voiceGroupLabel(voice, language = "") {
  const name = (voice.name || "").toLowerCase();
  const languageLabel = languageName(language || voice.lang);
  if (/fun|novelty|zarvox|whisper|bad news|bells|bubbles|boing|cellos|hysterical|pipe organ|trinoids|wobble|good news/i.test(voice.name)) {
    return `${languageLabel} - Funny voices`;
  }
  if (/samantha|victoria|karen|moira|fiona|serena|ava|allison|susan|zira|jenny|aria|female|woman|girl/i.test(voice.name)) {
    return `${languageLabel} - Women voices`;
  }
  if (/alex|daniel|fred|thomas|lee|aaron|oliver|david|mark|george|male|man|boy/i.test(voice.name)) {
    return `${languageLabel} - Men voices`;
  }
  if (/premium|enhanced|natural|neural|serious|professional/i.test(voice.name)) {
    return `${languageLabel} - Serious voices`;
  }
  return `${languageLabel} - Other voices`;
}

function groupedVoiceOptions(voices, language = "") {
  const groups = new Map();
  voices.forEach((voice) => {
    const label = voiceGroupLabel(voice, language);
    if (!groups.has(label)) groups.set(label, []);
    groups.get(label).push(voice);
  });
  return [...groups.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([label, groupVoices]) => {
    const options = groupVoices
      .sort((a, b) => a.name.localeCompare(b.name))
      .map((voice) => {
        const key = voiceKey(voice);
        return `<option value="${escapeHtml(key)}">${escapeHtml(`${voice.name} (${voice.lang})`)}</option>`;
      }).join("");
    return `<optgroup label="${escapeHtml(label)}">${options}</optgroup>`;
  }).join("");
}

function selectedNarrationVoice(voices = speechSynthesis.getVoices()) {
  const saved = localStorage.getItem("ytNarrationVoice") || "";
  const savedVoice = voices.find((voice) => voiceKey(voice) === saved);
  if (savedVoice) return savedVoice;
  const language = detectedNarrationLanguage();
  const matchingVoices = voices.filter((voice) => voiceMatchesLanguage(voice, language));
  const candidates = matchingVoices.length ? matchingVoices : voices;
  return candidates.find((voice) => /samantha|victoria|karen|moira|fiona|serena|ava|allison|susan|zira|jenny|aria/i.test(voice.name))
    || candidates.find((voice) => /premium|enhanced|natural|neural/i.test(voice.name))
    || candidates[0]
    || voices[0];
}

function usesElevenLabsVoice() {
  return localStorage.getItem("ytNarrationMode") === "elevenlabs"
    || localStorage.getItem("ytNarrationVoice") === "watchless-anime-ai";
}

function usesLocalVoice() {
  return localStorage.getItem("ytNarrationMode") === "local";
}

function localVoiceServerUrl() {
  return (localStorage.getItem("ytLocalVoiceServer") || defaultLocalVoiceServer).trim();
}

function localVoiceAssetsRoot() {
  return (localStorage.getItem("ytLocalVoiceAssetsRoot") || "").trim();
}

function savedLocalVoiceModels() {
  try {
    const models = JSON.parse(localStorage.getItem("ytLocalVoiceModels") || "[]");
    return Array.isArray(models) ? models : [];
  } catch {
    return [];
  }
}

function selectedLocalVoiceModel() {
  const selectedName = localStorage.getItem("ytLocalVoiceModelName") || "";
  return savedLocalVoiceModels().find((model) => model.name === selectedName) || savedLocalVoiceModels()[0] || null;
}

function latestNarratableTab() {
  const tab = activeTab();
  if (tab?.markdown) return tab;
  return [...state.tabs].reverse().find((item) => item.markdown) || null;
}

function narrationText() {
  const tab = latestNarratableTab();
  if (!tab?.markdown) return "";
  return plainNarrationText(tab.markdown);
}

function localVoiceSelectionKey() {
  const model = selectedLocalVoiceModel();
  if (!model) return "";
  return [
    localVoiceServerUrl(),
    localStorage.getItem("ytLocalVoiceModelName") || model.name || "",
    localStorage.getItem("ytLocalVoiceSpeakerName") || model?.speakers?.[0]?.name || "",
    localStorage.getItem("ytLocalVoiceStyle") || model?.styles?.[0] || "Neutral",
    "EN"
  ].join("|");
}

function savedElevenLabsVoices() {
  try {
    const voices = JSON.parse(localStorage.getItem("ytElevenLabsVoices") || "[]");
    return Array.isArray(voices) ? voices : [];
  } catch {
    return [];
  }
}

function recentElevenLabsVoiceIds() {
  try {
    const ids = JSON.parse(localStorage.getItem("ytRecentElevenLabsVoiceIds") || "[]");
    return Array.isArray(ids) ? ids : [];
  } catch {
    return [];
  }
}

function rememberRecentElevenLabsVoice(voiceId) {
  if (!voiceId) return;
  const ids = [voiceId, ...recentElevenLabsVoiceIds().filter((id) => id !== voiceId)].slice(0, 8);
  localStorage.setItem("ytRecentElevenLabsVoiceIds", JSON.stringify(ids));
}

function selectedVoiceLabel() {
  if (usesLocalVoice()) {
    const modelName = localStorage.getItem("ytLocalVoiceModelName") || "Local voice model";
    const style = localStorage.getItem("ytLocalVoiceStyle") || "";
    return style ? `${modelName} (${style})` : modelName;
  }
  if (usesElevenLabsVoice()) {
    return localStorage.getItem("ytAnimeVoiceName") || "ElevenLabs voice";
  }
  const voices = "speechSynthesis" in window ? speechSynthesis.getVoices() : [];
  const selected = selectedNarrationVoice(voices);
  return selected ? `${selected.name} (${selected.lang})` : "Automatic system voice";
}

function renderVoiceButton(value, label, detail = "", selected = false, extraAttrs = "") {
  return `
    <button class="voice-choice${selected ? " is-selected" : ""}" type="button" ${extraAttrs} value="${escapeHtml(value)}">
      <strong>${escapeHtml(label)}</strong>
      ${detail ? `<span>${escapeHtml(detail)}</span>` : ""}
    </button>`;
}

function localVoiceLanguageFilter() {
  return localStorage.getItem("ytLocalVoiceLanguageFilter") || "all";
}

function inferLocalVoiceLanguage(model = {}) {
  const direct = model.primary_language || model.language || "";
  if (direct) return String(direct).toUpperCase();
  const name = String(model.name || model.folder || "").toLowerCase();
  if (name.includes("esl") || name.includes("idflu")) return "ESL";
  if (name.includes("jp") || name.includes("jvnv") || name.endsWith("-jp")) return "JP";
  return "EN";
}

function localVoiceLanguages(model = {}) {
  const languages = Array.isArray(model.languages) ? model.languages : [];
  if (languages.length) return languages.map((item) => String(item).toUpperCase());
  return [inferLocalVoiceLanguage(model)];
}

function localVoiceMatchesLanguage(model = {}) {
  const filter = localVoiceLanguageFilter();
  if (filter === "all") return true;
  return localVoiceLanguages(model).some((language) => language === filter || (filter === "EN" && language.startsWith("EN")));
}

function localVoiceLanguageLabel(model = {}) {
  const primary = inferLocalVoiceLanguage(model);
  if (primary === "EN") return "English";
  if (primary === "JP") return "Japanese";
  if (primary === "ESL") return "ESL / accented English";
  if (primary === "UNKNOWN") return "Unknown language";
  return primary;
}

function localVoiceSupportsLanguage(model = {}, language = "EN") {
  const target = String(language || "EN").toUpperCase();
  return localVoiceLanguages(model).some((candidate) => candidate === target);
}

function localVoiceLanguageForText(model = {}) {
  const detected = detectedNarrationLanguage();
  if (detected === "ja" && localVoiceSupportsLanguage(model, "JP")) return "JP";
  if (detected === "zh" && localVoiceSupportsLanguage(model, "ZH")) return "ZH";
  if (localVoiceSupportsLanguage(model, "EN")) return "EN";
  if (localVoiceSupportsLanguage(model, "JP")) return "JP";
  return "EN";
}

function localVoiceWarmupText(language = "EN") {
  if (language === "JP") return "準備できました。";
  if (language === "ZH") return "准备好了。";
  return "Ready.";
}

function localVoiceIncompatibilityMessage(model = {}, language = "EN") {
  if (language === "EN" && !localVoiceSupportsLanguage(model, "EN")) {
    return `${model.name || "This model"} is not English-capable. It is a Japanese/JP-Extra voice model, so use it for Japanese text or choose an English model like Takanashi Kiara, HoloHi, HoloLow, HoloAus, or Koseki Bijou.`;
  }
  return `${model.name || "This model"} does not support ${language} narration. Choose a model that supports this text language.`;
}

function localVoiceLanguageFilterButtons() {
  const selected = localVoiceLanguageFilter();
  const options = [
    ["all", "All packs"],
    ["EN", "English"],
    ["ESL", "ESL"],
    ["JP", "Japanese"]
  ];
  return `<div class="voice-filter-row">
    ${options.map(([value, label]) => `
      <button class="voice-filter-chip${selected === value ? " is-selected" : ""}" type="button" data-local-language-filter="${escapeHtml(value)}">${escapeHtml(label)}</button>
    `).join("")}
  </div>`;
}

function renderLocalVoiceCard(model, actionLabel, extraAttrs = "", selected = false) {
  const language = localVoiceLanguageLabel(model);
  const detail = model.style || model.language_note || model.voice_type || "";
  const meta = [language, model.voice_type].filter(Boolean).join(" · ");
  return `
    <button class="voice-choice local-voice-card${selected ? " is-selected" : ""}" type="button" ${extraAttrs}>
      <span class="voice-card-kicker">${escapeHtml(meta)}</span>
      <strong>${escapeHtml(model.name)}</strong>
      ${detail ? `<span>${escapeHtml(detail)}</span>` : ""}
      <em>${escapeHtml(actionLabel)}</em>
    </button>`;
}

function elevenLabsVoiceTime(voice) {
  const raw = Number(voice.created_at_unix || voice.date_unix || 0);
  return raw > 100000000000 ? raw : raw * 1000;
}

function elevenLabsVoiceGroupLabel(voice) {
  const name = `${voice.name || ""} ${voice.description || ""}`.toLowerCase();
  const labels = voice.labels || {};
  const category = `${voice.category || ""}`.toLowerCase();
  const useCase = `${labels.use_case || ""}`.toLowerCase();
  const gender = `${labels.gender || ""}`.toLowerCase();
  if (/cloned|generated|professional/.test(category) || voice.is_owner) return "Your created/custom voices";
  if (/anime|girl|cute|kawaii|character|cartoon|game|animation/.test(`${name} ${useCase}`)) return "Anime / character style";
  if (/female|woman|girl/.test(gender) || /female|woman|girl/.test(name)) return "Women voices";
  if (/male|man|boy/.test(gender) || /male|man|boy/.test(name)) return "Men voices";
  if (/narrat|audiobook|news|serious|professional|calm|documentary/.test(`${name} ${useCase}`)) return "Narration / serious";
  if (/fun|comedy|character|cartoon|game|animation/.test(`${name} ${useCase}`)) return "Funny / character";
  return "Other ElevenLabs voices";
}

function nativeVoiceSections() {
  const voices = "speechSynthesis" in window ? speechSynthesis.getVoices() : [];
  const language = detectedNarrationLanguage();
  const matchingVoices = voices.filter((voice) => voiceMatchesLanguage(voice, language));
  const visibleVoices = matchingVoices.length ? matchingVoices : voices;
  const groups = new Map();
  visibleVoices.forEach((voice) => {
    const label = voiceGroupLabel(voice, language);
    if (!groups.has(label)) groups.set(label, []);
    groups.get(label).push(voice);
  });
  if (!visibleVoices.length) {
    return `<div class="voice-empty">No device voices were reported by this browser yet.</div>`;
  }
  const selectedKey = localStorage.getItem("ytNarrationVoice") || "";
  return [...groups.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([label, groupVoices]) => {
    const sortedVoices = groupVoices.sort((a, b) => a.name.localeCompare(b.name));
    const selectedInGroup = sortedVoices.some((voice) => !usesElevenLabsVoice() && voiceKey(voice) === selectedKey);
    const open = selectedInGroup || (!selectedKey && /women|serious/i.test(label));
    return `
    <details class="voice-group" ${open ? "open" : ""}>
      <summary><h4>${escapeHtml(label)}</h4><span>${sortedVoices.length} voices</span></summary>
      <div class="voice-choice-grid">
        ${sortedVoices.map((voice) => (
          renderVoiceButton(
            voiceKey(voice),
            voice.name,
            voice.lang,
            !usesElevenLabsVoice() && voiceKey(voice) === selectedKey,
            `data-voice-action="native" data-voice-key="${escapeHtml(voiceKey(voice))}"`
          )
        )).join("")}
      </div>
    </details>`;
  }).join("");
}

function elevenLabsVoiceSections() {
  const voices = savedElevenLabsVoices();
  const selectedId = localStorage.getItem("ytAnimeVoiceId") || "";
  if (!voices.length) {
    return `<div class="voice-empty">Connect your key, then click Load ElevenLabs voices.</div>`;
  }
  const recentIds = recentElevenLabsVoiceIds();
  const sortedVoices = [...voices].sort((a, b) => {
    const recentA = recentIds.indexOf(a.voice_id);
    const recentB = recentIds.indexOf(b.voice_id);
    if (recentA !== -1 || recentB !== -1) return (recentA === -1 ? 999 : recentA) - (recentB === -1 ? 999 : recentB);
    return elevenLabsVoiceTime(b) - elevenLabsVoiceTime(a);
  });
  const groups = new Map();
  sortedVoices.forEach((voice) => {
    const label = recentIds.includes(voice.voice_id) ? "Recently added / selected" : elevenLabsVoiceGroupLabel(voice);
    if (!groups.has(label)) groups.set(label, []);
    groups.get(label).push(voice);
  });
  return [...groups.entries()].map(([label, groupVoices], index) => {
    const selectedInGroup = groupVoices.some((voice) => usesElevenLabsVoice() && selectedId === voice.voice_id);
    const open = index === 0 || selectedInGroup;
    return `
    <details class="voice-group" ${open ? "open" : ""}>
      <summary><h4>${escapeHtml(label)}</h4><span>${groupVoices.length} voices</span></summary>
      <div class="voice-choice-grid">
    ${groupVoices.map((voice) => {
      const labels = voice.labels || {};
      const detail = [voice.category, labels.gender, labels.accent, labels.use_case].filter(Boolean).join(" · ");
      return renderVoiceButton(
        voice.voice_id,
        voice.name || "ElevenLabs voice",
        detail || voice.description || "ElevenLabs account voice",
        usesElevenLabsVoice() && selectedId === voice.voice_id,
        `data-voice-action="elevenlabs" data-voice-id="${escapeHtml(voice.voice_id)}" data-voice-name="${escapeHtml(voice.name || "ElevenLabs voice")}"`
      );
    }).join("")}
      </div>
    </details>`;
  }).join("");
}

function customVoiceSection() {
  const customId = localStorage.getItem("ytAnimeVoiceId") || "";
  const customName = localStorage.getItem("ytAnimeVoiceName") || "Uploaded anime voice";
  return customId
    ? renderVoiceButton(
      customId,
      customName,
      "Saved custom ElevenLabs voice",
      usesElevenLabsVoice() && localStorage.getItem("ytAnimeVoiceId") === customId,
      `data-voice-action="elevenlabs" data-voice-id="${escapeHtml(customId)}" data-voice-name="${escapeHtml(customName)}"`
    )
    : `<div class="voice-empty">No custom voice uploaded yet.</div>`;
}

function voiceStatusTitle(type = "") {
  if (type === "success") return "ElevenLabs connected";
  if (type === "loading") return "Checking ElevenLabs";
  if (type === "elevenlabs_certificate_error") return "Certificate issue on this Mac";
  if (type === "elevenlabs_invalid_api_key") return "API key rejected";
  if (type === "elevenlabs_rate_limited") return "ElevenLabs usage limit";
  return "ElevenLabs needs attention";
}

function voiceStatusHtml() {
  const status = state.voiceStatus;
  if (!status?.message) return "";
  const kind = status.type === "success" || status.type === "loading" ? status.type : "error";
  return `
    <div class="voice-status voice-status--${escapeHtml(kind)}">
      <strong>${escapeHtml(voiceStatusTitle(status.type))}</strong>
      <p>${escapeHtml(status.message)}</p>
    </div>`;
}

function localVoiceStatusTitle(type = "") {
  if (type === "success") return "Local voice ready";
  if (type === "loading") return "Checking local voice server";
  return "Local voice needs attention";
}

function localVoiceStatusHtml() {
  const status = state.localVoiceStatus;
  if (!status?.message) return "";
  const kind = status.type === "success" || status.type === "loading" ? status.type : "error";
  return `
    <div class="voice-status voice-status--${escapeHtml(kind)}">
      <strong>${escapeHtml(localVoiceStatusTitle(status.type))}</strong>
      <p>${escapeHtml(status.message)}</p>
    </div>`;
}

function voiceSectionIsOpen(sectionId, defaultOpen = true) {
  const saved = localStorage.getItem(`ytVoiceSectionOpen:${sectionId}`);
  return saved === null ? defaultOpen : saved === "true";
}

function voiceSectionHtml({ id, kicker, title, paragraphs = [], body = "", defaultOpen = true }) {
  return `
    <details class="voice-section" data-voice-section="${escapeHtml(id)}" ${voiceSectionIsOpen(id, defaultOpen) ? "open" : ""}>
      <summary class="voice-section-summary">
        <div class="voice-section-head">
          <span class="step-kicker">${escapeHtml(kicker)}</span>
          <h3>${escapeHtml(title)}</h3>
          ${paragraphs.map((text) => `<p>${text}</p>`).join("")}
        </div>
        <span class="voice-section-toggle" aria-hidden="true"></span>
      </summary>
      <div class="voice-section-body">
        ${body}
      </div>
    </details>`;
}

function localVoiceCatalogCards() {
  if (!state.localVoiceCatalog.length) {
    return `<div class="voice-empty">Load the local voice section once to see curated Hugging Face voice models.</div>`;
  }
  const models = state.localVoiceCatalog.filter(localVoiceMatchesLanguage);
  if (!models.length) {
    return `<div class="voice-empty">No curated downloads match this language filter yet. Switch to All to see every public model pack.</div>`;
  }
  return `<div class="voice-choice-grid">
    ${models.map((model) => renderLocalVoiceCard(
      model,
      "Download this voice pack",
      `data-local-download="${escapeHtml(model.id)}"`
    )).join("")}
  </div>`;
}

function localVoiceModelButtons() {
  const models = savedLocalVoiceModels();
  if (!models.length) {
    return `<div class="voice-empty">No local models detected yet. Test your local server after it is running, or download one into the assets folder below.</div>`;
  }
  const selectedModel = selectedLocalVoiceModel();
  const filteredModels = models.filter(localVoiceMatchesLanguage);
  if (!filteredModels.length) {
    return `<div class="voice-empty">No downloaded models match this language filter. Switch to All, or download an English-capable model below.</div>`;
  }
  return `<div class="voice-choice-grid">
    ${filteredModels.map((model) => renderLocalVoiceCard(
      {
        ...model,
        voice_type: `${model.device || "cpu"} · ${(model.styles || []).length} styles · ${(model.speakers || []).length} speakers`
      },
      selectedModel?.name === model.name ? "Selected" : "Use this voice model",
      `data-local-model="${escapeHtml(model.name)}"`,
      selectedModel?.name === model.name
    )).join("")}
  </div>`;
}

function localVoiceSpeakerOptions(model) {
  const speakers = model?.speakers || [];
  const saved = localStorage.getItem("ytLocalVoiceSpeakerName") || "";
  return speakers.map((speaker) => `<option value="${escapeHtml(speaker.name)}" ${saved === speaker.name ? "selected" : ""}>${escapeHtml(speaker.name)}</option>`).join("");
}

function localVoiceStyleOptions(model) {
  const styles = model?.styles || [];
  const saved = localStorage.getItem("ytLocalVoiceStyle") || "";
  return styles.map((style) => `<option value="${escapeHtml(style)}" ${saved === style ? "selected" : ""}>${escapeHtml(style)}</option>`).join("");
}

function localVoiceSectionHtml() {
  const serverUrl = localVoiceServerUrl();
  const assetsRoot = localVoiceAssetsRoot();
  const model = selectedLocalVoiceModel();
  return voiceSectionHtml({
    id: "local",
    kicker: "Section 2",
    title: "Free local voice models",
    paragraphs: [
      "Use a local Style-Bert-VITS2 server running on your Mac. This keeps narration off paid APIs and gives WatchLess a proper local model workflow.",
      "Best flow: test the local server, pick one downloaded English-capable model, and ignore the advanced download list unless you want more voices."
    ],
    body: `
      <div class="voice-login-row local-voice-grid">
        <input id="localVoiceServerInput" type="text" value="${escapeHtml(serverUrl)}" placeholder="Local server URL, for example http://127.0.0.1:5000">
        <button id="saveLocalVoiceServerBtn" type="button">Save server</button>
        <button id="testLocalVoiceServerBtn" type="button">Test server</button>
      </div>
      <div class="voice-login-row local-voice-grid">
        <input id="localVoiceAssetsRootInput" type="text" value="${escapeHtml(assetsRoot)}" placeholder="Model assets folder, for example /Users/sam/Style-Bert-VITS2/model_assets">
        <button id="saveLocalVoiceAssetsBtn" type="button">Save folder</button>
        <button id="refreshLocalVoiceModelsBtn" type="button">Refresh models</button>
      </div>
      ${localVoiceStatusHtml()}
      <div class="voice-subsection">
        <h4>Loaded local voice models</h4>
        <p>Choose which downloaded local model WatchLess should narrate with. English-compatible packs are shown first because most summaries are English.</p>
        ${localVoiceLanguageFilterButtons()}
        ${localVoiceModelButtons()}
      </div>
      <div class="voice-inline-fields">
        <label><span>Speaker</span><select id="localVoiceSpeakerSelect">${localVoiceSpeakerOptions(model)}</select></label>
        <label><span>Style</span><select id="localVoiceStyleSelect">${localVoiceStyleOptions(model)}</select></label>
      </div>
      <details class="voice-group voice-download-group">
        <summary><h4>Advanced: download more local voice packs</h4><span>Optional</span></summary>
        <div class="voice-download-body">
          <p>Use this only after saving a model assets folder above. WatchLess will download the selected compatible files into that folder, then refresh the local model list.</p>
          ${localVoiceLanguageFilterButtons()}
          ${localVoiceCatalogCards()}
        </div>
      </details>`,
  });
}

function voiceSettingsHtml() {
  const language = detectedNarrationLanguage();
  const languageLabel = languageName(language);
  const apiKey = localStorage.getItem("ytElevenLabsApiKey") || "";
  return `
    <div class="voice-page">
      <section class="voice-hero">
        <span class="step-kicker">Voice settings</span>
        <h2>Narration voice</h2>
        <p>Current voice: <strong>${escapeHtml(selectedVoiceLabel())}</strong>. WatchLess detects the summary language as <strong>${escapeHtml(languageLabel)}</strong> and shows matching system voices first.</p>
      </section>

      ${voiceSectionHtml({
        id: "native",
        kicker: "Section 1",
        title: "Choose your native system voices",
        paragraphs: ["These voices come from the Mac/browser. They are free, fast, and stay on the device."],
        body: nativeVoiceSections(),
      })}

      ${localVoiceSectionHtml()}

      ${voiceSectionHtml({
        id: "elevenlabs",
        kicker: "Section 3",
        title: "ElevenLabs account voices",
        paragraphs: [
          "Paste your ElevenLabs API key, then load the voice models available in your account. To find the key: open ElevenLabs, go to your profile or workspace settings, then open API Keys.",
          "Best flow: pick or create voices inside ElevenLabs first, then come back here and click Load voices. WatchLess lists voices your account can use through the API.",
          "If a library voice does not appear here, it is probably not API-available for your account or plan."
        ],
        body: `
        <div class="voice-login-row">
          <input id="elevenLabsApiKeyInput" type="password" value="${escapeHtml(apiKey)}" placeholder="Paste ElevenLabs API key">
          <button id="saveElevenLabsKeyBtn" type="button">Save key</button>
          <button id="loadElevenLabsVoicesBtn" type="button">Load voices</button>
        </div>
        ${voiceStatusHtml()}
        ${elevenLabsVoiceSections()}`,
      })}
    </div>`;
}

function refreshVoiceSettingsTab() {
  if (activeTab()?.type === "voice-settings") {
    summary.innerHTML = voiceSettingsHtml();
  }
}

function saveElevenLabsKey() {
  const existing = localStorage.getItem("ytElevenLabsApiKey") || "";
  const value = prompt("Paste your ElevenLabs API key. It will be saved on this Mac only.", existing);
  if (value === null) return;
  const cleaned = cleanElevenLabsApiKey(value);
  if (!cleaned) {
    localStorage.removeItem("ytElevenLabsApiKey");
    showToast("ElevenLabs key removed");
    return;
  }
  localStorage.setItem("ytElevenLabsApiKey", cleaned);
  showToast("ElevenLabs connected");
}

function hasAllowedAnimeVoiceFileType(file) {
  const name = (file?.name || "").toLowerCase();
  return allowedAnimeVoiceExtensions.some((extension) => name.endsWith(extension));
}

async function uploadAnimeVoice(file) {
  if (!file) return;
  if (!hasAllowedAnimeVoiceFileType(file)) {
    state.voiceStatus = {
      type: "unsupported_voice_file_type",
      message: animeVoiceFileTypeMessage
    };
    refreshVoiceSettingsTab();
    showToast(animeVoiceFileTypeMessage);
    return;
  }
  const apiKey = localStorage.getItem("ytElevenLabsApiKey") || "";
  if (!apiKey) {
    state.voiceStatus = {
      type: "anime_voice_not_configured",
      message: "Add your ElevenLabs API key before uploading a custom voice. Voice cloning also requires a paid ElevenLabs plan."
    };
    refreshVoiceSettingsTab();
    showToast("Add your ElevenLabs API key first");
    saveElevenLabsKey();
    return;
  }
  if (!confirm("Only upload a voice sample you own or have permission to use.")) return;
  const formData = new FormData();
  formData.append("file", file);
  formData.append("name", "WatchLess Anime Voice");
  formData.append("api_key", apiKey);
  state.voiceStatus = {
    type: "loading",
    message: "Uploading this voice sample to ElevenLabs and creating a custom voice on your paid ElevenLabs plan."
  };
  refreshVoiceSettingsTab();
  try {
    const response = await fetch(api.animeVoice, { method: "POST", body: formData });
    const data = await response.json();
    if (!response.ok || data.ok === false) throw new Error(data.error || "Could not upload voice.");
    if (!data.voice_id) throw new Error("Voice upload finished, but no voice ID was returned.");
    localStorage.setItem("ytAnimeVoiceId", data.voice_id);
    localStorage.setItem("ytAnimeVoiceName", "Uploaded anime voice");
    localStorage.setItem("ytNarrationMode", "elevenlabs");
    localStorage.setItem("ytNarrationVoice", "watchless-anime-ai");
    rememberRecentElevenLabsVoice(data.voice_id);
    state.voiceStatus = {
      type: "success",
      message: "Paid ElevenLabs custom voice uploaded and selected for narration."
    };
    refreshVoiceSettingsTab();
    showToast("Anime voice uploaded");
  } catch (error) {
    state.voiceStatus = {
      type: error.errorType || "anime_voice_upload_failed",
      message: error.message
    };
    refreshVoiceSettingsTab();
    showToast("Voice upload needs attention");
  } finally {
    if (animeVoiceFileInput) animeVoiceFileInput.value = "";
  }
}

async function ensureLocalVoiceCatalog() {
  if (state.localVoiceCatalog.length) return;
  try {
    const data = await requestJson(api.localVoiceCatalog);
    state.localVoiceCatalog = data.models || [];
  } catch (_) {}
}

function saveLocalVoiceServerSettings() {
  const value = (document.getElementById("localVoiceServerInput")?.value || defaultLocalVoiceServer).trim() || defaultLocalVoiceServer;
  localStorage.setItem("ytLocalVoiceServer", value);
  state.localVoiceStatus = {
    type: "success",
    message: "Local voice server address saved on this Mac."
  };
  refreshVoiceSettingsTab();
  showToast("Local voice server saved");
}

function saveLocalVoiceAssetsSettings() {
  const value = (document.getElementById("localVoiceAssetsRootInput")?.value || "").trim();
  if (value) localStorage.setItem("ytLocalVoiceAssetsRoot", value);
  else localStorage.removeItem("ytLocalVoiceAssetsRoot");
  state.localVoiceStatus = {
    type: "success",
    message: value ? "Local model folder saved on this Mac." : "Local model folder removed from this Mac."
  };
  refreshVoiceSettingsTab();
  showToast(value ? "Local folder saved" : "Local folder removed");
}

async function warmLocalVoiceModel() {
  const key = localVoiceSelectionKey();
  if (!key || warmedLocalVoiceKey === key) return;
  if (warmingLocalVoiceKey === key) return localVoiceWarmupPromise;
  const model = selectedLocalVoiceModel();
  if (!model) return;
  warmingLocalVoiceKey = key;
  state.localVoiceStatus = {
    type: "loading",
    message: `Warming ${model.name} so the first narration starts faster.`
  };
  refreshVoiceSettingsTab();
  const language = localVoiceLanguageForText(model);
  if (!localVoiceSupportsLanguage(model, language)) return;
  const payload = {
    text: localVoiceWarmupText(language),
    server_url: localVoiceServerUrl(),
    model_name: localStorage.getItem("ytLocalVoiceModelName") || model.name || "",
    speaker_name: localStorage.getItem("ytLocalVoiceSpeakerName") || model?.speakers?.[0]?.name || "",
    style: localStorage.getItem("ytLocalVoiceStyle") || model?.styles?.[0] || "Neutral",
    language
  };
  const warmupPromise = fetch(api.localVoiceNarration, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  }).then(async (response) => {
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.error || `Warm-up failed: ${response.status}`);
    }
    await response.blob();
    warmedLocalVoiceKey = key;
    state.localVoiceStatus = {
      type: "success",
      message: `${model.name} is ready. Narration should start faster now.`
    };
    refreshVoiceSettingsTab();
  }).catch((error) => {
    state.localVoiceStatus = {
      type: "local_voice_warmup_failed",
      message: localVoiceFriendlyError(error)
    };
    refreshVoiceSettingsTab();
  }).finally(() => {
    if (warmingLocalVoiceKey === key) warmingLocalVoiceKey = "";
    if (localVoiceWarmupPromise === warmupPromise) localVoiceWarmupPromise = null;
  });
  localVoiceWarmupPromise = warmupPromise;
  return warmupPromise;
}

function scheduleLocalVoiceWarmup() {
  clearTimeout(localVoiceWarmupTimer);
  localVoiceWarmupTimer = setTimeout(() => {
    warmLocalVoiceModel();
  }, 350);
}

function localVoiceFriendlyError(error) {
  if (error?.errorType === "watchless_backend_unreachable") {
    return error.message;
  }
  if (error?.errorType === "request_error" && /404/.test(error.message || "")) {
    return (
      "This WatchLess window is missing the local voice endpoint. " +
      "Close every WatchLess window, reopen the app from the correct WatchLess folder, then test the server again."
    );
  }
  return error?.message || "Local voice is not available right now.";
}

async function loadLocalVoiceModels(refresh = false) {
  const serverUrl = (document.getElementById("localVoiceServerInput")?.value || localVoiceServerUrl()).trim() || defaultLocalVoiceServer;
  const assetsRoot = (document.getElementById("localVoiceAssetsRootInput")?.value || localVoiceAssetsRoot()).trim();
  localStorage.setItem("ytLocalVoiceServer", serverUrl);
  if (assetsRoot) localStorage.setItem("ytLocalVoiceAssetsRoot", assetsRoot);
  state.localVoiceStatus = {
    type: "loading",
    message: refresh ? "Refreshing the local voice server model list." : "Checking the local voice server and loading available models."
  };
  refreshVoiceSettingsTab();
  try {
    await ensureLocalVoiceCatalog();
    const data = await requestJson(api.localVoiceStatus, {
      method: "POST",
      body: JSON.stringify({ server_url: serverUrl, assets_root: assetsRoot, refresh })
    });
    const models = data.server?.models || [];
    state.localVoiceModels = models;
    localStorage.setItem("ytLocalVoiceModels", JSON.stringify(models));
    if (models.length) {
      const savedModelName = localStorage.getItem("ytLocalVoiceModelName") || models[0].name;
      const savedModel = models.find((model) => model.name === savedModelName);
      const targetLanguage = detectedNarrationLanguage() === "ja" ? "JP" : "EN";
      const chosenModel = (
        savedModel && localVoiceSupportsLanguage(savedModel, targetLanguage)
          ? savedModel
          : models.find((model) => localVoiceSupportsLanguage(model, targetLanguage)) || savedModel || models[0]
      );
      localStorage.setItem("ytLocalVoiceModelName", chosenModel.name);
      if ((chosenModel.speakers || []).length) {
        const existingSpeaker = localStorage.getItem("ytLocalVoiceSpeakerName") || "";
        const speaker = chosenModel.speakers.find((item) => item.name === existingSpeaker) || chosenModel.speakers[0];
        localStorage.setItem("ytLocalVoiceSpeakerName", speaker.name);
      }
      if ((chosenModel.styles || []).length) {
        const existingStyle = localStorage.getItem("ytLocalVoiceStyle") || "";
        const style = chosenModel.styles.includes(existingStyle) ? existingStyle : chosenModel.styles[0];
        localStorage.setItem("ytLocalVoiceStyle", style);
      }
    }
    state.localVoiceStatus = {
      type: "success",
      message: models.length
        ? `Connected successfully. WatchLess found ${models.length} local voice model${models.length === 1 ? "" : "s"} on ${serverUrl}.`
        : `Connected to ${serverUrl}, but no local models were found yet.`
    };
    refreshVoiceSettingsTab();
    showToast(models.length ? "Local models loaded" : "No local models found");
    if (models.length) scheduleLocalVoiceWarmup();
  } catch (error) {
    state.localVoiceStatus = {
      type: error.errorType || "local_voice_error",
      message: localVoiceFriendlyError(error)
    };
    refreshVoiceSettingsTab();
    showToast("Local voice needs attention");
  }
}

async function downloadLocalVoiceModel(modelId) {
  const assetsRoot = (document.getElementById("localVoiceAssetsRootInput")?.value || localVoiceAssetsRoot()).trim();
  const serverUrl = (document.getElementById("localVoiceServerInput")?.value || localVoiceServerUrl()).trim() || defaultLocalVoiceServer;
  if (!assetsRoot) {
    state.localVoiceStatus = {
      type: "local_voice_missing_assets_root",
      message: "Save the local model folder first so WatchLess knows where to put the downloaded voice model."
    };
    refreshVoiceSettingsTab();
    showToast("Save local folder first");
    return;
  }
  localStorage.setItem("ytLocalVoiceAssetsRoot", assetsRoot);
  state.localVoiceStatus = {
    type: "loading",
    message: "Downloading the local voice model from Hugging Face into your model assets folder."
  };
  refreshVoiceSettingsTab();
  try {
    const data = await requestJson(api.localVoiceDownload, {
      method: "POST",
      body: JSON.stringify({
        model_id: modelId,
        assets_root: assetsRoot,
        server_url: serverUrl
      })
    });
    if (data.server?.models) {
      state.localVoiceModels = data.server.models;
      localStorage.setItem("ytLocalVoiceModels", JSON.stringify(data.server.models));
    }
    if (data.model?.folder) {
      localStorage.setItem("ytLocalVoiceModelName", data.model.folder);
      localStorage.setItem("ytNarrationMode", "local");
      localStorage.setItem("ytNarrationVoice", "watchless-local-ai");
    }
    state.localVoiceStatus = {
      type: "success",
      message: `${data.model?.name || "Local voice model"} downloaded. WatchLess refreshed the local model list${data.server ? "" : " next time you test the server"}.`
    };
    refreshVoiceSettingsTab();
    showToast("Local voice downloaded");
  } catch (error) {
    state.localVoiceStatus = {
      type: error.errorType || "local_voice_download_failed",
      message: error.message
    };
    refreshVoiceSettingsTab();
    showToast("Local download failed");
  }
}

function chooseLocalVoiceModel(modelName) {
  const models = savedLocalVoiceModels();
  const model = models.find((item) => item.name === modelName);
  localStorage.setItem("ytNarrationMode", "local");
  localStorage.setItem("ytNarrationVoice", "watchless-local-ai");
  localStorage.setItem("ytLocalVoiceModelName", modelName);
  if ((model?.speakers || []).length) localStorage.setItem("ytLocalVoiceSpeakerName", model.speakers[0].name);
  if ((model?.styles || []).length) localStorage.setItem("ytLocalVoiceStyle", model.styles[0]);
  refreshVoiceSettingsTab();
  showToast("Local voice selected");
  scheduleLocalVoiceWarmup();
}

function saveLocalVoiceDropdowns() {
  const speaker = document.getElementById("localVoiceSpeakerSelect")?.value || "";
  const style = document.getElementById("localVoiceStyleSelect")?.value || "";
  const previousKey = localVoiceSelectionKey();
  if (speaker) localStorage.setItem("ytLocalVoiceSpeakerName", speaker);
  if (style) localStorage.setItem("ytLocalVoiceStyle", style);
  if (previousKey && previousKey !== localVoiceSelectionKey()) {
    warmedLocalVoiceKey = "";
    warmingLocalVoiceKey = "";
  }
}

async function loadElevenLabsVoices() {
  const apiKey = cleanElevenLabsApiKey(document.getElementById("elevenLabsApiKeyInput")?.value || localStorage.getItem("ytElevenLabsApiKey") || "");
  if (!apiKey) {
    showToast("Paste your ElevenLabs API key first");
    return;
  }
  localStorage.setItem("ytElevenLabsApiKey", apiKey);
  state.voiceStatus = {
    type: "loading",
    message: "Checking the key and asking ElevenLabs for the voices available in this account."
  };
  refreshVoiceSettingsTab();
  showToast("Loading ElevenLabs voices");
  try {
    const data = await requestJson(api.elevenLabsVoices, {
      method: "POST",
      body: JSON.stringify({ api_key: apiKey })
    });
    localStorage.setItem("ytElevenLabsVoices", JSON.stringify(data.voices || []));
    state.voiceStatus = {
      type: "success",
      message: `Connected successfully. WatchLess found ${(data.voices || []).length} ElevenLabs voices for this account.`
    };
    refreshVoiceSettingsTab();
    showToast(`${(data.voices || []).length} ElevenLabs voices loaded`);
  } catch (error) {
    state.voiceStatus = {
      type: error.errorType || "elevenlabs_error",
      message: error.message
    };
    refreshVoiceSettingsTab();
    showToast("ElevenLabs needs attention");
  }
}

function saveElevenLabsKeyFromPage() {
  const input = document.getElementById("elevenLabsApiKeyInput");
  const value = cleanElevenLabsApiKey(input?.value || "");
  if (!value) {
    localStorage.removeItem("ytElevenLabsApiKey");
    localStorage.removeItem("ytElevenLabsVoices");
    state.voiceStatus = {
      type: "success",
      message: "ElevenLabs key removed from this Mac."
    };
    refreshVoiceSettingsTab();
    showToast("ElevenLabs key removed");
    return;
  }
  localStorage.setItem("ytElevenLabsApiKey", value);
  state.voiceStatus = {
    type: "success",
    message: "Key saved locally. Click Load voices to check it with ElevenLabs and choose a voice."
  };
  refreshVoiceSettingsTab();
  showToast("ElevenLabs key saved");
}

function chooseNativeVoice(key) {
  localStorage.setItem("ytNarrationMode", "device");
  localStorage.setItem("ytNarrationVoice", key);
  refreshVoiceSettingsTab();
  showToast("System voice selected");
}

function chooseElevenLabsVoice(voiceId, voiceName) {
  localStorage.setItem("ytNarrationMode", "elevenlabs");
  localStorage.setItem("ytAnimeVoiceId", voiceId);
  localStorage.setItem("ytAnimeVoiceName", voiceName || "ElevenLabs voice");
  localStorage.setItem("ytNarrationVoice", "watchless-anime-ai");
  rememberRecentElevenLabsVoice(voiceId);
  refreshVoiceSettingsTab();
  showToast("ElevenLabs voice selected");
}

function handleVoiceSettingsClick(event) {
  const sectionSummary = event.target.closest(".voice-section-summary");
  if (sectionSummary) {
    setTimeout(() => {
      const section = sectionSummary.closest(".voice-section");
      if (section?.dataset.voiceSection) {
        localStorage.setItem(`ytVoiceSectionOpen:${section.dataset.voiceSection}`, section.open ? "true" : "false");
      }
    }, 0);
    return;
  }
  const target = event.target.closest("button");
  if (!target) return;
  if (target.id === "saveLocalVoiceServerBtn") {
    saveLocalVoiceServerSettings();
    return;
  }
  if (target.id === "testLocalVoiceServerBtn") {
    loadLocalVoiceModels(false);
    return;
  }
  if (target.id === "saveLocalVoiceAssetsBtn") {
    saveLocalVoiceAssetsSettings();
    return;
  }
  if (target.id === "refreshLocalVoiceModelsBtn") {
    loadLocalVoiceModels(true);
    return;
  }
  if (target.id === "saveElevenLabsKeyBtn") {
    saveElevenLabsKeyFromPage();
    return;
  }
  if (target.id === "loadElevenLabsVoicesBtn") {
    loadElevenLabsVoices();
    return;
  }
  if (target.id === "uploadCustomVoiceBtn") {
    animeVoiceFileInput?.click();
    return;
  }
  if (target.dataset.voiceAction === "native") {
    chooseNativeVoice(target.dataset.voiceKey || target.value || "");
    return;
  }
  if (target.dataset.localDownload) {
    downloadLocalVoiceModel(target.dataset.localDownload);
    return;
  }
  if (target.dataset.localLanguageFilter) {
    localStorage.setItem("ytLocalVoiceLanguageFilter", target.dataset.localLanguageFilter);
    refreshVoiceSettingsTab();
    return;
  }
  if (target.dataset.localModel) {
    chooseLocalVoiceModel(target.dataset.localModel || "");
    return;
  }
  if (target.dataset.voiceAction === "elevenlabs") {
    chooseElevenLabsVoice(target.dataset.voiceId || target.value || "", target.dataset.voiceName || target.textContent.trim());
  }
}

function handleVoiceSettingsChange(event) {
  const target = event.target;
  if (target?.id === "localVoiceSpeakerSelect" || target?.id === "localVoiceStyleSelect") {
    saveLocalVoiceDropdowns();
    localStorage.setItem("ytNarrationMode", "local");
    localStorage.setItem("ytNarrationVoice", "watchless-local-ai");
    scheduleLocalVoiceWarmup();
  }
}

function handleZoom(event) {
  const key = event.key.toLowerCase();
  if ((event.metaKey || event.ctrlKey) && (key === "+" || key === "=")) {
    event.preventDefault();
    setAppZoom(appZoom + .06);
    return;
  }
  if ((event.metaKey || event.ctrlKey) && !event.shiftKey && key === "-") {
    event.preventDefault();
    setAppZoom(appZoom - .06);
    return;
  }
  if ((event.metaKey || event.ctrlKey) && key === "n") {
    event.preventDefault();
    createTab();
  }
  if ((event.metaKey || event.ctrlKey) && event.shiftKey && key === "t") {
    event.preventDefault();
    reopenClosedTab();
  }
}

function startResizeDrag(event, type) {
  event.preventDefault();
  if (type === "sidebar") dragging = true;
  if (type === "chat") chatDragging = true;
  document.body.classList.add("is-resizing");
}

resizer.addEventListener("mousedown", (event) => startResizeDrag(event, "sidebar"));
chatResizer?.addEventListener("mousedown", (event) => startResizeDrag(event, "chat"));
document.addEventListener("mouseup", () => {
  dragging = false;
  chatDragging = false;
  document.body.classList.remove("is-resizing");
});
window.addEventListener("blur", () => {
  dragging = false;
  chatDragging = false;
  document.body.classList.remove("is-resizing");
});
document.addEventListener("mousemove", (event) => {
  if (dragging && !sidebarCollapsed && window.innerWidth > 1150) {
    sidebarWidth = constrainedSidebarWidth(event.clientX);
    localStorage.setItem("ytSidebarWidth", String(sidebarWidth));
    applySidebarLayout();
  }
  if (chatDragging && !chatPanel.hidden && window.innerWidth > 1150) {
    chatWidth = constrainedChatWidth(window.innerWidth - event.clientX - 24);
    localStorage.setItem("ytChatWidth", String(chatWidth));
    applyChatLayout();
  }
});
window.addEventListener("resize", applySidebarLayout);
document.addEventListener("keydown", handleZoom, true);
urlInput.addEventListener("input", saveActiveDraft);
providerSelect.addEventListener("change", () => {
  syncProviderUi();
  testConnection();
});
modelSelect.addEventListener("change", handleModelSelectionChange);
testConnectionBtn.addEventListener("click", testConnection);
summarizeBtn.addEventListener("click", summarize);
copyBtn.addEventListener("click", copyResult);
guideBtn.addEventListener("click", createGuideTab);
speakBtn.addEventListener("click", toggleNarration);
voiceSettingsBtn?.addEventListener("click", createVoiceSettingsTab);
summary.addEventListener("click", handleVoiceSettingsClick);
summary.addEventListener("change", handleVoiceSettingsChange);
animeVoiceFileInput?.addEventListener("change", () => uploadAnimeVoice(animeVoiceFileInput.files[0]));
if ("speechSynthesis" in window) {
  speechSynthesis.addEventListener?.("voiceschanged", refreshVoiceSettingsTab);
}
chatBtn.addEventListener("click", () => toggleChatPanel());
chatCloseBtn.addEventListener("click", () => toggleChatPanel(false));
chatForm.addEventListener("submit", sendChatMessage);
donationBtn.addEventListener("click", openDonation);
feedbackEmailBtn?.addEventListener("click", copyFeedbackEmail);
zoomInBtn.addEventListener("click", () => setZoom(summaryZoom + .08));
zoomOutBtn.addEventListener("click", () => setZoom(summaryZoom - .08));
chatFileBtn.addEventListener("click", () => chatFileInput.click());
chatImageBtn.addEventListener("click", () => chatImageInput.click());
chatFileInput.addEventListener("change", () => attachChatFile(chatFileInput.files[0]));
chatImageInput.addEventListener("change", () => attachChatFile(chatImageInput.files[0]));
newTabBtn.addEventListener("click", () => createTab());
chromeTabs.addEventListener("wheel", handleChromeTabsWheel, { passive: false });
sidebarToggleBtn?.addEventListener("click", toggleSidebar);
sidebarRailActions.forEach((button) => button.addEventListener("click", () => openSidebarSection(button.dataset.sidebarTarget)));
loadModelBtn.addEventListener("click", loadSelectedModel);
unloadModelBtn.addEventListener("click", unloadLoadedModel);
viewPresetsBtn.addEventListener("click", async () => {
  presetDrawer.hidden = !presetDrawer.hidden;
  if (!presetDrawer.hidden) await loadPromptPresets();
});
savePresetBtn.addEventListener("click", saveCurrentAsPreset);
document.getElementById("savePromptBtn").addEventListener("click", savePromptPreset);
document.getElementById("resetPromptBtn").addEventListener("click", resetPromptPreset);
promptEditor.addEventListener("input", syncActivePromptPresetFromEditor);

const originalActivateTab = activateTab;
activateTab = async function activateTabWithHistory(tabId) {
  const tab = state.tabs.find((item) => item.id === tabId);
  if (tab && tab.type === "history" && tab.historyId && !tab.markdown && !tab.error) {
    await loadHistoryItem(tab);
  }
  originalActivateTab(tabId);
};

loadFrontendModules().then(() => {
  applyAppZoom();
  applyZoom();
  applyChatLayout();
  applySidebarLayout();
  if (!donationBtn.dataset.url) {
    donationBtn.disabled = true;
    donationBtn.title = "Donation link is not configured yet.";
  }
  createGuideTab();
  loadSettings().then(refreshModels);
  loadPromptPreset();
  loadPromptPresets();
  loadHistoryTabs();
});
