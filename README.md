# ArchiveLens

ArchiveLens will help an agent discover relevant archive items, inspect their
content, and cite evidence. Compilation prepares existing material; chat searches
and reads the resulting collection.

The implemented contracts are `Item`, `ArticleContent`, and `TweetThread`.
An item has a UUID, an optional existing `CatalogRecord`, and zero or more source
contents. Each article preserves its source URL, title, and supplied body text.
Tweet threads preserve ArchiveAI's structured URL/language/posts model, including
typed text, image, and video content blocks. Search derives plain text from the
preserved source content at runtime. Passage locations and indexing are not
implemented yet.

An item does not require a local content file. The catalog schema
and controlled vocabularies come from ArchiveAI and remain in
`src/archivelens/catalog/`.

## Development

```sh
uv sync
uv run pytest
# Browser formatting checks (Node.js 22+; no npm install needed):
node --test tests/web/formatting.test.mjs
```

Use test-driven development: add a failing behavior test, implement the smallest
change that passes, then refactor. Tests use fictional catalog data and require
no network access or model credentials.

Generated embedding caches, compiled items, catalog manifests, and acquisition
queues are local outputs excluded from Git. The compilation commands below
recreate the item collection and manifest; semantic search creates its embedding
cache when needed. The document, FAQ, project metadata, and prompt files remain
versioned runtime inputs.

## Finding your way around

Start with the entry point for the flow you are changing. Both chat interfaces
use the same options and runtime construction:

```text
chat/__main__.py (terminal) ─┐
                           ├─ cli_options.py → chat/runtime.py → chat/graph.py
web/__main__.py (HTTP) ─────┘                                      ↓
                                                           chat/tools/*
                                                                 ↓
                                                        retrieval collections
```

All paths below are relative to `src/archivelens/`.

| Location | Responsibility |
| --- | --- |
| `models/`, `catalog/` | Stored item/content/representation contracts and ArchiveAI catalog schema/vocabularies |
| `compilation/articles.py` | Convert saved ArchiveAI article/thread exports to items |
| `compilation/workbook.py`, `workbook_rows.py` | Import workbook/export files; normalize paired catalog rows |
| `compilation/fetch_missing.py` | Build the acquisition queue from the manifest |
| `config.py`, `cli_options.py` | Read YAML; resolve and validate CLI/environment settings |
| `chat/runtime.py` | Construct providers, collections, tools, and the graph |
| `chat/graph.py`, `chat/prompts.py` | Agent/tool loop and prompt assembly |
| `chat/collection.py`, `documents.py`, `faqs.py`, `project_metadata.py` | Load, search, and read each kind of material |
| `chat/search.py`, `chat/embeddings.py` | Shared retrieval math and embedding cache |
| `chat/tools/`, `chat/web_tools.py` | Model-facing tools and optional public web lookups |
| `chat/results.py` | Extract answer text and inspected item summaries |
| `web/app.py`, `web/streaming.py` | HTTP routes/history; graph events translated to SSE |
| `web/static/app.js` | Browser entry point and event wiring |
| `web/static/chat.js`, `formatting.js` | Streaming messages; Markdown, citations, escaping, and text direction |
| `web/static/document-viewer.js`, `item-modal.js`, `state.js` | PDF controls; source details; shared UI state and DOM references |

See [the developer guide](docs/architecture.md) for execution flow, state ownership,
data boundaries, and where to make common changes.

## Compile saved ArchiveAI exports

Import the article-like catalog from the ArchiveAI ground-truth workbook. This
creates catalog-only items for rows without fetched text and writes a manifest
with content status. Posts are excluded from this first retrieval corpus.

```sh
cd ~/Dev/ArchiveLens
PYTHONPATH=src uv run python -m archivelens.compilation.workbook \
  "/Users/delmedigo/Dev/ArchiveAI/resources/workbooks/ground truth hebrew 800.xlsx" \
  --export-dir /Users/delmedigo/Dev/ArchiveAI/data/HF_text_only \
  --output data/archiveai/compiled/items \
  --manifest data/archiveai/catalog-manifest.json
```

The manifest distinguishes `content_available`, `catalog_only`, and `invalid`
records. Only `content_available` records are written to the RAG collection;
catalog-only records remain in the manifest for acquisition but are not
searchable or readable evidence.

