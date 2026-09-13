"""Catalog-only records imported from the Bearing Witness archive CSV."""

from pydantic import BaseModel, ConfigDict


class ShallowCatalogRecord(BaseModel):
    """Searchable archive metadata with no claim of inspectable source text."""

    model_config = ConfigDict(extra='forbid')

    id: str
    english_title: str = ''
    english_description: str = ''
    link: str = ''
    platform: str = ''
    published_date: str = ''
    event_date_from: str = ''
    event_date_to: str = ''
    author: str = ''
    reference: str = ''
    language: list[str] = []
    location: str = ''
    type: str = ''
    media: list[str] = []
    theme_tags: list[str] = []
    countries_and_organizations_tags: list[str] = []
    locations_tags: list[str] = []
    figures_tags: list[str] = []
