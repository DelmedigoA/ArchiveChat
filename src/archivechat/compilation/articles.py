"""Compile ArchiveAI article and social-thread exports without fetching URLs."""

import argparse
import json
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from ..catalog import CatalogRecord
from ..models import ArticleContent, Item, SocialThreadContent, TextRepresentation

ARTICLE_CONVERTER = "article-text-v1"
SOCIAL_THREAD_CONVERTER = "social-thread-text-v1"


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


def _compile_content(folder: Path, raw: dict[str, Any], catalog: CatalogRecord) -> ArticleContent | SocialThreadContent:
    if isinstance(raw.get("text_body"), str) and raw["text_body"].strip():
        article = ArticleContent(
            id=uuid5(NAMESPACE_URL, raw["url"] + "#article"),
            url=raw["url"], title=raw.get("title") or catalog.english_title, text_body=raw["text_body"],
        )
        text = article.text_body.strip()
        article.representations.append(TextRepresentation(
            id=uuid5(article.id, ARTICLE_CONVERTER + "\n" + text),
            text=text, produced_by=ARTICLE_CONVERTER,
        ))
        return article

    thread_text = _thread_text(raw.get("thread"))
    if thread_text:
        thread = SocialThreadContent(
            id=uuid5(NAMESPACE_URL, raw["url"] + "#social-thread"),
            url=raw["url"], title=raw.get("title") or catalog.english_title,
            text_body=thread_text, posts=raw.get("thread") or [],
        )
        thread.representations.append(TextRepresentation(
            id=uuid5(thread.id, SOCIAL_THREAD_CONVERTER + "\n" + thread_text),
            text=thread_text, produced_by=SOCIAL_THREAD_CONVERTER,
        ))
        return thread

    raise ValueError(f"{folder}: expected a news article text_body or nonempty social thread")


def _thread_text(thread: Any) -> str:
    if not isinstance(thread, list):
        return ""
    posts = []
    for index, post in enumerate(thread, 1):
        if not isinstance(post, dict):
            continue
        author = post.get("author") or "Unknown author"
        published = post.get("published_at") or "unknown date"
        parts = []
        for block in post.get("content") or []:
            if isinstance(block, dict) and isinstance(block.get("content"), str) and block["content"].strip():
                parts.append(block["content"].strip())
        body = "\n".join(parts).strip()
        if body:
            posts.append(f"Post {index} — {author} — {published}\n{body}")
    return "\n\n".join(posts).strip()


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
