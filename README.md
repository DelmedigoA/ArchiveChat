# ArchiveLens

ArchiveLens will help an agent discover relevant archive items, inspect their
content, and cite evidence. Compilation prepares existing material; chat searches
and reads the resulting collection.

The implemented contracts are `Item`, `ArticleContent`, and `TextRepresentation`.
An item has a UUID, an optional existing `CatalogRecord`, and zero or more articles.
Each article preserves its source URL, title, and supplied body text. Its optional
text representations contain prepared text and the converter/version that produced
it (`produced_by`). Their nesting preserves item → article → representation links.
Representations currently cover whole articles. The first converter preserves
paragraphs and trims surrounding whitespace; passage locations and indexing
are not implemented yet.

An item does not require a local content file. The catalog schema
and controlled vocabularies come from ArchiveAI and remain in
`src/archivechat/catalog/`.

## Development

```sh
uv sync
uv run pytest
```

Use test-driven development: add a failing behavior test, implement the smallest
change that passes, then refactor. Tests use fictional catalog data and require
no network access or model credentials.

Next milestone: search a small catalog collection and return candidate item IDs
with metadata-grounded reasons. Content conversion and model-based relevance
evaluations will follow as separate steps.

## Compile saved ArchiveAI exports

The importer reads ArchiveAI export folders containing `raw_content.json` and
`output.json` catalog records. It uses saved article or social-thread text
without fetching URLs or generating new catalog metadata.

```sh
cd ~/Dev/ArchiveChat
PYTHONPATH=src uv run python -m archivechat.compilation.articles \
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

Set `OPENAI_API_KEY` in your local `.env` (or environment). The default model is
`gpt-5` with `low` reasoning effort and `low` verbosity; optionally override
those with `ARCHIVECHAT_MODEL`, `ARCHIVECHAT_REASONING_EFFORT`,
`ARCHIVECHAT_VERBOSITY`, `--model`, `--reasoning-effort`, or `--verbosity`.
Search returns up to ten item candidates by default; override that with
`ARCHIVECHAT_SEARCH_LIMIT` or `--search-limit`. FAQ search returns up to five
questions by default; override that with `ARCHIVECHAT_FAQ_SEARCH_LIMIT` or
`--faq-search-limit`. Bearing Witness document search returns up to five page
matches by default; override that with `ARCHIVECHAT_DOCUMENT_SEARCH_LIMIT` or
`--document-search-limit`. Project metadata is loaded from
`data/project-metadata/bearing-witness.json` by default; override that with
`ARCHIVECHAT_PROJECT_METADATA_FILE` or `--project-metadata-file`. Reasoning runs through OpenAI's
Responses API; pass `--reasoning-effort none` to disable reasoning. Run:

```sh
cd ~/Dev/ArchiveChat
PYTHONPATH=src uv run python -m archivechat.chat
```

Fully explicit live command:

```sh
cd ~/Dev/ArchiveChat
PYTHONPATH=src uv run python -m archivechat.chat \
  --collection data/archiveai/compiled/items \
  --model gpt-5.6-luna \
  --reasoning-effort low \
  --verbosity low \
  --search-limit 10 \
  --faq-file data/faqs/bearing-witness/faq.json \
  --faq-search-limit 5 \
  --document-text data/documents/bearing-witness/gaza-english-v6.7.0.txt \
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

Fully explicit local web UI command:

```sh
cd ~/Dev/ArchiveChat
PYTHONPATH=src uv run python -m archivechat.web \
  --collection data/archiveai/compiled/items \
  --model gpt-5.6-luna \
  --reasoning-effort low \
  --verbosity low \
  --search-limit 10 \
  --faq-file data/faqs/bearing-witness/faq.json \
  --faq-search-limit 5 \
  --document-text data/documents/bearing-witness/gaza-english-v6.7.0.txt \
  --document-search-limit 5 \
  --project-metadata-file data/project-metadata/bearing-witness.json \
  --semantic-search \
  --embedding-model text-embedding-3-small \
  --web-tools \
  --port 8765
```

To add semantic search with OpenAI embeddings for archive items and document pages:

```sh
cd ~/Dev/ArchiveChat
PYTHONPATH=src uv run python -m archivechat.chat --semantic-search
```

The default embedding model is `text-embedding-3-small`; override it with
`ARCHIVECHAT_EMBEDDING_MODEL` or `--embedding-model`.

To allow simple public web lookups:

```sh
cd ~/Dev/ArchiveChat
PYTHONPATH=src uv run python -m archivechat.chat --web-tools
```

This adds `search_wikipedia`, `read_wikipedia_summary`, and
`fetch_web_page_text`. Web results are for background context; archive items
remain the evidence base for answers about the compiled collection.

For one question:

```sh
cd ~/Dev/ArchiveChat
PYTHONPATH=src uv run python -m archivechat.chat \
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
