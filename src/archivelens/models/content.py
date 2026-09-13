"""Source material attached to an archive item."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


class ArticleContent(BaseModel):
    """Original supplied article text.

    Text is retained as supplied; this model does not fetch or clean it.
    """

    id: UUID
    kind: Literal["article"] = "article"
    url: HttpUrl
    title: str
    text_body: str


class Image(BaseModel):
    url: HttpUrl


class Video(BaseModel):
    url: HttpUrl


class TweetTextContent(BaseModel):
    kind: Literal["text"]
    content: str


class TweetImageContent(BaseModel):
    kind: Literal["image"]
    content: Image


class TweetVideoContent(BaseModel):
    kind: Literal["video"]
    content: Video


TweetContent = TweetTextContent | TweetImageContent | TweetVideoContent


class Post(BaseModel):
    author: str
    published_at: datetime
    content: list[TweetContent]


class TweetThread(BaseModel):
    """Structured X/Twitter thread, based on ArchiveAI's Tweet model."""

    id: UUID
    kind: Literal["tweet_thread"] = "tweet_thread"
    url: HttpUrl
    lang: Literal["en", "he", "ar"] | None = None
    thread: list[Post]


class SocialThreadContent(BaseModel):
    """Legacy compiled social-thread content from the ArchiveAI corpus.

    ArchiveLens now models newly compiled threads as ``TweetThread``, but the
    checked-in compiled corpus still uses ArchiveAI's flattened representation.
    Keep this shape readable so existing corpora remain usable.
    """

    id: UUID
    kind: Literal["social_thread"] = "social_thread"
    url: HttpUrl
    title: str
    text_body: str
    posts: list[dict[str, Any]] = Field(default_factory=list)
    representations: list[dict[str, Any]] = Field(default_factory=list)
