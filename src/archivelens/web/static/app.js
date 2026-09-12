// Page entry point: connect user interactions and show the opening message.
import { state, els } from "./state.js";
import { ask, appendMessage, resetConversation } from "./chat.js";
import { openItemModal, closeItemModal, copyItemUrl } from "./item-modal.js";
import {
  openDocumentViewer, closeDocumentViewer, changeDocumentPage, changeDocumentZoom,
  showDocumentPage, beginWorkspaceResize, handleDividerKeydown, renderDocumentPage,
} from "./document-viewer.js";

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

els.resetConversation.addEventListener("click", resetConversation);

document.addEventListener("click", async (event) => {
  const documentCitation = event.target.closest("[data-document-page]");
  if (documentCitation) {
    try {
      state.viewer.evidence = JSON.parse(documentCitation.dataset.documentEvidence || "[]");
    } catch {
      state.viewer.evidence = [];
    }
    state.viewer.evidencePage = Number(documentCitation.dataset.documentPage);
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
