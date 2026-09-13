import assert from "node:assert/strict";
import test from "node:test";
import {
  renderAnswer, renderDocumentCitations, isHebrewDominant, escapeAttribute,
} from "../../src/archivelens/web/static/formatting.js";

test("answer formatting escapes HTML and retains inline Markdown and paragraphs", () => {
  assert.equal(
    renderAnswer('<script> **Bold** and *emphasis*\nline\n\nNext', []),
    '<p>&lt;script&gt; <strong>Bold</strong> and <em>emphasis</em><br>line</p><p>Next</p>',
  );
  assert.equal(escapeAttribute('"`<&'), '&quot;&#096;&lt;&amp;');
});

test("answer formatting renders block Markdown and escaped heading markers", () => {
  assert.equal(
    renderAnswer('### 1. Bibas\n\n\\> A quoted statement', []),
    '<h3>1. Bibas</h3><blockquote>A quoted statement</blockquote>',
  );
});

test("repeated source URLs share a citation number and unknown URLs remain links", () => {
  const html = renderAnswer(
    '[One](https://example.org/source/) [Again](https://example.org/source) [Other](https://example.org/other)',
    [{ item_id: 'item-1', title: 'Source', url: 'https://example.org/source' }],
  );
  const citation = '<button class="citation-link" type="button" data-item-id="item-1" title="Source" aria-label="Open source 1: Source">[1]</button>';
  assert.equal(html, `<p>${citation} ${citation} <a href="https://example.org/other" target="_blank" rel="noreferrer">Other</a></p>`);
});

test("stable archive citation IDs render numbered source buttons without exposing the marker", () => {
  const html = renderAnswer(
    'The reporting supports this claim. [[ARCHIVE_CITATION item_id=item-1]]',
    [{ item_id: 'item-1', title: 'Source', url: 'https://example.org/source' }],
  );
  assert.match(html, /data-item-id="item-1"/);
  assert.match(html, />\[1\]<\/button>/);
  assert.doesNotMatch(html, /ARCHIVE_CITATION/);
});

test("unknown archive citation IDs remain hidden", () => {
  const html = renderAnswer('Claim. [[ARCHIVE_CITATION item_id=unknown]]', []);
  assert.doesNotMatch(html, /ARCHIVE_CITATION|unknown/);
});

test("document citations open at the first page and invalid ranges remain text", () => {
  assert.equal(renderDocumentCitations('(Bearing Witness, pp. 0–3)'), '(Bearing Witness, pp. 0–3)');
  assert.equal(renderDocumentCitations('(Bearing Witness, pp. 5–2)'), '(Bearing Witness, pp. 5–2)');
  assert.equal(
    renderDocumentCitations('(Bearing Witness, pp. 2 to 5)'),
    '<button class="document-citation-link" type="button" data-document-page="2" title="Open Bearing Witness PDF at page 2" aria-label="Open Bearing Witness PDF at page 2">(Bearing Witness, pp. 2–5)</button>',
  );
});

test("page citations without an evidence anchor do not guess at a highlight", () => {
  const html = renderAnswer(
    'Neither side offered evidence for their claims. (Bearing Witness, p. 150)',
    [],
  );
  assert.doesNotMatch(html, /data-document-evidence=/);
});

test("AI evidence quotes are hidden and attached to the matching page citation", () => {
  const html = renderAnswer(
    'The report documents the incident. [[BW_EVIDENCE page=66]]Exact supporting sentence.[[/BW_EVIDENCE]] (Bearing Witness, p. 66)',
    [],
  );
  assert.doesNotMatch(html, />Exact supporting sentence\./);
  assert.doesNotMatch(html, /BW_EVIDENCE/);
  assert.match(html, /data-document-evidence="\[&quot;Exact supporting sentence\.&quot;\]"/);
});

test("escaped evidence-marker underscores still attach a PDF highlight", () => {
  const html = renderAnswer(
    'Claim. [[BW\\_EVIDENCE page=195]The ratio increased in May to 39%[[/BW\\_EVIDENCE]] (Bearing Witness, p. 195)',
    [],
  );
  assert.doesNotMatch(html, /BW\\?_EVIDENCE/);
  assert.match(html, /data-document-evidence="\[&quot;The ratio increased in May to 39%&quot;\]"/);
});

test("a document quote keeps its red-rule blockquote treatment and a hidden highlight anchor", () => {
  const html = renderAnswer(
    '> “Anyone crossing the line is a terrorist.” [[BW_EVIDENCE page=62]]crossing the line is a terrorist[[/BW_EVIDENCE]] (Bearing Witness, p. 62)',
    [],
  );
  assert.match(html, /^<blockquote>/);
  assert.match(html, /“Anyone crossing the line is a terrorist\.”/);
  assert.match(html, /data-document-evidence="\[&quot;crossing the line is a terrorist&quot;\]"/);
});

test("direction depends on the majority of letters, including Hebrew marks", () => {
  assert.equal(isHebrewDominant('שלום world'), false);
  assert.equal(isHebrewDominant('שלום עולם! 123'), true);
  assert.equal(isHebrewDominant('שָׁלוֹם'), true);
  assert.equal(isHebrewDominant('123!?'), false);
});
