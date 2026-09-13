"""The archival unit returned by item discovery."""

from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from ..catalog import CatalogRecord
from .content import ArticleContent, SocialThreadContent, TweetThread
from .shallow_catalog import ShallowCatalogRecord

Content = Annotated[ArticleContent | TweetThread | SocialThreadContent, Field(discriminator='kind')]


class Item(BaseModel):
    """An item has its own identity, separate from an imported catalog row ID.

    Catalog metadata may be attached before any content has been compiled.
    """

    id: UUID
    catalog_record: CatalogRecord | ShallowCatalogRecord | None = None
    contents: list[Content] = Field(default_factory=list)

    @field_validator('catalog_record', mode='before')
    @classmethod
    def parse_catalog_record(cls, value):
        if isinstance(value, CatalogRecord | ShallowCatalogRecord) or value is None:
            return value
        if isinstance(value, dict):
            # ArchiveAI records have the bilingual fields and numeric source-row ID.
            # Keep their controlled-vocabulary validation strict; the CSV's separate
            # shallow schema intentionally has a string source-row ID.
            if 'hebrew_title' in value or isinstance(value.get('id'), int):
                return CatalogRecord.model_validate(value)
            return ShallowCatalogRecord.model_validate(value)
        return value
