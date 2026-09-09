const state = {
  items: new Map(),
  busy: false,
  splitPercent: Number(sessionStorage.getItem("archivechat:workspace-split")) || 50,
  viewer: {
    config: null,
    pdfjs: null,
    document: null,
    page: 1,
    zoom: 1,
    loading: null,
  },
};

const els = {
  composer: document.getElementById("composer"),
  question: document.getElementById("question"),
  messages: document.getElementById("messages"),
  status: document.getElementById("status"),
  workspace: document.getElementById("workspace"),
  divider: document.getElementById("workspace-divider"),
  documentPane: document.getElementById("document-pane"),
  documentClose: document.getElementById("document-close"),
  documentTitle: document.getElementById("document-title"),
  documentVersion: document.getElementById("document-version"),
  documentStatus: document.getElementById("document-status"),
  documentCanvas: document.getElementById("document-canvas"),
  documentCanvasWrap: document.getElementById("document-canvas-wrap"),
  documentPage: document.getElementById("document-page"),
  documentPageCount: document.getElementById("document-page-count"),
  documentPrevious: document.getElementById("document-previous"),
  documentNext: document.getElementById("document-next"),
  documentZoomOut: document.getElementById("document-zoom-out"),
  documentZoomIn: document.getElementById("document-zoom-in"),
};

els.composer.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (state.busy) {
    return;
  }
  const question = els.question.value.trim();
  if (!question) {
    return;
  }
  els.question.value = "";
  appendMessage("user", question);
  await ask(question);
});

els.question.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    els.composer.requestSubmit();
  }
});

document.addEventListener("click", async (event) => {
  const documentCitation = event.target.closest("[data-document-page]");
  if (documentCitation) {
    await openDocumentViewer(Number(documentCitation.dataset.documentPage));
    return;
  }

  const sourceButton = event.target.closest("[data-item-id]");
  if (sourceButton) {
    const item = state.items.get(sourceButton.dataset.itemId);
    if (item) {
      openItemModal(item);
    }
    return;
  }

  const shareButton = event.target.closest("[data-share-item]");
  if (shareButton) {
    await copyItemUrl(shareButton.dataset.shareItem);
    return;
  }

  const modal = document.getElementById("item-modal");
  if (modal && (event.target === modal || event.target.closest("[data-modal-close]"))) {
    closeItemModal();
  }
});

els.documentClose.addEventListener("click", closeDocumentViewer);
els.documentPrevious.addEventListener("click", () => changeDocumentPage(-1));
els.documentNext.addEventListener("click", () => changeDocumentPage(1));
els.documentZoomOut.addEventListener("click", () => changeDocumentZoom(-0.15));
els.documentZoomIn.addEventListener("click", () => changeDocumentZoom(0.15));
els.documentPage.addEventListener("change", () => showDocumentPage(Number(els.documentPage.value)));
els.divider.addEventListener("pointerdown", beginWorkspaceResize);
els.divider.addEventListener("keydown", handleDividerKeydown);
window.addEventListener("resize", () => {
  if (state.viewer.document) {
    renderDocumentPage();
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    closeItemModal();
  }
});

const openingSentences = [
  "Ask a question about the archive, the document, or the evidence.",
  "Explore the archive through questions about events, sources, patterns, and context.",
  "Search the archive by asking about a claim, event, source, or theme.",
  "Ask about Gaza, the Bearing Witness document, or the materials collected in the archive.",
  "Start with a question about what happened, how it was documented, or what the sources show.",
];

appendMessage("assistant", openingSentences[Math.floor(Math.random() * openingSentences.length)]);

async function ask(question) {
  setBusy(true);
  const streamState = createStreamState();
  try {
    const response = await fetch("/api/chat/stream", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
      },
      body: JSON.stringify({ question }),
    });
    if (!response.ok || !response.body) {
      const payload = await response.json().catch(() => ({}));
      streamState.node.remove();
      appendMessage("assistant", payload.detail || payload.error || "Chat failed.");
      return;
    }
    await readChatStream(response.body, streamState);
  } catch (error) {
    streamState.node.remove();
    appendMessage("assistant", `Request failed: ${error.message}`);
  } finally {
    setBusy(false);
  }
}

function setBusy(value) {
  state.busy = value;
  els.status.textContent = "Ready";
  els.composer.querySelector("button").disabled = value;
}

