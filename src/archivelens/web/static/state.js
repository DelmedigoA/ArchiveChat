// Shared page state and DOM references. Imported once by the UI modules.

export const state = {
  items: new Map(),
  busy: false,
  splitPercent: Number(sessionStorage.getItem("archivelens:workspace-split")) || 50,
  viewer: {
    config: null,
    pdfjs: null,
    document: null,
    page: 1,
    zoom: 1,
    loading: null,
  },
};

export const els = {
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
