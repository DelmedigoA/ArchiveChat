from uuid import uuid4

import pytest
from pydantic import ValidationError

from archivechat.models import ArticleContent, Item, SocialThreadContent, TextRepresentation


def test_article_and_representation_round_trip_with_item(item_data):
    representation = TextRepresentation(
        id=uuid4(), text="Cats are beautiful creatures.",
        produced_by="article-text-v1",
    )
    article = ArticleContent(
        id=uuid4(), url="https://example.com/cats", title="Cats",
        text_body="Cats are beautiful creatures.",
        representations=[representation],
    )
    item = Item(**item_data, contents=[article])

    restored = Item.model_validate_json(item.model_dump_json())

    assert restored == item
    assert restored.contents[0].url == article.url
    assert restored.contents[0].representations[0].id == representation.id
    assert restored.contents[0].representations[0].produced_by == "article-text-v1"


def test_social_thread_and_representation_round_trip_with_item(item_data):
    representation = TextRepresentation(
        id=uuid4(), text="Post 1 text.",
        produced_by="social-thread-text-v1",
    )
    thread = SocialThreadContent(
        id=uuid4(), url="https://x.com/example/status/1", title="Thread",
        text_body="Post 1 text.", posts=[{"author": "Example", "content": []}],
        representations=[representation],
    )
    item = Item(**item_data, contents=[thread])

    restored = Item.model_validate_json(item.model_dump_json())

    assert restored == item
    assert restored.contents[0].kind == "social_thread"
    assert restored.contents[0].representations[0].produced_by == "social-thread-text-v1"


def test_article_can_exist_before_conversion():
    article = ArticleContent(
        id=uuid4(), url="https://example.com/cats", title="Cats",
        text_body="Original article text.",
    )

    assert article.representations == []


def test_items_do_not_share_contents():
    first, second = Item(id=uuid4()), Item(id=uuid4())
    first.contents.append(ArticleContent(
        id=uuid4(), url="https://example.com/cats", title="Cats",
        text_body="Original article text.",
    ))

    assert second.contents == []


@pytest.mark.parametrize("field,value", [("text", ""), ("text", "  "), ("produced_by", "")])
def test_representation_requires_text_and_conversion_provenance(field, value):
    data = {"id": uuid4(), "text": "Searchable article text.", "produced_by": "article-text-v1"}
    data[field] = value

    with pytest.raises(ValidationError):
        TextRepresentation(**data)


def test_article_rejects_invalid_source_url():
    with pytest.raises(ValidationError):
        ArticleContent(id=uuid4(), url="not-a-url", title="Cats", text_body="Article.")
