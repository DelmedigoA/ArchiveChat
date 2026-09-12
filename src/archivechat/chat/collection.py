"""Small in-memory BM25 search over compiled items."""

import re
from collections import Counter
from pathlib import Path

from ..models import Item
from .embeddings import CachedEmbeddings as CachedEmbeddings  # Original import path remains valid.
from .embeddings import Embeddings
from .search import bm25_score, cosine_similarity, tokens


class Collection:
    def __init__(self, directory: Path, embeddings: Embeddings | None = None):
        self.items = {}
        self.documents = {}
        self.document_frequencies = Counter()
        self.search_texts = {}
        self.content_available = {}
        for path in sorted(directory.glob('*.json')):
            item = Item.model_validate_json(path.read_text())
            if not item.contents or not any(c.text_body.strip() for c in item.contents):
                continue
            key = str(item.id)
            if key in self.items:
                raise ValueError(f'Duplicate item ID: {key}')
            self.items[key] = item
            searchable_text = self._searchable_text(item)
            self.search_texts[key] = searchable_text
            self.content_available[key] = bool(
                item.contents and any(c.text_body.strip() for c in item.contents)
            )
            document_tokens = tokens(searchable_text)
            self.documents[key] = Counter(document_tokens)
            self.document_frequencies.update(set(document_tokens))
        if not self.items:
            raise ValueError(f'No compiled items in {directory}')
        self.average_document_length = sum(
            sum(document.values()) for document in self.documents.values()
        ) / len(self.documents)
        self.embeddings = embeddings
        self.embedding_vectors = {}
        if embeddings:
            item_ids = [item_id for item_id in self.items if self.content_available[item_id]]
            vectors = embeddings.embed_documents(
                [self.search_texts[item_id] for item_id in item_ids]
            )
            self.embedding_vectors = dict(zip(item_ids, vectors, strict=True))

    def search(self, query: str, limit: int = 10) -> list[dict]:
        terms = tokens(query)
        if not terms:
            return []
        matches = []
        query_vector = self.embeddings.embed_query(query) if self.embeddings else None
        for key, item in self.items.items():
            bm25_score = self._bm25_score(key, terms)
            semantic_score = (
                self._semantic_score(query_vector, self.embedding_vectors.get(key))
                if query_vector
                else 0.0
            )
            score = bm25_score + semantic_score
            if score <= 0:
                continue
            body = '\n\n'.join(c.text_body for c in item.contents)
            first = next(
                (
                    m.start()
                    for m in re.finditer(r'\w+', body)
                    if m.group().casefold() in set(terms)
                ),
                0,
            )
            start = max(0, first - 100)
            catalog = item.catalog_record
            titles = ' '.join(c.title for c in item.contents)
            matches.append(
                {
                    'item_id': key,
                    'title': catalog.english_title if catalog else titles,
                    'description': catalog.english_description if catalog else '',
                    'url': str(catalog.link) if catalog else str(item.contents[0].url),
                    'excerpt': body[start : start + 500],
                    'score': score,
                    'bm25_score': bm25_score,
                    'semantic_score': semantic_score,
                    'content_available': self.content_available[key],
                    'content_status': 'content_available'
                    if self.content_available[key]
                    else 'catalog_only',
                }
            )
        return sorted(matches, key=lambda m: (-m['score'], m['item_id']))[: max(0, min(limit, 10))]

    def read(self, item_id: str) -> dict:
        item = self.items.get(item_id)
        return item.model_dump(mode='json') if item else {'error': 'Unknown item ID'}

    def _searchable_text(self, item: Item) -> str:
        catalog = item.catalog_record
        metadata = catalog.model_dump_json() if catalog else ''
        body = '\n\n'.join(c.text_body for c in item.contents)
        titles = ' '.join(c.title for c in item.contents)
        return f'{metadata} {titles} {body}'

    def _bm25_score(self, item_id: str, query_terms: list[str]) -> float:
        return bm25_score(
            self.documents[item_id],
            query_terms,
            self.document_frequencies,
            len(self.documents),
            self.average_document_length,
        )

    def _semantic_score(
        self, query_vector: list[float], document_vector: list[float] | None
    ) -> float:
        return cosine_similarity(query_vector, document_vector)
