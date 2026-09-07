from uuid import UUID

from pydantic import BaseModel

from .catalog import CatalogRecord

from pathlib import Path

class Source(BaseModel):
    id: UUID
    path: Path
    archive_record: CatalogRecord