Create a controlled queue for ArchiveAI acquisition:

```sh
PYTHONPATH=src uv run python -m archivelens.compilation.fetch_missing \
  --manifest data/archiveai/catalog-manifest.json \
  --output data/archiveai/acquisition-queue.jsonl \
  --limit 25
```

Import the queued URLs into ArchiveAI's item store and run its normal
`scripts/acquire.py` stage. Copy the resulting `raw_content.json`/`output.json`
export folders into the ArchiveAI export directory, then rerun the workbook
import command. Existing content is skipped and only newly fetched records are
compiled.

The importer reads ArchiveAI export folders containing `raw_content.json` and
`output.json` catalog records. It uses saved article or social-thread text
without fetching URLs or generating new catalog metadata.

```sh
cd ~/Dev/ArchiveLens
PYTHONPATH=src uv run python -m archivelens.compilation.articles \
  /Users/delmedigo/Dev/ArchiveAI/data/HF_text_only/* \
  --output data/archiveai/compiled/items
```

Each output JSON contains a complete `Item`, one content object, and a text
representation. The current local collection compiles 14 ArchiveAI records: five
saved news articles and nine saved social threads. Generated item JSON files are
local data excluded from Git. The importer rejects folders with no usable saved
text and validates catalog records. Unchanged inputs have stable IDs; changed
prepared text gets a new representation ID. Original exports remain in ArchiveAI.

## Chat with the collection

The standard web configuration is in `config/archive-lens.yaml`. Run the web
UI with all model, collection, document, search, embedding, and web-tool
settings from that file:

```sh
cd ~/Dev/ArchiveLens
PYTHONPATH=src uv run python -m archivelens.web --config config/archive-lens.yaml
```

Command-line flags override values from the YAML file. The terminal chat entry
point accepts the same `--config` option.

Set `OPENAI_API_KEY` in your local `.env` (or environment). The default model is
`gpt-5` with `low` reasoning effort and `low` verbosity; optionally override
those with `ARCHIVELENS_MODEL`, `ARCHIVELENS_REASONING_EFFORT`,
`ARCHIVELENS_VERBOSITY`, `--model`, `--reasoning-effort`, or `--verbosity`.
Search returns up to ten item candidates by default; override that with
`ARCHIVELENS_SEARCH_LIMIT` or `--search-limit`. FAQ search returns up to five
questions by default; override that with `ARCHIVELENS_FAQ_SEARCH_LIMIT` or
`--faq-search-limit`. The Bearing Witness document is excluded by default because
it changes both the available tools and the system prompt. Enable it with
`--include-document` (or `ARCHIVELENS_INCLUDE_DOCUMENT=true`); document search
then returns up to five page matches by default, configurable with
`ARCHIVELENS_DOCUMENT_SEARCH_LIMIT` or `--document-search-limit`. Project metadata is loaded from
`data/project-metadata/bearing-witness.json` by default; override that with
`ARCHIVELENS_PROJECT_METADATA_FILE` or `--project-metadata-file`. Reasoning runs through OpenAI's
Responses API; pass `--reasoning-effort none` to disable reasoning. Run:

```sh
cd ~/Dev/ArchiveLens
PYTHONPATH=src uv run python -m archivelens.chat
```

Fully explicit live command:

```sh
cd ~/Dev/ArchiveLens
PYTHONPATH=src uv run python -m archivelens.chat \
  --collection data/archiveai/compiled/items \
  --model gpt-5.6-luna \
  --reasoning-effort low \
  --verbosity low \
  --search-limit 10 \
  --faq-file data/faqs/bearing-witness/faq.json \
  --faq-search-limit 5 \
  --document-text data/documents/bearing-witness/gaza-english-v6.7.0.txt \
  --include-document \
  --document-search-limit 5 \
  --project-metadata-file data/project-metadata/bearing-witness.json \
  --semantic-search \
  --embedding-model text-embedding-3-small \
  --web-tools
```

The web UI streams assistant responses from `/api/chat/stream`. While the graph
is working, status messages such as searching the archive, reading archive
records, checking project context, checking FAQ metadata, searching the Bearing
Witness document, reading document pages, checking public web context, and
writing the answer appear inside the assistant message. As text arrives, the UI
re-renders the accumulated answer so Markdown formatting appears live. Completed
`read_item` tool calls emit item events, allowing source links to become
clickable citation markers such as `[1]` before the final message when the item
is already known; clicking a marker opens the item/catalog record modal with
summary, URL, and tags.

