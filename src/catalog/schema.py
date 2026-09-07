from __future__ import annotations

from datetime import date
from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, BeforeValidator, Field, HttpUrl, field_validator, model_validator

from .vocabularies.countries_organizations import (
    COUNTRIES_ORGANIZATIONS_HEBREW_VALUES,
    COUNTRIES_ORGANIZATIONS_VALUES,
)
from .vocabularies.figures import FIGURE_HEBREW_VALUES, FIGURE_VALUES
from .vocabularies.languages import LANGUAGE_HEBREW_VALUES, LANGUAGE_VALUES
from .vocabularies.locations import LOCATION_HEBREW_VALUES, LOCATION_VALUES
from .vocabularies.media import MEDIA_HEBREW_VALUES, MEDIA_VALUES
from .vocabularies.platforms import PLATFORM_HEBREW_VALUES, PLATFORM_VALUES
from .vocabularies.themes import THEME_HEBREW_VALUES, THEME_VALUES
from .vocabularies.types import TYPE_HEBREW_VALUES, TYPE_VALUES

CatalogPlatform = Literal[*PLATFORM_VALUES]
HebrewCatalogPlatform = Literal[*PLATFORM_HEBREW_VALUES]
CatalogLanguage = Literal[*LANGUAGE_VALUES]
HebrewCatalogLanguage = Literal[*LANGUAGE_HEBREW_VALUES]
CatalogType = Literal[*TYPE_VALUES]
HebrewCatalogType = Literal[*TYPE_HEBREW_VALUES]
CatalogMedia = Literal[*MEDIA_VALUES]
HebrewCatalogMedia = Literal[*MEDIA_HEBREW_VALUES]
ThemeTag = Literal[*THEME_VALUES]
HebrewThemeTag = Literal[*THEME_HEBREW_VALUES]
CountriesOrganizationsTag = Literal[*COUNTRIES_ORGANIZATIONS_VALUES]
HebrewCountriesOrganizationsTag = Literal[*COUNTRIES_ORGANIZATIONS_HEBREW_VALUES]
LocationTag = Literal[*LOCATION_VALUES]
HebrewLocationTag = Literal[*LOCATION_HEBREW_VALUES]
FigureTag = Literal[*FIGURE_VALUES]
HebrewFigureTag = Literal[*FIGURE_HEBREW_VALUES]


def ends_with_dot(sentence: str) -> bool:
    return sentence.endswith(".")

def _normalize_title(sentence: str) -> str:
    sentence = sentence.strip()
    if not ends_with_dot(sentence):
        return sentence
    else:
        return sentence[:-1]

def _normalize_description(sentence: str) -> str:
    if ends_with_dot(sentence):
        return sentence
    else:
        return sentence + "."

class CatalogSeed(BaseModel):
    id: int = Field(
        ...,
        ge=1,
        description="Stable source-spreadsheet row identifier, copied unchanged.",
    )
    link: HttpUrl = Field(
        description="Canonical URL of the cataloged source item.",
    )


