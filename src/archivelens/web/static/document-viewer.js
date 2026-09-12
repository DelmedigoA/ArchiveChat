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
  textLayer.style.setProperty("--total-scale-factor", scale);
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
  const spans = [...textLayer.querySelectorAll("span")].filter((span) => normalizeText(span.textContent));
  const records = [];
  let offset = 0;
  spans.forEach((span) => {
    const normalized = normalizeWithMap(span.textContent);
    records.push({ span, ...normalized, start: offset, end: offset + normalized.text.length });
    offset += normalized.text.length + 1;
  });
  const normalizedPage = records.map((record) => record.text).join(" ");
  const rangesBySpan = new Map();
  for (const quote of quotes) {
    const normalizedQuote = normalizeText(quote);
    const start = normalizedPage.indexOf(normalizedQuote);
    if (start < 0) continue;
    const end = start + normalizedQuote.length;
    records.forEach((record) => {
      const localStart = Math.max(start, record.start) - record.start;
      const localEnd = Math.min(end, record.end) - record.start;
      if (localStart >= localEnd) return;
      const rawStart = record.map[localStart];
      const rawEnd = record.map[localEnd - 1] + 1;
      const ranges = rangesBySpan.get(record.span) || [];
      ranges.push([rawStart, rawEnd]);
      rangesBySpan.set(record.span, ranges);
    });
  }
  for (const record of records) {
    const ranges = mergeRanges(rangesBySpan.get(record.span) || []);
    if (ranges.length) {
      wrapHighlightRanges(record.span, ranges);
    }
  }
}

function normalizeWithMap(text) {
  let normalized = "";
  const map = [];
  for (let index = 0; index < String(text || "").length; index += 1) {
    const character = String(text || "")[index];
    if (/\s/.test(character)) {
      if (normalized && !normalized.endsWith(" ")) {
        normalized += " ";
        map.push(index);
      }
      continue;
    }
    normalized += character;
    map.push(index);
  }
  while (normalized.endsWith(" ")) {
    normalized = normalized.slice(0, -1);
    map.pop();
  }
  return { text: normalized, map };
}

function mergeRanges(ranges) {
  return ranges.sort((left, right) => left[0] - right[0]).reduce((merged, range) => {
    const previous = merged.at(-1);
    if (previous && range[0] <= previous[1]) {
      previous[1] = Math.max(previous[1], range[1]);
    } else {
      merged.push([...range]);
    }
    return merged;
  }, []);
}

function wrapHighlightRanges(span, ranges) {
  const text = span.textContent;
  span.replaceChildren();
  let cursor = 0;
  for (const [start, end] of ranges) {
    if (start > cursor) span.append(document.createTextNode(text.slice(cursor, start)));
    const mark = document.createElement("mark");
    mark.className = "textLayer__highlight";
    mark.textContent = text.slice(start, end);
    span.append(mark);
    cursor = end;
  }
  if (cursor < text.length) span.append(document.createTextNode(text.slice(cursor)));
}

function normalizeText(text) {
  return normalizeWithMap(text).text;
}

function setDocumentStatus(message, isError = false) {
  els.documentStatus.textContent = message;
  els.documentStatus.classList.toggle("document-status--error", isError);
}

export { openDocumentViewer, closeDocumentViewer, changeDocumentPage, changeDocumentZoom, showDocumentPage, beginWorkspaceResize, handleDividerKeydown, renderDocumentPage };