Bearing Witness document citations use `(Bearing Witness, p. 125)` or
`(Bearing Witness, pp. 125–128)`. In the web UI, these open a resizable PDF.js
reader beside the conversation at the citation's first page. The default local
asset is `data/documents/bearing-witness/bearing-witness-gaza-english-v6.7.0.pdf`; configure a versioned CDN/static
asset with `document_pdf_url`, `--document-pdf-url`, or
`ARCHIVELENS_DOCUMENT_PDF_URL` for deployment. The serving host must support
HTTP byte-range requests for progressive loading. Override the local fallback
file with `--document-pdf-path` or `ARCHIVELENS_DOCUMENT_PDF_PATH`.

Fully explicit local web UI command:

```sh
cd ~/Dev/ArchiveLens
PYTHONPATH=src uv run python -m archivelens.web \
  --collection data/archiveai/compiled/items \
  --model gpt-5.6-luna \
  --reasoning-effort low \
  --verbosity low \
  --search-limit 10 \
  --faq-file data/faqs/bearing-witness/faq.json \
  --faq-search-limit 5 \
  --document-text data/documents/bearing-witness/gaza-english-v6.7.0.txt \
  --include-document \
  --document-search-limit 5 \
  --project-metadata-file data/project-metadata/bearing-witness.json \
  --semantic-search \
  --embedding-model text-embedding-3-small \
  --web-tools \
  --port 8765
```

To add semantic search with OpenAI embeddings for archive items and document pages:

```sh
cd ~/Dev/ArchiveLens
PYTHONPATH=src uv run python -m archivelens.chat --semantic-search
```

The default embedding model is `text-embedding-3-small`; override it with
`ARCHIVELENS_EMBEDDING_MODEL` or `--embedding-model`.

To allow simple public web lookups:

```sh
cd ~/Dev/ArchiveLens
PYTHONPATH=src uv run python -m archivelens.chat --web-tools
```

This adds `search_wikipedia`, `read_wikipedia_summary`, and
`fetch_web_page_text`. Web results are for background context; archive items
remain the evidence base for answers about the compiled collection.

For one question:

```sh
cd ~/Dev/ArchiveLens
PYTHONPATH=src uv run python -m archivelens.chat \
  --question "What does the archive report about UNRWA funding?"
```

You can omit `--model` to use the value loaded from `.env`. Use `--collection`
with a directory of compiled item JSON files to select another collection.
Type `quit` to exit interactive chat. Conversation history is kept in memory
for the current terminal session only.

The LangGraph loop is `agent → tools → agent → answer`. `search_items` returns
up to ten candidates using BM25 across catalog metadata and article and social-thread text. With
`--semantic-search`, it also embeds each item and each Bearing Witness document
page at collection load time, then adds cosine similarity to the BM25 score. `read_item` returns the entire stored item
without truncating its articles. Project metadata is separate: `list_project_metadata_records` returns available
metadata records without their full content, and `read_project_metadata_record`
returns the selected project/document/about/website-navigation/sitemap-crawl
record. The prompt labels project metadata and FAQ metadata as context about
ArchiveLens and Bearing Witness, not evidence for claims about events in Gaza.
When a question maps to a public Bearing Witness website section, the prompt asks
the model to use metadata to recommend that section at the end of the answer, using a Markdown link when metadata provides a URL.
FAQ metadata is separate: `search_faqs` searches only FAQ questions as level-1
metadata records, and
`read_faq` returns the level-2 metadata answer for a selected FAQ. The Bearing
Witness document is also separate:
`search_bearing_witness_document` searches page-level records, and
`read_bearing_witness_pages` returns the level-2 full text for selected pages.
The prompt asks the model to read evidence before answering and cite original
URLs or document page numbers; citation correctness is not yet enforced by a
separate validator. Tool rounds are bounded. Live use sends questions, retrieved
item material, FAQ answers, project metadata records, document pages, and embedded
item text to the selected OpenAI APIs. With
`--web-tools`, live use can also contact Wikipedia and user-provided HTTP or
HTTPS URLs. Automated graph tests use scripted models, fake embeddings, and fake
HTTP clients, so they need no API calls.
