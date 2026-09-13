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
  const renderArchiveCitation = (itemId) => {
    const item = byId.get(itemId);
    if (!item) {
      return "";
    }
    if (!citationNumbers.has(item.item_id)) {
      citationNumbers.set(item.item_id, nextCitationNumber);
      nextCitationNumber += 1;
    }
    const number = citationNumbers.get(item.item_id);
    const title = item.title || `Source ${number}`;
    return `<button class="citation-link" type="button" data-item-id="${escapeAttribute(item.item_id)}" title="${escapeAttribute(title)}" aria-label="Open source ${number}: ${escapeAttribute(title)}">[${number}]</button>`;
  };
  const byId = new Map(items.map((item) => [item.item_id, item]));
  const renderInline = (value) => {
    const formatted = renderInlineMarkdown(escapeHtml(value));
    return formatted.replace(/\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g, (match, label, url) => {
    const item = byUrl.get(normalizeUrl(url));
    if (!item) {
      return `<a href="${escapeAttribute(url)}" target="_blank" rel="noreferrer">${label}</a>`;
    }
    return renderArchiveCitation(item.item_id);
    }).replace(/\[\[ARCHIVE_CITATION\s+item_id=([A-Za-z0-9:-]+)\]\]/g, (match, itemId) => (
      renderArchiveCitation(itemId)
    ));
  };
  return renderMarkdownBlocks(answerText, (value) => renderDocumentCitations(renderInline(value), evidence));
}

function renderMarkdownBlocks(text, renderInline) {
  const lines = String(text || "")
    .replace(/\r\n?/g, "\n")
    .split("\n")
    .map(normalizeMarkdownMarkers);
  const blocks = [];
  let paragraph = [];

  const flushParagraph = () => {
    if (paragraph.length) {
      blocks.push(`<p>${renderInline(paragraph.join("\n")).replace(/\n/g, "<br>")}</p>`);
      paragraph = [];
    }
  };

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    if (!line.trim()) {
      flushParagraph();
      continue;
    }

    const heading = line.match(/^\s*(#{1,6})\s+(.+?)\s*#*\s*$/);
    if (heading) {
      flushParagraph();
      const level = heading[1].length;
      blocks.push(`<h${level}>${renderInline(heading[2])}</h${level}>`);
      continue;
    }

    if (/^\s*>/.test(line)) {
      flushParagraph();
      const quote = [];
      while (index < lines.length && /^\s*>/.test(lines[index])) {
        quote.push(lines[index].replace(/^\s*>\s?/, ""));
        index += 1;
      }
      index -= 1;
      blocks.push(`<blockquote>${renderInline(quote.join("\n")).replace(/\n/g, "<br>")}</blockquote>`);
      continue;
    }

    const unordered = line.match(/^\s*[-+*]\s+(.+)$/);
    const ordered = line.match(/^\s*\d+\.\s+(.+)$/);
    if (unordered || ordered) {
      flushParagraph();
      const orderedList = Boolean(ordered);
      const list = [];
      while (index < lines.length) {
        const match = lines[index].match(
          orderedList ? /^\s*\d+\.\s+(.+)$/ : /^\s*[-+*]\s+(.+)$/,
        );
        if (!match) {
          break;
        }
        list.push(`<li>${renderInline(match[1])}</li>`);
        index += 1;
      }
      index -= 1;
      blocks.push(`<${orderedList ? "ol" : "ul"}>${list.join("")}</${orderedList ? "ol" : "ul"}>`);
      continue;
    }

    paragraph.push(line);
  }
  flushParagraph();
  return blocks.join("");
}

function normalizeMarkdownMarkers(line) {
  return line
    .replace(/^(\s*)\\(#{1,6})(?=\s)/, "$1$2")
    .replace(/^(\s*)\\>(?=\s?)/, "$1>");
}

function renderDocumentCitations(text, evidence = new Map()) {
  const citationPattern = /(\(?\s*Bearing\s+Witness\s*,\s*p{1,2}\.?\s*)(\d+)(?:\s*(?:–|—|-|to)\s*(\d+))?(\s*\)?)/gi;
  return text.replace(citationPattern, (match, prefix, start, end, suffix, offset) => {
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
  const pattern = /\[\[BW\\?_EVIDENCE\s+page=(\d+)\]{1,2}([\s\S]*?)\[\[\/BW\\?_EVIDENCE\]\]/g;
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
    return "";
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