async function readChatStream(body, streamState) {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split("\n\n");
    buffer = events.pop() || "";
    for (const eventText of events) {
      handleStreamEvent(parseServerSentEvent(eventText), streamState);
    }
  }
  if (buffer.trim()) {
    handleStreamEvent(parseServerSentEvent(buffer), streamState);
  }
}

function parseServerSentEvent(text) {
  const event = { event: "message", data: {} };
  const dataLines = [];
  for (const line of text.split("\n")) {
    if (line.startsWith("event: ")) {
      event.event = line.slice(7).trim();
    } else if (line.startsWith("data: ")) {
      dataLines.push(line.slice(6));
    }
  }
  if (dataLines.length) {
    event.data = JSON.parse(dataLines.join("\n"));
  }
  return event;
}

function handleStreamEvent(event, streamState) {
  if (event.event === "status") {
    updateStreamingStatus(streamState, event.data.message || "Reviewing material…");
  } else if (event.event === "item") {
    addStreamItem(streamState, event.data.item);
  } else if (event.event === "delta") {
    appendStreamingText(streamState, event.data.text || "");
  } else if (event.event === "final") {
    for (const item of event.data.items || []) {
      addStreamItem(streamState, item);
    }
    replaceWithAssistantMessage(streamState, event.data.answer || "");
  } else if (event.event === "error") {
    streamState.node.remove();
    appendMessage("assistant", event.data.detail || event.data.message || "Chat failed.");
  }
}

function appendMessage(role, text) {
  const node = document.createElement("article");
  node.className = `message message--${role}`;
  setMessageDirection(node, text);
  node.textContent = text;
  els.messages.appendChild(node);
  node.scrollIntoView({ block: "end" });
}

function appendAssistantMessage(answer, items) {
  const node = document.createElement("article");
  node.className = "message message--assistant";
  setMessageDirection(node, answer);
  node.innerHTML = renderAnswer(answer, items);
  els.messages.appendChild(node);
  node.scrollIntoView({ block: "end" });
}

function createStreamState() {
  const node = document.createElement("article");
  node.className = "message message--assistant message--streaming";
  const streamState = {
    node,
    rawAnswer: "",
    items: [],
    itemIds: new Set(),
    hasAnswerText: false,
  };
  updateStreamingStatus(streamState, "Reviewing material…");
  els.messages.appendChild(node);
  node.scrollIntoView({ block: "end" });
  return streamState;
}

function updateStreamingStatus(streamState, message) {
  if (streamState.hasAnswerText) {
    return;
  }
  streamState.node.innerHTML = `<span class="message-status">${escapeHtml(message)}</span>`;
}

function addStreamItem(streamState, item) {
  if (!item || !item.item_id || streamState.itemIds.has(item.item_id)) {
    return;
  }
  streamState.itemIds.add(item.item_id);
  streamState.items.push(item);
  state.items.set(item.item_id, item);
  renderStreamingAnswer(streamState);
}

function appendStreamingText(streamState, text) {
  if (!text) {
    return;
  }
  streamState.hasAnswerText = true;
  streamState.rawAnswer += text;
  renderStreamingAnswer(streamState);
}

function renderStreamingAnswer(streamState) {
  if (!streamState.hasAnswerText) {
    return;
  }
  setMessageDirection(streamState.node, streamState.rawAnswer);
  streamState.node.innerHTML = renderAnswer(streamState.rawAnswer, streamState.items);
  streamState.node.scrollIntoView({ block: "end" });
}

function replaceWithAssistantMessage(streamState, answer) {
  streamState.node.classList.remove("message--streaming");
  streamState.rawAnswer = answer;
  streamState.hasAnswerText = true;
  renderStreamingAnswer(streamState);
}

function setMessageDirection(node, text) {
  const isRtl = isHebrewDominant(text);
  node.dir = isRtl ? "rtl" : "ltr";
  node.classList.toggle("message--rtl", isRtl);
}

function isHebrewDominant(text) {
  const letters = text.match(/[\p{L}\p{M}]/gu) || [];
  if (!letters.length) {
    return false;
  }
  const hebrewLetters = letters.filter((character) => /[\u0590-\u05FF]/u.test(character));
  return hebrewLetters.length > letters.length / 2;
}

