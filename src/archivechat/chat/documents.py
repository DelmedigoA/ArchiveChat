"""Page-level retrieval for the Bearing Witness document."""

import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

DOCUMENT_TEXT_PATH = Path(__file__).resolve().parents[3] / 'data' / 'documents' / 'bearing-witness' / 'gaza-english-v6.7.0.txt'
DOCUMENT_TITLE = 'Bearing Witness - Gaza, English v6.7.0, July 5 2025'


def tokens(text: str) -> list[str]:
    return re.findall(r'\w+', text.casefold())


@dataclass(frozen=True)
class DocumentPage:
    page: int
    text: str


class DocumentCollection:
    """Search page-level document records, then read full page windows."""

    def __init__(self, text_path: Path = DOCUMENT_TEXT_PATH, title: str = DOCUMENT_TITLE, read_radius: int = 1):
        self.text_path = text_path
        self.title = title
        self.read_radius = read_radius
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

    def search(self, query: str, limit: int = 5) -> list[dict]:
        """Search document pages and return level-1 page matches without full text."""
        query_terms = tokens(query)
        if not query_terms:
            return []
        matches = []
        terms = set(query_terms)
        for page in self.pages:
            score = self._bm25_score(page.page, query_terms)
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
