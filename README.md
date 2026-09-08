# ArchiveChat

ArchiveChat will help an agent discover relevant archive items, inspect their
content, and cite evidence. Compilation prepares existing material; chat searches
and reads the resulting collection.

The first implemented contract is `Item`: a UUID and an optional existing
`CatalogRecord`. An item does not require a local content file. The catalog schema
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
