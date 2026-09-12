"""Embedding provider contract and persistent content-hash cache."""

import hashlib
import json
from pathlib import Path
from typing import Protocol


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
            for key, vector in zip(
                (self._key(text) for text in missing),
                self.backend.embed_documents(missing),
                strict=True,
            ):
                self.cache[key] = vector
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self.cache))
        return [self.cache[key] for key in keys]

    def embed_query(self, text: str) -> list[float]:
        return self.backend.embed_query(text)
