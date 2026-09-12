// Lazy PDF loading, page/zoom controls, and the resizable workspace.
import { state, els } from "./state.js";

function setWorkspaceSplit(percent) {
  state.splitPercent = Math.max(30, Math.min(70, percent));
  els.workspace.style.setProperty("--chat-pane-width", `${state.splitPercent}%`);
  sessionStorage.setItem("archivelens:workspace-split", String(state.splitPercent));
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
  const textContent = await page.getTextContent();
  const pixelRatio = window.devicePixelRatio || 1;
  const context = els.documentCanvas.getContext("2d");
  els.documentCanvas.width = Math.floor(viewport.width * pixelRatio);
  els.documentCanvas.height = Math.floor(viewport.height * pixelRatio);
  els.documentCanvas.style.width = `${Math.floor(viewport.width)}px`;
  els.documentCanvas.style.height = `${Math.floor(viewport.height)}px`;
  const pageLayer = document.getElementById("document-page-layer");
  const textLayer = document.getElementById("document-text-layer");
  pageLayer.style.width = `${Math.floor(viewport.width)}px`;
  pageLayer.style.height = `${Math.floor(viewport.height)}px`;
  textLayer.replaceChildren();
  textLayer.style.setProperty("--scale-factor", scale);
  const textLayerTask = new state.viewer.pdfjs.TextLayer({
    textContentSource: textContent,
    container: textLayer,
    viewport,
  });
  await textLayerTask.render();
  await page.render({ canvasContext: context, viewport, transform: [pixelRatio, 0, 0, pixelRatio, 0, 0] }).promise;
  applyEvidenceHighlights(textContent.items, state.viewer.page === state.viewer.evidencePage ? state.viewer.evidence : []);
  setDocumentStatus(`Page ${state.viewer.page} of ${pdf.numPages}`);
}

function applyEvidenceHighlights(items, quotes) {
  const textLayer = document.getElementById("document-text-layer");
  const spans = [...textLayer.querySelectorAll("span")];
  const normalizedItems = items.map((item) => normalizeText(item.str));
  const normalizedPage = normalizedItems.filter(Boolean).join(" ");
  const itemOffsets = [];
  let offset = 0;
  normalizedItems.forEach((text, index) => {
    if (!text) return;
    itemOffsets[index] = { start: offset, end: offset + text.length };
    offset += text.length + 1;
  });
  const matchedItems = new Set();
  for (const quote of quotes) {
    const start = normalizedPage.indexOf(normalizeText(quote));
    if (start < 0) continue;
    const end = start + normalizeText(quote).length;
    itemOffsets.forEach((range, index) => {
      if (range && range.start < end && range.end > start) matchedItems.add(index);
    });
  }
  let itemIndex = 0;
  for (const span of spans) {
    const spanText = normalizeText(span.textContent);
    if (!spanText) continue;
    while (itemIndex < normalizedItems.length && !normalizedItems[itemIndex]) itemIndex += 1;
    span.classList.toggle("textLayer__highlight", matchedItems.has(itemIndex));
    itemIndex += 1;
  }
}

function normalizeText(text) {
  return String(text || "").replace(/\s+/g, " ").trim();
}

function setDocumentStatus(message, isError = false) {
  els.documentStatus.textContent = message;
  els.documentStatus.classList.toggle("document-status--error", isError);
}

export { openDocumentViewer, closeDocumentViewer, changeDocumentPage, changeDocumentZoom, showDocumentPage, beginWorkspaceResize, handleDividerKeydown, renderDocumentPage };