function renderAnswer(answer, items) {
  const byUrl = new Map();
  for (const item of items) {
    if (item.url) {
      byUrl.set(normalizeUrl(item.url), item);
    }
  }

  const citationNumbers = new Map();
  let nextCitationNumber = 1;
  const escaped = escapeHtml(answer);
  const formatted = renderInlineMarkdown(escaped);
  const linked = formatted.replace(/\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g, (match, label, url) => {
    const item = byUrl.get(normalizeUrl(url));
    if (!item) {
      return `<a href="${escapeAttribute(url)}" target="_blank" rel="noreferrer">${label}</a>`;
    }

    if (!citationNumbers.has(item.item_id)) {
      citationNumbers.set(item.item_id, nextCitationNumber);
      nextCitationNumber += 1;
    }
    const number = citationNumbers.get(item.item_id);
    const title = item.title || label || `Source ${number}`;
    return `<button class="citation-link" type="button" data-item-id="${escapeAttribute(item.item_id)}" title="${escapeAttribute(title)}" aria-label="Open source ${number}: ${escapeAttribute(title)}">[${number}]</button>`;
  });
  return renderDocumentCitations(linked)
    .split(/\n{2,}/)
    .map((paragraph) => `<p>${paragraph.replace(/\n/g, "<br>")}</p>`)
    .join("");
}

function renderDocumentCitations(text) {
  const citationPattern = /(\(?\s*Bearing\s+Witness\s*,\s*p{1,2}\.?\s*)(\d+)(?:\s*(?:–|—|-|to)\s*(\d+))?(\s*\)?)/gi;
  return text.replace(citationPattern, (match, prefix, start, end, suffix) => {
    const firstPage = Number(start);
    const lastPage = end ? Number(end) : firstPage;
    if (!Number.isInteger(firstPage) || firstPage < 1 || lastPage < firstPage) {
      return match;
    }
    return `<button class="document-citation-link" type="button" data-document-page="${firstPage}" title="Open Bearing Witness PDF at page ${firstPage}" aria-label="Open Bearing Witness PDF at page ${firstPage}">${prefix}${start}${end ? `–${end}` : ""}${suffix}</button>`;
  });
}

function setWorkspaceSplit(percent) {
  state.splitPercent = Math.max(30, Math.min(70, percent));
  els.workspace.style.setProperty("--chat-pane-width", `${state.splitPercent}%`);
  sessionStorage.setItem("archivechat:workspace-split", String(state.splitPercent));
}

function openWorkspace() {
  els.workspace.classList.add("workspace--viewer-open");
  els.documentPane.setAttribute("aria-hidden", "false");
  setWorkspaceSplit(state.splitPercent);
}

function closeDocumentViewer() {
  els.workspace.classList.remove("workspace--viewer-open");
  els.documentPane.setAttribute("aria-hidden", "true");
  els.question.focus();
}

function beginWorkspaceResize(event) {
  if (!els.workspace.classList.contains("workspace--viewer-open")) {
    return;
  }
  event.preventDefault();
  els.divider.setPointerCapture(event.pointerId);
  const resize = (moveEvent) => {
    const bounds = els.workspace.getBoundingClientRect();
    setWorkspaceSplit(((moveEvent.clientX - bounds.left) / bounds.width) * 100);
  };
  const finish = () => {
    els.divider.removeEventListener("pointermove", resize);
    els.divider.removeEventListener("pointerup", finish);
    els.divider.removeEventListener("pointercancel", finish);
    if (state.viewer.document) {
      renderDocumentPage();
    }
  };
  els.divider.addEventListener("pointermove", resize);
  els.divider.addEventListener("pointerup", finish);
  els.divider.addEventListener("pointercancel", finish);
}

function handleDividerKeydown(event) {
  if (!els.workspace.classList.contains("workspace--viewer-open")) {
    return;
  }
  if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
    event.preventDefault();
    setWorkspaceSplit(state.splitPercent + (event.key === "ArrowLeft" ? -5 : 5));
    if (state.viewer.document) {
      renderDocumentPage();
    }
  }
}

async function openDocumentViewer(page) {
  openWorkspace();
  setDocumentStatus("Loading Bearing Witness document…");
  try {
    const config = await getDocumentConfig();
    if (!config.pdf_url) {
      throw new Error("The Bearing Witness PDF is not configured for this deployment.");
    }
    els.documentTitle.textContent = config.title || "Bearing Witness – Gaza";
    els.documentVersion.textContent = config.version || "";
    await loadPdfDocument(config.pdf_url);
    await showDocumentPage(page);
  } catch (error) {
    setDocumentStatus(error.message || "The document could not be loaded.", true);
  }
}

