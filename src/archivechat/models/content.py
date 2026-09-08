"""Source material attached to an archive item."""

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl

from .representation import TextRepresentation


class ArticleContent(BaseModel):
    """Original supplied article text and its derived representations.

    Text is retained as supplied; this model does not fetch or clean it.
    """

    id: UUID
    kind: Literal["article"] = "article"
    url: HttpUrl
    title: str
    text_body: str
    representations: list[TextRepresentation] = Field(default_factory=list)


class SocialThreadContent(BaseModel):
    """Original supplied social thread text and its derived representations."""

    id: UUID
    kind: Literal["social_thread"] = "social_thread"
    url: HttpUrl
    title: str
    text_body: str
    posts: list[dict[str, Any]] = Field(default_factory=list)
    representations: list[TextRepresentation] = Field(default_factory=list)
