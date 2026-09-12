"""Shared retrieval math; collections own their records and result formats."""

import math
import re
from collections import Counter


def tokens(text: str) -> list[str]:
    return re.findall(r'\w+', text.casefold())


def bm25_score(
    document: Counter[str],
    query_terms: list[str],
    document_frequencies: Counter[str],
    total_documents: int,
    average_document_length: float,
) -> float:
    """Score one tokenized record, preserving query term order and repetition."""
    k1 = 1.5
    b = 0.75
    score = 0.0
    document_length = sum(document.values())
    for term in query_terms:
        term_frequency = document[term]
        if term_frequency == 0:
            continue
        document_frequency = document_frequencies[term]
        inverse_document_frequency = math.log(
            1 + (total_documents - document_frequency + 0.5) / (document_frequency + 0.5)
        )
        denominator = term_frequency + k1 * (1 - b + b * document_length / average_document_length)
        score += inverse_document_frequency * (term_frequency * (k1 + 1) / denominator)
    return score


def cosine_similarity(query_vector: list[float], document_vector: list[float] | None) -> float:
    if not document_vector:
        return 0.0
    numerator = sum(
        query_value * document_value
        for query_value, document_value in zip(query_vector, document_vector, strict=True)
    )
    query_norm = math.sqrt(sum(value * value for value in query_vector))
    document_norm = math.sqrt(sum(value * value for value in document_vector))
    if query_norm == 0 or document_norm == 0:
        return 0.0
    return numerator / (query_norm * document_norm)