async function getDocumentConfig() {
  if (state.viewer.config) {
    return state.viewer.config;
  }
  const response = await fetch("/api/document-config");
  if (!response.ok) {
    throw new Error("The document viewer configuration could not be loaded.");
  }
  state.viewer.config = await response.json();
  return state.viewer.config;
}

async function loadPdfDocument(url) {
  if (state.viewer.document && state.viewer.url === url) {
    return state.viewer.document;
  }
  if (!state.viewer.loading) {
    state.viewer.loading = import("/static/vendor/pdfjs/pdf.mjs")
      .then(async (pdfjs) => {
        pdfjs.GlobalWorkerOptions.workerSrc = "/static/vendor/pdfjs/pdf.worker.mjs";
        state.viewer.pdfjs = pdfjs;
        state.viewer.document = await pdfjs.getDocument({ url, rangeChunkSize: 65536 }).promise;
        state.viewer.url = url;
        return state.viewer.document;
      })
      .finally(() => {
        state.viewer.loading = null;
      });
  }
  return state.viewer.loading;
}

async function showDocumentPage(page) {
  const pdf = state.viewer.document;
  if (!pdf) {
    return;
  }
  state.viewer.page = Math.max(1, Math.min(pdf.numPages, Math.round(page) || 1));
  els.documentPage.value = String(state.viewer.page);
  els.documentPage.max = String(pdf.numPages);
  els.documentPageCount.textContent = `of ${pdf.numPages}`;
  await renderDocumentPage();
}

async function changeDocumentPage(delta) {
  await showDocumentPage(state.viewer.page + delta);
}

async function changeDocumentZoom(delta) {
  state.viewer.zoom = Math.max(0.6, Math.min(2.5, state.viewer.zoom + delta));
  await renderDocumentPage();
}

async function renderDocumentPage() {
  const pdf = state.viewer.document;
  if (!pdf) {
    return;
  }
  setDocumentStatus(`Rendering page ${state.viewer.page}…`);
  const page = await pdf.getPage(state.viewer.page);
  const baseViewport = page.getViewport({ scale: 1 });
  const availableWidth = Math.max(280, els.documentCanvasWrap.clientWidth - 28);
  const scale = Math.min(availableWidth / baseViewport.width, 2) * state.viewer.zoom;
  const viewport = page.getViewport({ scale });
  const pixelRatio = window.devicePixelRatio || 1;
  const context = els.documentCanvas.getContext("2d");
  els.documentCanvas.width = Math.floor(viewport.width * pixelRatio);
  els.documentCanvas.height = Math.floor(viewport.height * pixelRatio);
  els.documentCanvas.style.width = `${Math.floor(viewport.width)}px`;
  els.documentCanvas.style.height = `${Math.floor(viewport.height)}px`;
  await page.render({ canvasContext: context, viewport, transform: [pixelRatio, 0, 0, pixelRatio, 0, 0] }).promise;
  setDocumentStatus(`Page ${state.viewer.page} of ${pdf.numPages}`);
}

function setDocumentStatus(message, isError = false) {
  els.documentStatus.textContent = message;
  els.documentStatus.classList.toggle("document-status--error", isError);
}
function renderInlineMarkdown(text) {
  return text
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/__([^_]+)__/g, '<strong>$1</strong>')
    .replace(/(^|\s)\*([^*]+)\*/g, '$1<em>$2</em>')
    .replace(/(^|\s)_([^_]+)_/g, '$1<em>$2</em>');
}

