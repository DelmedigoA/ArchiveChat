from uuid import uuid4

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from archivelens.models import ArticleContent, Item, TweetTextContent, TweetThread, Post


def test_article_round_trip_with_item(item_data):
    article = ArticleContent(
        id=uuid4(), url="https://example.com/cats", title="Cats",
        text_body="Cats are beautiful creatures.",
    )
    item = Item(**item_data, contents=[article])

    restored = Item.model_validate_json(item.model_dump_json())

    assert restored == item
    assert restored.contents[0].url == article.url


def test_tweet_thread_round_trip_with_item(item_data):
    thread = TweetThread(
        id=uuid4(), url="https://x.com/example/status/1", lang="en",
        thread=[Post(
            author="Example", published_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            content=[TweetTextContent(kind="text", content="Post 1 text.")],
        )],
    )
    item = Item(**item_data, contents=[thread])

    restored = Item.model_validate_json(item.model_dump_json())

    assert restored == item
    assert restored.contents[0].kind == "tweet_thread"
    assert restored.contents[0].thread[0].content[0].content == "Post 1 text."


def test_article_can_exist_before_conversion():
    article = ArticleContent(
        id=uuid4(), url="https://example.com/cats", title="Cats",
        text_body="Original article text.",
    )

def test_items_do_not_share_contents():
    first, second = Item(id=uuid4()), Item(id=uuid4())
    first.contents.append(ArticleContent(
        id=uuid4(), url="https://example.com/cats", title="Cats",
        text_body="Original article text.",
    ))

    assert second.contents == []


def test_article_rejects_invalid_source_url():
    with pytest.raises(ValidationError):
        ArticleContent(id=uuid4(), url="not-a-url", title="Cats", text_body="Article.")
