"""Small in-memory BM25 search over compiled items."""

import math
import re
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Protocol

from ..models import Item


class Embeddings(Protocol):
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class CachedEmbeddings:
    """Persistent content-hash cache around an embedding provider."""

    def __init__(self, backend: Embeddings, path: Path, model: str):
        self.backend = backend
        self.path = path
        self.model = model
        self.cache = json.loads(path.read_text()) if path.exists() else {}

    def _key(self, text: str) -> str:
        return f"{self.model}:{hashlib.sha256(text.encode()).hexdigest()}"

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        keys = [self._key(text) for text in texts]
        missing = [text for text, key in zip(texts, keys, strict=True) if key not in self.cache]
        if missing:
            for key, vector in zip((self._key(text) for text in missing), self.backend.embed_documents(missing), strict=True):
                self.cache[key] = vector
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self.cache))
        return [self.cache[key] for key in keys]

    def embed_query(self, text: str) -> list[float]:
        return self.backend.embed_query(text)


def tokens(text: str) -> list[str]:
    return re.findall(r'\w+', text.casefold())


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
            self.content_available[key] = bool(item.contents and any(c.text_body.strip() for c in item.contents))
            document_tokens = tokens(searchable_text)
            self.documents[key] = Counter(document_tokens)
            self.document_frequencies.update(set(document_tokens))
        if not self.items:
            raise ValueError(f'No compiled items in {directory}')
        self.average_document_length = sum(sum(document.values()) for document in self.documents.values()) / len(self.documents)
        self.embeddings = embeddings
        self.embedding_vectors = {}
        if embeddings:
            item_ids = [item_id for item_id in self.items if self.content_available[item_id]]
            vectors = embeddings.embed_documents([self.search_texts[item_id] for item_id in item_ids])
            self.embedding_vectors = dict(zip(item_ids, vectors, strict=True))

    def search(self, query: str, limit: int = 10) -> list[dict]:
        terms = tokens(query)
        if not terms:
            return []
        matches = []
        query_vector = self.embeddings.embed_query(query) if self.embeddings else None
        for key, item in self.items.items():
            bm25_score = self._bm25_score(key, terms)
            semantic_score = self._semantic_score(query_vector, self.embedding_vectors.get(key)) if query_vector else 0.0
            score = bm25_score + semantic_score
            if score <= 0:
                continue
            body = '\n\n'.join(c.text_body for c in item.contents)
            first = next((m.start() for m in re.finditer(r'\w+', body) if m.group().casefold() in set(terms)), 0)
            start = max(0, first - 100)
            catalog = item.catalog_record
            titles = ' '.join(c.title for c in item.contents)
            matches.append({
                'item_id': key,
                'title': catalog.english_title if catalog else titles,
                'description': catalog.english_description if catalog else '',
                'url': str(catalog.link) if catalog else str(item.contents[0].url),
                'excerpt': body[start:start + 500],
                'score': score,
                'bm25_score': bm25_score,
                'semantic_score': semantic_score,
                'content_available': self.content_available[key],
                'content_status': 'content_available' if self.content_available[key] else 'catalog_only',
            })
        return sorted(matches, key=lambda m: (-m['score'], m['item_id']))[:max(0, min(limit, 10))]

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
        k1 = 1.5
        b = 0.75
        score = 0.0
        document = self.documents[item_id]
        document_length = sum(document.values())
        total_documents = len(self.documents)
        for term in query_terms:
            term_frequency = document[term]
            if term_frequency == 0:
                continue
            document_frequency = self.document_frequencies[term]
            inverse_document_frequency = math.log(1 + (total_documents - document_frequency + 0.5) / (document_frequency + 0.5))
            denominator = term_frequency + k1 * (1 - b + b * document_length / self.average_document_length)
            score += inverse_document_frequency * (term_frequency * (k1 + 1) / denominator)
        return score

    def _semantic_score(self, query_vector: list[float], document_vector: list[float] | None) -> float:
        if not document_vector:
            return 0.0
        numerator = sum(query_value * document_value for query_value, document_value in zip(query_vector, document_vector, strict=True))
        query_norm = math.sqrt(sum(value * value for value in query_vector))
        document_norm = math.sqrt(sum(value * value for value in document_vector))
        if query_norm == 0 or document_norm == 0:
            return 0.0
        return numerator / (query_norm * document_norm)
