"""Derived text used for search and reading."""

from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, StringConstraints


NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class TextRepresentation(BaseModel):
    """Full article text prepared by a named converter/version.

    The containing ArticleContent supplies the source identity. Passage
    locations and indexing are separate, later compilation concerns.
    """

    id: UUID
    kind: Literal["text"] = "text"
    text: NonEmptyText
    produced_by: NonEmptyText
