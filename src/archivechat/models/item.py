"""The archival unit returned by item discovery."""

from uuid import UUID

from pydantic import BaseModel

from ..catalog import CatalogRecord


class Item(BaseModel):
    """An item has its own identity, separate from an imported catalog row ID.

    Catalog metadata may be attached before any content has been compiled.
    """

    id: UUID
    catalog_record: CatalogRecord | None = None
