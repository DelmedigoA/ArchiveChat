# Developer guide

ArchiveChat has two flows: compilation prepares local JSON items; chat loads those
items and exposes search/read tools to a LangGraph agent. The terminal and web
interfaces share the same graph construction. There is no frontend build step.

## Follow a question

1. `python -m archivechat.chat` or `python -m archivechat.web` loads `.env`.
2. `cli_options.parse_chat_options()` parses flags, applies YAML values, resolves
   environment/default values, and performs the existing entry-point validation.
3. `chat.runtime.build_runtime()` creates optional cached embeddings, loads archive,
   FAQ, document, and project metadata collections, configures the model, and
   calls `chat.graph.build_graph()`.
4. `chat.graph` runs the existing `agent → tools → agent → answer` loop. Tool
   definitions in `chat/tools/` delegate to collection methods. Optional public
   web tools live in `chat/web_tools.py`.
5. The terminal's `run_conversation()` invokes the graph and prints answer text.
   The web app invokes it through `/api/chat` or streams it through
   `/api/chat/stream`.
6. `web/streaming.py` maps graph events to `status`, `item`, `delta`, `final`,
   `done`, or `error` events. `chat/results.py` supplies answer text and source
   summaries. The response payloads and event ordering remain unchanged.
7. In the browser, `app.js` connects events to `chat.js`, `item-modal.js`, and
   `document-viewer.js`. `chat.js` handles the request and incremental rendering;
   `formatting.js` produces Markdown/citation HTML and determines text direction.

## State ownership

- The terminal keeps its conversation list in `run_conversation()`.
- Each `create_app()` call owns one in-memory conversation list shared by its
  JSON and streaming routes. Both routes retain that existing history behavior.
- Each collection owns its records, token counts, and optional vectors.
  `chat/search.py` contains only shared tokenization, BM25, and cosine functions;
  collection-specific excerpts, result fields, sorting, and limits stay with the
  corresponding collection.
- `CachedEmbeddings` owns the model/content-hash cache and file writes. Query
  embeddings still go directly to the provider.
- `web/static/state.js` owns browser item lookup, busy state, PDF state, pane
  width, and DOM references. Native ES module imports share this single instance.
  Each request's incremental answer and source list are local to `chat.js`.
- PDF.js and its worker load only when a document citation opens the viewer.
  The configured PDF endpoint, byte ranges, navigation, zoom, and session-storage
  pane width retain their existing behavior.

## Follow a compiled item

`compilation/articles.py` reads saved `raw_content.json` and `output.json` files.
It validates the catalog and converts article or social-thread text into an
`Item` containing content and text representations. Existing stable IDs,
converter names, whitespace rules, and serialized formats are unchanged.

`compilation/workbook.py` handles workbook/file traversal, export discovery,
manifest entries, and output writes. `workbook_rows.py` handles cell normalization,
English/Hebrew pairing, vocabulary labels, and catalog validation. Keeping row
rules separate makes it possible to inspect them without following filesystem
operations. The importer still cleans legacy catalog-only output files, selects
the same article types, and compiles only records with matching exports.

`compilation/fetch_missing.py` turns catalog-only manifest entries into an
acquisition queue. Fetching remains a separate ArchiveAI stage.

## Data boundaries

- `models/` defines `Item`, content, and representation contracts.
- `catalog/` retains the ArchiveAI schema and controlled vocabularies.
- Archive items provide inspectable evidence. Only items with usable content
  enter the archive search collection.
- FAQ and project metadata are separate context stores with dedicated tools.
- The optional Bearing Witness document has page-level search and full-page reads.
- Prompts live in `data/prompts/`; deployment defaults live in
  `config/archive-lens.yaml`.

## Common changes

| Change | Start here |
| --- | --- |
| Add or change a setting | `cli_options.py`, then `chat/runtime.py` |
| Change graph routing or tool-round behavior | `chat/graph.py` |
| Change one result format or excerpt | Its collection in `chat/` |
| Change scoring shared by archive, FAQ, and document search | `chat/search.py` |
| Change a model-facing tool description | `chat/tools/` or `chat/web_tools.py` |
| Change SSE progress or final payloads | `web/streaming.py` |
| Change citations or Markdown rendering | `web/static/formatting.js` |
| Change source details or PDF interactions | `item-modal.js` or `document-viewer.js` |
| Change workbook catalog normalization | `compilation/workbook_rows.py` |

Scalar options generally resolve CLI → YAML → environment → default. Boolean
switches preserve the existing special case: an environment value of `true`
enables the switch even if YAML supplies `false`. Terminal-only model validation
and web-only PDF/host/port defaults remain separate.

## Verification

Run `uv run pytest` for Python behavior, including scripted graph/model tests,
collection retrieval, importers, CLI settings, and HTTP/SSE responses. Run
`node --test tests/web/formatting.test.mjs` with Node.js 22+ for executable browser
formatting checks. Neither suite needs model credentials or external requests.

The refactor also compared the original and revised implementations directly:
search results and scores, embedding-provider calls/cache bytes, CLI defaults and
errors, HTTP/SSE responses and history, and the local ArchiveAI workbook's catalog
records and manifest. Live model output is nondeterministic; verification uses
scripted providers and graph events to check the application behavior reliably.

## Architectural references

The current [Sefaria runtime facade](https://github.com/Sefaria/ai-chatbot/blob/main/server/chat/V2/agent/claude_service.py)
separates dependency setup from execution. ArchiveChat applies that idea through
one shared runtime function and focused HTTP/browser modules, retaining its
existing Starlette/LangGraph stack.

The local `/Users/delmedigo/Dev/ArchiveAI/src/archive_ai/catalog/ground_truth.py`
is the reference for paired workbook-row modeling. Its separation of row
normalization from file processing transfers here; ArchiveChat retains its own
existing normalization rules and catalog contracts.