class CatalogDraft(BaseModel):
    english_title: str = Field(
        description="Exact English source title when present; otherwise a short neutral content summary.",
    )
    hebrew_title: str = Field(
        description="Exact Hebrew title or accurate translation, short and neutral.",
    )
    english_description: str = Field(
        description="Neutral 2-3 sentence summary of the source content.",
    )
    hebrew_description: str = Field(
        description="Neutral 2-3 sentence summary or translation in Hebrew.",
    )
    published_date: date = Field(
        description="Exact publication date of the article or post.",
    )
    event_date_from: date | None = Field(
        default=None,
        description="Start date of the event period, blank when no specific start date is known.",
    )
    event_date_to: date | None = Field(
        default=None,
        description="End date of the event period. Same as start date for single-day events.",
    )
    platform: CatalogPlatform = Field(
        description="Platform where the material was published.",
    )
    platform_hebrew: HebrewCatalogPlatform = Field(
        description="Hebrew label deterministically mapped from platform.",
    )
    author: str = Field(
        description="Author name for the source item.",
    )
    author_hebrew: str | None = Field(
        default=None,
        description=(
            "Hebrew form of the author name. "
            "For Israeli authors with a known Hebrew name, use the Hebrew rendering. "
            "For all other authors (including Arabic, English, or other non-Hebrew names), "
            "copy the 'author' English value exactly — do not transliterate into Hebrew."
        ),
    )
    source: list[CatalogPlatform] = Field(
        default_factory=list,
        description="Original source platform for quoted, embedded, or reposted material.",
    )
    reference: Annotated[
        list[str],
        BeforeValidator(lambda v: [] if v is None else ([v] if isinstance(v, str) else v)),
    ] = Field(
        default_factory=list,
        description="URLs of external sources cited, quoted, or embedded by this item. Only include actual URLs — no search queries or text descriptions.",
    )
    followup_instructions: list[str] = Field(
        default_factory=list,
        description="Action items for the human reviewer requiring manual lookup, e.g. '[Search: Haaretz \"article title\" June 2025]' when a referenced source has no URL in the content.",
    )
    location: str | None = Field(
        default=None,
        description=(
            "Locations where the events physically took place, in English. "
            "Semicolon-separated location names only — no parenthetical explanations or descriptions. "
            "Do not list both a specific location and its broader parent "
            "(e.g. list 'Jabaliya' but not also 'Gaza Strip'; list 'Kerem Shalom Crossing' but not also 'Gaza Strip')."
        ),
    )
    location_hebrew: str | None = Field(
        default=None,
        description=(
            "Same locations as the 'location' field, written in Hebrew. "
            "Location names only — no parenthetical explanations or descriptions. "
            "Apply the same hierarchy rule: do not list a specific location and its broader parent together."
        ),
    )
    language: list[CatalogLanguage] = Field(
        description="Languages with substantive written or clearly spoken content.",
    )
    language_hebrew: list[HebrewCatalogLanguage] = Field(
        description="Hebrew labels deterministically mapped from language.",
    )
    type: CatalogType = Field(
        description="Best matching content type from the vocabulary.",
    )
    type_hebrew: HebrewCatalogType = Field(
        description="Hebrew label deterministically mapped from type.",
    )
    media: list[CatalogMedia] = Field(
        description="Media categories present in the source.",
    )
    media_hebrew: list[HebrewCatalogMedia] = Field(
        description="Hebrew labels deterministically mapped from media.",
    )
    theme_tags: list[ThemeTag] = Field(
        description="Theme tags that materially support search and retrieval.",
    )
    theme_tags_hebrew: list[HebrewThemeTag] = Field(
        description="Hebrew labels derived from theme tags.",
    )
    countries_and_organizations_tags: list[CountriesOrganizationsTag] = Field(
        default_factory=list,
        description="Countries and organizations mentioned as subjects.",
    )
    countries_and_organizations_tags_hebrew: list[HebrewCountriesOrganizationsTag] = (
        Field(
            default_factory=list,
            description="Hebrew labels derived from countries and organizations tags.",
        )
    )
    locations_tags: list[LocationTag] = Field(
        default_factory=list,
        description="Precise major location tags from the vocabulary.",
    )
    locations_tags_hebrew: list[HebrewLocationTag] = Field(
        default_factory=list,
        description="Hebrew labels derived from location tags.",
    )
    figures_tags: list[FigureTag] = Field(
        default_factory=list,
        description="Named individuals mentioned in the source, excluding authors unless they are subjects.",
    )
    figures_tags_hebrew: list[HebrewFigureTag] = Field(
        description="Hebrew labels derived from figure tags.",
    )

    @model_validator(mode="after")
    def validate_event_dates(self) -> Self:
        if self.event_date_from is None and self.event_date_to is None:
            return self

        if self.event_date_from is not None and self.event_date_to is None:
            raise ValueError("Event date to is required when event date from is filled")

        if (
            self.event_date_from is not None
            and self.event_date_to is not None
            and self.event_date_from > self.event_date_to
        ):
            raise ValueError("Event date from must be on or before event date to")

        if (
            self.published_date is not None
            and self.event_date_to is not None
            and self.event_date_to > self.published_date
        ):
            raise ValueError("Event date to must be on or before published date")

        return self

    @model_validator(mode='before')
    @classmethod
    def validate_title_before(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        data = data.copy()
        for field in ("english_title", "hebrew_title"):
            if isinstance(data.get(field), str):
                data[field] = _normalize_title(data[field])
        return data

    @field_validator("english_description", "hebrew_description", mode="after")
    @classmethod
    def normalize_description(cls, value: str) -> str:
        return _normalize_description(value)

    @model_validator(mode="after")
    def validate_title(self) -> Self:
        if (
            not ends_with_dot(self.english_title)
            and not ends_with_dot(self.hebrew_title)
        ):
            return self
        else:
            raise ValueError("Title must not end with a dot")

    @model_validator(mode="after")
    def validate_description(self) -> Self:
        if (
            ends_with_dot(self.english_description)
            and ends_with_dot(self.hebrew_description)
        ):
            return self
        else:
            raise ValueError("Description must end with a dot")

    @model_validator(mode="after")
    def validate_type(self) -> Self:
        if self.platform == "X" and self.type != "Post":
            raise ValueError("X type must be Post")
        return self


class CatalogRecord(CatalogSeed, CatalogDraft):
    @classmethod
    def from_patches(cls, seed: CatalogSeed, *patches: BaseModel) -> CatalogRecord:
        data = seed.model_dump()
        for patch in patches:
            data.update(patch.model_dump(exclude_none=True, exclude_unset=True))
        return cls(**data)
