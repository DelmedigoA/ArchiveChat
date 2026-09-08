"""Page-level retrieval for the Bearing Witness document."""

import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

DOCUMENT_TEXT_PATH = Path(__file__).resolve().parents[3] / 'data' / 'documents' / 'bearing-witness' / 'gaza-english-v6.7.0.txt'
DOCUMENT_TITLE = 'Bearing Witness - Gaza, English v6.7.0, July 5 2025'


class Embeddings(Protocol):
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


def tokens(text: str) -> list[str]:
    return re.findall(r'\w+', text.casefold())


@dataclass(frozen=True)
class DocumentPage:
    page: int
    text: str


class DocumentCollection:
    """Search page-level document records, then read full page windows."""

    def __init__(
        self,
        text_path: Path = DOCUMENT_TEXT_PATH,
        title: str = DOCUMENT_TITLE,
        read_radius: int = 1,
        embeddings: Embeddings | None = None,
    ):
        self.text_path = text_path
        self.title = title
        self.read_radius = read_radius
        self.embeddings = embeddings
        raw_pages = text_path.read_text(errors='replace').split('\f')
        self.pages = [
            DocumentPage(page=index, text=text.strip())
            for index, text in enumerate(raw_pages, 1)
            if text.strip()
        ]
        if not self.pages:
            raise ValueError(f'No document text in {text_path}')
        self.documents: dict[int, Counter[str]] = {}
        self.document_frequencies: Counter[str] = Counter()
        for page in self.pages:
            document_tokens = tokens(page.text)
            self.documents[page.page] = Counter(document_tokens)
            self.document_frequencies.update(set(document_tokens))
        self.average_document_length = sum(sum(document.values()) for document in self.documents.values()) / len(self.documents)
        self.page_by_number = {page.page: page for page in self.pages}
        self.embedding_vectors: dict[int, list[float]] = {}
        if embeddings:
            page_numbers = [page.page for page in self.pages]
            vectors = embeddings.embed_documents([self._embedding_text(page) for page in self.pages])
            self.embedding_vectors = dict(zip(page_numbers, vectors, strict=True))

    def search(self, query: str, limit: int = 5) -> list[dict]:
        """Search document pages and return level-1 page matches without full text."""
        query_terms = tokens(query)
        if not query_terms:
            return []
        matches = []
        terms = set(query_terms)
        query_vector = self.embeddings.embed_query(query) if self.embeddings else None
        for page in self.pages:
            bm25_score = self._bm25_score(page.page, query_terms)
            semantic_score = self._semantic_score(query_vector, self.embedding_vectors.get(page.page)) if query_vector else 0.0
            score = bm25_score + semantic_score
            if score <= 0:
                continue
            words = list(re.finditer(r'\w+', page.text))
            first = next((m.start() for m in words if m.group().casefold() in terms), 0)
            start = max(0, first - 180)
            matches.append({
                'document_id': 'bearing-witness-gaza-english-v6.7.0',
                'title': self.title,
                'page': page.page,
                'read_start_page': max(1, page.page - self.read_radius),
                'read_end_page': min(self.pages[-1].page, page.page + self.read_radius),
                'excerpt': page.text[start:start + 700],
                'score': score,
                'bm25_score': bm25_score,
                'semantic_score': semantic_score,
            })
        return sorted(matches, key=lambda match: (-match['score'], match['page']))[:max(0, min(limit, 10))]

    def read_pages(self, start_page: int, end_page: int | None = None) -> dict:
        """Read full level-2 document text for a page range."""
        end_page = start_page if end_page is None else end_page
        if start_page < 1 or end_page < start_page:
            return {'error': 'Invalid page range'}
        selected = [page for page in self.pages if start_page <= page.page <= end_page]
        if not selected:
            return {'error': 'Unknown page range'}
        return {
            'document_id': 'bearing-witness-gaza-english-v6.7.0',
            'title': self.title,
            'start_page': selected[0].page,
            'end_page': selected[-1].page,
            'text': '\n\n'.join(f'[Page {page.page}]\n{page.text}' for page in selected),
        }

    def _bm25_score(self, page_number: int, query_terms: list[str]) -> float:
        k1 = 1.5
        b = 0.75
        score = 0.0
        document = self.documents[page_number]
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

    def _embedding_text(self, page: DocumentPage) -> str:
        return f'{self.title} page {page.page}\n{page.text}'

    def _semantic_score(self, query_vector: list[float], document_vector: list[float] | None) -> float:
        if not document_vector:
            return 0.0
        numerator = sum(query_value * document_value for query_value, document_value in zip(query_vector, document_vector, strict=True))
        query_norm = math.sqrt(sum(value * value for value in query_vector))
        document_norm = math.sqrt(sum(value * value for value in document_vector))
        if query_norm == 0 or document_norm == 0:
            return 0.0
        return numerator / (query_norm * document_norm)
