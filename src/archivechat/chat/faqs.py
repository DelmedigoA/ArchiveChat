"""Question-first FAQ retrieval for project context."""

import json
from collections import Counter
from pathlib import Path
from typing import Any

from .search import bm25_score, tokens

FAQ_PATH = Path(__file__).resolve().parents[3] / 'data' / 'faqs' / 'bearing-witness' / 'faq.json'


class FaqCollection:
    """Two-level FAQ store: search questions first, then read answers by ID."""

    def __init__(self, path: Path = FAQ_PATH):
        self.path = path
        raw = json.loads(path.read_text())
        self.faqs: dict[str, dict[str, Any]] = {}
        self.documents: dict[str, Counter[str]] = {}
        self.document_frequencies: Counter[str] = Counter()
        for faq in raw:
            faq_id = str(faq['id'])
            if faq_id in self.faqs:
                raise ValueError(f'Duplicate FAQ ID: {faq_id}')
            normalized = {
                'faq_id': faq_id,
                'question': str(faq['question']),
                'answer': str(faq['answer']),
                'url': str(faq.get('url') or ''),
            }
            self.faqs[faq_id] = normalized
            document_tokens = tokens(normalized['question'])
            self.documents[faq_id] = Counter(document_tokens)
            self.document_frequencies.update(set(document_tokens))
        if not self.faqs:
            raise ValueError(f'No FAQs in {path}')
        self.average_document_length = sum(
            sum(document.values()) for document in self.documents.values()
        ) / len(self.documents)

    def search(self, query: str, limit: int = 5) -> list[dict]:
        """Search only FAQ questions and return matching level-1 FAQ records."""
        query_terms = tokens(query)
        if not query_terms:
            return []
        matches = []
        for faq_id, faq in self.faqs.items():
            score = self._bm25_score(faq_id, query_terms)
            if score <= 0:
                continue
            matches.append(
                {
                    'faq_id': faq_id,
                    'question': faq['question'],
                    'url': faq['url'],
                    'score': score,
                }
            )
        return sorted(matches, key=lambda match: (-match['score'], match['faq_id']))[
            : max(0, min(limit, 10))
        ]

    def read(self, faq_id: str) -> dict:
        """Read a level-2 FAQ answer by ID."""
        return self.faqs.get(faq_id) or {'error': 'Unknown FAQ ID'}

    def _bm25_score(self, faq_id: str, query_terms: list[str]) -> float:
        return bm25_score(
            self.documents[faq_id],
            query_terms,
            self.document_frequencies,
            len(self.documents),
            self.average_document_length,
        )
