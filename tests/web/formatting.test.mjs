import assert from "node:assert/strict";
import test from "node:test";
import {
  renderAnswer, renderDocumentCitations, isHebrewDominant, escapeAttribute,
} from "../../src/archivechat/web/static/formatting.js";

test("answer formatting escapes HTML and retains inline Markdown and paragraphs", () => {
  assert.equal(
    renderAnswer('<script> **Bold** and *emphasis*\nline\n\nNext', []),
    '<p>&lt;script&gt; <strong>Bold</strong> and <em>emphasis</em><br>line</p><p>Next</p>',
  );
  assert.equal(escapeAttribute('"`<&'), '&quot;&#096;&lt;&amp;');
});

test("repeated source URLs share a citation number and unknown URLs remain links", () => {
  const html = renderAnswer(
    '[One](https://example.org/source/) [Again](https://example.org/source) [Other](https://example.org/other)',
    [{ item_id: 'item-1', title: 'Source', url: 'https://example.org/source' }],
  );
  const citation = '<button class="citation-link" type="button" data-item-id="item-1" title="Source" aria-label="Open source 1: Source">[1]</button>';
  assert.equal(html, `<p>${citation} ${citation} <a href="https://example.org/other" target="_blank" rel="noreferrer">Other</a></p>`);
});

test("document citations open at the first page and invalid ranges remain text", () => {
  assert.equal(renderDocumentCitations('(Bearing Witness, pp. 0–3)'), '(Bearing Witness, pp. 0–3)');
  assert.equal(renderDocumentCitations('(Bearing Witness, pp. 5–2)'), '(Bearing Witness, pp. 5–2)');
  assert.equal(
    renderDocumentCitations('(Bearing Witness, pp. 2 to 5)'),
    '<button class="document-citation-link" type="button" data-document-page="2" title="Open Bearing Witness PDF at page 2" aria-label="Open Bearing Witness PDF at page 2">(Bearing Witness, pp. 2–5)</button>',
  );
});

test("direction depends on the majority of letters, including Hebrew marks", () => {
  assert.equal(isHebrewDominant('שלום world'), false);
  assert.equal(isHebrewDominant('שלום עולם! 123'), true);
  assert.equal(isHebrewDominant('שָׁלוֹם'), true);
  assert.equal(isHebrewDominant('123!?'), false);
});