function openItemModal(item) {
  closeItemModal();
  const catalog = item.catalog || {};
  const sourceUrl = item.url || catalog.link || "";
  const modal = document.createElement("div");
  modal.className = "item-modal";
  modal.id = "item-modal";
  modal.innerHTML = `
    <div class="item-modal__panel" role="dialog" aria-modal="true" aria-labelledby="item-modal-title">
      <button class="item-modal__close" type="button" data-modal-close aria-label="Close">×</button>
      <div class="item-modal__body">
        <h2 id="item-modal-title">${escapeHtml(item.title || catalog.english_title || "Untitled item")}</h2>
        ${item.hebrew_title ? `<div class="item-modal__hebrew" dir="rtl">${escapeHtml(item.hebrew_title)}</div>` : ""}
        <div class="item-modal__meta">${renderMeta(catalog)}</div>
        ${renderIconChipRow("location", splitValues(catalog.location), "Location")}
        ${renderIconChipRow("person", catalog.figures_tags, "Figures")}
        ${renderEventDate(catalog)}
        <p class="item-modal__summary">${escapeHtml(item.description || item.hebrew_description || catalog.english_description || "")}</p>
        ${renderCatalogChips(catalog)}
        <div class="item-modal__published">${renderPublished(catalog)}</div>
      </div>
      <div class="item-modal__actions">
        <button class="item-modal__secondary" type="button" data-share-item="${escapeAttribute(item.item_id)}">Share <span aria-hidden="true">↗</span></button>
        <button class="item-modal__secondary" type="button">Found an issue? <span aria-hidden="true">⚑</span></button>
        ${sourceUrl ? `<a class="item-modal__primary" href="${escapeAttribute(sourceUrl)}" target="_blank" rel="noreferrer">View Item <span aria-hidden="true">↗</span></a>` : ""}
      </div>
    </div>
  `;
  document.body.appendChild(modal);
  document.body.classList.add("has-modal-open");
}
function closeItemModal() {
  const modal = document.getElementById("item-modal");
  if (modal) {
    modal.remove();
  }
  document.body.classList.remove("has-modal-open");
}

function renderMeta(catalog) {
  const values = [
    catalog.type,
    formatList(catalog.media),
    formatList(catalog.language),
    catalog.id ? `Record #${catalog.id}` : "",
  ].filter(Boolean);
  return values.map(escapeHtml).join(" | ");
}

function renderIconChipRow(kind, values, label) {
  if (!Array.isArray(values) || !values.length) {
    return "";
  }
  const icon = kind === "location" ? "📍" : "👤";
  return `
    <div class="item-modal__icon-row" aria-label="${escapeAttribute(label)}">
      <span class="item-modal__row-icon" aria-hidden="true">${icon}</span>
      <div class="item-modal__row-chips">
        ${values.map((value) => `<span class="chip chip--neutral">${escapeHtml(value)}</span>`).join("")}
      </div>
    </div>
  `;
}

function renderEventDate(catalog) {
  const eventDate = formatDateRange(catalog.event_date_from, catalog.event_date_to);
  if (!eventDate) {
    return "";
  }
  return `
    <div class="item-modal__event-date">
      <span aria-hidden="true">▣</span>
      <span>Event Date: ${escapeHtml(eventDate)}</span>
    </div>
  `;
}

function renderCatalogChips(catalog) {
  const chips = [
    ...chipItems(catalog.theme_tags, "theme"),
    ...chipItems(catalog.countries_and_organizations_tags, "organization"),
    ...chipItems(catalog.locations_tags, "location"),
    ...chipItems(catalog.figures_tags, "figure"),
  ];
  if (!chips.length) {
    return "";
  }
  return `<div class="item-modal__chips">${chips.join("")}</div>`;
}

function chipItems(values, kind) {
  if (!Array.isArray(values)) {
    return [];
  }
  return values.map((value) => `<span class="chip chip--${kind}">${escapeHtml(value)}</span>`);
}

function renderPublished(catalog) {
  const parts = [catalog.platform, catalog.published_date].filter(Boolean);
  if (!parts.length) {
    return "";
  }
  return `Published: ${parts.map(escapeHtml).join(", ")}`;
}

function formatList(values) {
  return Array.isArray(values) ? values.join(", ") : values;
}

function splitValues(value) {
  if (Array.isArray(value)) {
    return value.filter(Boolean);
  }
  if (!value) {
    return [];
  }
  return String(value)
    .split(/;|,/)
    .map((part) => part.trim())
    .filter(Boolean);
}

function formatDateRange(from, to) {
  if (!from && !to) {
    return "";
  }
  if (from && to && from !== to) {
    return `${formatDate(from)} - ${formatDate(to)}`;
  }
  return formatDate(from || to);
}

function formatDate(value) {
  if (!value) {
    return "";
  }
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  return date.toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" });
}

async function copyItemUrl(itemId) {
  const item = state.items.get(itemId);
  const url = item?.url || item?.catalog?.link;
  if (!url || !navigator.clipboard) {
    return;
  }
  await navigator.clipboard.writeText(url);
}

function normalizeUrl(url) {
  return String(url || "").replace(/\/$/, "");
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function escapeAttribute(value) {
  return escapeHtml(value).replaceAll("`", "&#096;");
}
