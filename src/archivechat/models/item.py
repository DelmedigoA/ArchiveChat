"""The archival unit returned by item discovery."""

from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field

from ..catalog import CatalogRecord
from .content import ArticleContent, SocialThreadContent

Content = Annotated[ArticleContent | SocialThreadContent, Field(discriminator='kind')]


class Item(BaseModel):
    """An item has its own identity, separate from an imported catalog row ID.

    Catalog metadata may be attached before any content has been compiled.
    """

    id: UUID
    catalog_record: CatalogRecord | None = None
    contents: list[Content] = Field(default_factory=list)
