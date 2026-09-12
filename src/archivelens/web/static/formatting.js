// Answer formatting, citation markup, and escaping; no DOM or network access.

function isHebrewDominant(text) {
  const letters = text.match(/[\p{L}\p{M}]/gu) || [];
  if (!letters.length) {
    return false;
  }
  const hebrewLetters = letters.filter((character) => /[\u0590-\u05FF]/u.test(character));
  return hebrewLetters.length > letters.length / 2;
}

function renderAnswer(answer, items) {
  const { text: answerText, evidence } = extractDocumentEvidence(answer);
  const byUrl = new Map();
  for (const item of items) {
    if (item.url) {
      byUrl.set(normalizeUrl(item.url), item);
    }
  }

  const citationNumbers = new Map();
  let nextCitationNumber = 1;
  const escaped = escapeHtml(answerText);
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
  return renderDocumentCitations(linked, evidence)
    .split(/\n{2,}/)
    .map((paragraph) => `<p>${paragraph.replace(/\n/g, "<br>")}</p>`)
    .join("");
}

function renderDocumentCitations(text, evidence = new Map()) {
  const citationPattern = /(\(?\s*Bearing\s+Witness\s*,\s*p{1,2}\.?\s*)(\d+)(?:\s*(?:–|—|-|to)\s*(\d+))?(\s*\)?)/gi;
  return text.replace(citationPattern, (match, prefix, start, end, suffix) => {
    const firstPage = Number(start);
    const lastPage = end ? Number(end) : firstPage;
    if (!Number.isInteger(firstPage) || firstPage < 1 || lastPage < firstPage) {
      return match;
    }
    const pageEvidence = evidence.get(firstPage) || [];
    const evidenceAttribute = pageEvidence.length
      ? ` data-document-evidence="${escapeAttribute(JSON.stringify(pageEvidence))}"`
      : "";
    return `<button class="document-citation-link" type="button" data-document-page="${firstPage}"${evidenceAttribute} title="Open Bearing Witness PDF at page ${firstPage}" aria-label="Open Bearing Witness PDF at page ${firstPage}">${prefix}${start}${end ? `–${end}` : ""}${suffix}</button>`;
  });
}

function extractDocumentEvidence(answer) {
  const evidence = new Map();
  const pattern = /\[\[BW_EVIDENCE\s+page=(\d+)\]\]([\s\S]*?)\[\[\/BW_EVIDENCE\]\]/g;
  const text = String(answer || "").replace(pattern, (match, page, quote) => {
    const pageNumber = Number(page);
    const value = quote.trim();
    if (Number.isInteger(pageNumber) && pageNumber > 0 && value) {
      const existing = evidence.get(pageNumber) || [];
      if (existing.length < 3 && !existing.includes(value)) {
        existing.push(value);
        evidence.set(pageNumber, existing);
      }
    }
    return value;
  });
  return { text, evidence };
}

function renderInlineMarkdown(text) {
  return text
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/__([^_]+)__/g, '<strong>$1</strong>')
    .replace(/(^|\s)\*([^*]+)\*/g, '$1<em>$2</em>')
    .replace(/(^|\s)_([^_]+)_/g, '$1<em>$2</em>');
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

export { isHebrewDominant, renderAnswer, renderDocumentCitations, renderInlineMarkdown, normalizeUrl, escapeHtml, escapeAttribute, extractDocumentEvidence };
