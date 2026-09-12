"""Compile ArchiveAI article and social-thread exports without fetching URLs."""

import argparse
import json
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from ..catalog import CatalogRecord
from ..models import ArticleContent, Item, Post, TweetThread


def compile_article(folder: Path) -> Item:
    """Read raw_content.json and output.json from an ArchiveAI item folder."""
    raw = json.loads((folder / "raw_content.json").read_text())
    catalog_data = json.loads((folder / "output.json").read_text())
    if isinstance(catalog_data, str):
        catalog_data = json.loads(catalog_data)
    catalog = CatalogRecord.model_validate(catalog_data)
    content = _compile_content(folder, raw, catalog)
    return Item(
        id=uuid5(NAMESPACE_URL, str(catalog.link)),
        catalog_record=catalog, contents=[content],
    )


def _compile_content(folder: Path, raw: dict[str, Any], catalog: CatalogRecord) -> ArticleContent | TweetThread:
    if isinstance(raw.get("text_body"), str) and raw["text_body"].strip():
        article = ArticleContent(
            id=uuid5(NAMESPACE_URL, raw["url"] + "#article"),
            url=raw["url"], title=raw.get("title") or catalog.english_title, text_body=raw["text_body"],
        )
        return article

    posts = raw.get("thread")
    if posts:
        thread = TweetThread(
            id=uuid5(NAMESPACE_URL, raw["url"] + "#social-thread"),
            url=raw["url"], lang=raw.get("lang"),
            thread=[Post.model_validate(post) for post in posts],
        )
        return thread

    raise ValueError(f"{folder}: expected a news article text_body or nonempty social thread")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folders", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    # Validate the complete batch before writing any output.
    items = [compile_article(folder) for folder in args.folders]
    args.output.mkdir(parents=True, exist_ok=True)
    for item in items:
        path = args.output / f"{item.id}.json"
        path.write_text(item.model_dump_json(indent=2) + "\n")
        print(f"{item.catalog_record.id}: {path}")


if __name__ == "__main__":
    main()
