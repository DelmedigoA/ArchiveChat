import json

import pytest

from archivechat.compilation.articles import compile_article
from archivechat.models import Item


@pytest.fixture
def article_folder(tmp_path, item_data):
    (tmp_path / "raw_content.json").write_text(json.dumps({
        "url": "https://example.com/cats", "title": "Cats",
        "text_body": "  First paragraph.\n\nSecond paragraph.  ",
    }))
    (tmp_path / "output.json").write_text(json.dumps(item_data["catalog_record"]))
    return tmp_path


def test_compile_preserves_source_catalog_and_paragraphs(article_folder):
    item = compile_article(article_folder)
    article = item.contents[0]
    assert item.catalog_record.english_title == "Cats"
    assert str(article.url) == "https://example.com/cats"
    assert article.text_body == "  First paragraph.\n\nSecond paragraph.  "
    assert article.representations[0].text == "First paragraph.\n\nSecond paragraph."
    assert article.representations[0].produced_by == "article-text-v1"
    assert Item.model_validate_json(item.model_dump_json()) == item
    assert compile_article(article_folder) == item


def test_compile_accepts_archive_ai_double_encoded_catalog(article_folder):
    path = article_folder / "output.json"
    path.write_text(json.dumps(path.read_text()))
    assert compile_article(article_folder).catalog_record.id == 1


def test_compile_accepts_social_thread_content(article_folder):
    (article_folder / "raw_content.json").write_text(json.dumps({
        "url": "https://x.com/example/status/1",
        "thread": [{
            "author": "Example (@example)",
            "published_at": "2024-01-01T00:00:00Z",
            "content": [{"kind": "text", "content": "First post text."}],
        }],
    }))

    item = compile_article(article_folder)
    thread = item.contents[0]

    assert thread.kind == "social_thread"
    assert "First post text." in thread.text_body
    assert thread.representations[0].produced_by == "social-thread-text-v1"
    assert Item.model_validate_json(item.model_dump_json()) == item


@pytest.mark.parametrize("raw", [
    {"url": "https://x.com/example/status/1", "thread": []},
    {"url": "https://example.com/cats", "title": "Cats", "text_body": "  "},
])
def test_compile_rejects_empty_content(article_folder, raw):
    (article_folder / "raw_content.json").write_text(json.dumps(raw))
    with pytest.raises(ValueError):
        compile_article(article_folder)


def test_changed_text_gets_new_representation_identity(article_folder):
    before = compile_article(article_folder)
    path = article_folder / "raw_content.json"
    raw = json.loads(path.read_text())
    raw["text_body"] = "Updated article."
    path.write_text(json.dumps(raw))
    after = compile_article(article_folder)
    assert before.id == after.id
    assert before.contents[0].id == after.contents[0].id
    assert before.contents[0].representations[0].id != after.contents[0].representations[0].id
