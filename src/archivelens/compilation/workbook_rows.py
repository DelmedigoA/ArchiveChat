"""Normalize paired English/Hebrew workbook rows into existing catalog records."""

import re
from datetime import date, datetime
from typing import Any

from ..catalog import CatalogRecord
from ..catalog.vocabularies.countries_organizations import (
    COUNTRIES_ORGANIZATIONS_LABELS_HE,
    COUNTRIES_ORGANIZATIONS_VALUES,
)
from ..catalog.vocabularies.figures import FIGURE_LABELS_HE, FIGURE_VALUES
from ..catalog.vocabularies.languages import LANGUAGE_LABELS_HE, LANGUAGE_VALUES
from ..catalog.vocabularies.locations import LOCATION_LABELS_HE, LOCATION_VALUES
from ..catalog.vocabularies.media import MEDIA_LABELS_HE, MEDIA_VALUES
from ..catalog.vocabularies.platforms import PLATFORM_LABELS_HE, PLATFORM_VALUES
from ..catalog.vocabularies.themes import THEME_LABELS_HE, THEME_VALUES
from ..catalog.vocabularies.types import TYPE_LABELS_HE, TYPE_VALUES


LIST_FIELDS = {
    "source",
    "language",
    "media",
    "theme_tags",
    "countries_and_organizations_tags",
    "locations_tags",
    "figures_tags",
}
VOCABS = {
    "platform": PLATFORM_VALUES,
    "source": PLATFORM_VALUES,
    "language": LANGUAGE_VALUES,
    "type": TYPE_VALUES,
    "media": MEDIA_VALUES,
    "theme_tags": THEME_VALUES,
    "countries_and_organizations_tags": COUNTRIES_ORGANIZATIONS_VALUES,
    "locations_tags": LOCATION_VALUES,
    "figures_tags": FIGURE_VALUES,
}
HEBREW_LABELS = {
    "platform": PLATFORM_LABELS_HE,
    "language": LANGUAGE_LABELS_HE,
    "type": TYPE_LABELS_HE,
    "media": MEDIA_LABELS_HE,
    "theme_tags": THEME_LABELS_HE,
    "countries_and_organizations_tags": COUNTRIES_ORGANIZATIONS_LABELS_HE,
    "locations_tags": LOCATION_LABELS_HE,
    "figures_tags": FIGURE_LABELS_HE,
}
ALIASES = {("type", "Journalistic report"): "Journalistic Report"}
ENGLISH_COLUMNS = {
    "id": "Number",
    "link": "Link",
    "english_title": "Title",
    "english_description": "Description*",
    "published_date": "published Date",
    "event_date_from": "Event date from",
    "event_date_to": "Event date to",
    "platform": "Platform",
    "author": "Author",
    "source": "Source",
    "reference": "Reference",
    "location": "Location",
    "language": "Language",
    "type": "Type",
    "media": "Media",
    "theme_tags": "Theme (tag)",
    "countries_and_organizations_tags": "Countries & Organizations (tag)",
    "locations_tags": "Locations (tag)",
    "figures_tags": "Figures (tag)",
}


def is_blank(value: Any) -> bool:
    return value is None or str(value).strip() in {"", "########"}


def split_values(value: Any) -> list[str]:
    if is_blank(value):
        return []
    return [part.strip().strip('"') for part in str(value).split(",") if part.strip().strip('"')]


def clean_date(value: Any) -> date | None:
    if is_blank(value):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


def normalize_value(field: str, value: Any) -> Any:
    if field in {"published_date", "event_date_from", "event_date_to"}:
        return clean_date(value)
    if field in LIST_FIELDS:
        values = split_values(value)
        vocab = VOCABS.get(field, ())
        lookup = {str(v).casefold(): v for v in vocab}
        return [lookup.get(v.casefold(), ALIASES.get((field, v), v)) for v in values]
    if is_blank(value):
        return None
    text = str(value).strip().strip('"')
    text = ALIASES.get((field, text), text)
    vocab = VOCABS.get(field, ())
    return {str(v).casefold(): v for v in vocab}.get(text.casefold(), text)


def rows_by_catalog_id(rows: list[tuple[Any, ...]]) -> dict[int, dict[str, Any]]:
    headers = [str(value).strip() if value is not None else None for value in rows[0]]
    result: dict[int, dict[str, Any]] = {}
    for row in rows[1:]:
        data = {header: value for header, value in zip(headers, row) if header}
        if is_blank(data.get("Number")):
            continue
        result[int(data["Number"])] = data
    return result


def catalog_from_rows(english: dict[str, Any], hebrew: dict[str, Any]) -> CatalogRecord:
    data = {
        field: normalize_value(field, english.get(column))
        for field, column in ENGLISH_COLUMNS.items()
    }
    # The Hebrew sheet supplies missing dates and required Hebrew fields.
    for field, column in (
        ("published_date", "published Date"),
        ("event_date_from", "Event date from"),
        ("event_date_to", "Event date to"),
    ):
        if data[field] is None:
            data[field] = normalize_value(field, hebrew.get(column))
    data["hebrew_title"] = (
        normalize_value("hebrew_title", hebrew.get("Title")) or data["english_title"]
    )
    data["hebrew_description"] = (
        normalize_value("hebrew_description", hebrew.get("Description*"))
        or data["english_description"]
    )
    data["author_hebrew"] = normalize_value("author_hebrew", hebrew.get("Author"))
    data["location_hebrew"] = normalize_value("location_hebrew", hebrew.get("Location"))
    # These are deterministic labels in ArchiveAI; retain the source values.
    data["platform_hebrew"] = HEBREW_LABELS["platform"].get(data["platform"], data["platform"])
    data["author"] = data.get("author") or data.get("platform") or data["english_title"]
    # Ground-truth rows occasionally contain stale tags or partial event
    # ranges. Keep the catalog record valid while preserving the source URL
    # and stable ID; the raw workbook remains the provenance for corrections.
    for field, vocab in VOCABS.items():
        if field in LIST_FIELDS:
            data[field] = [value for value in data.get(field, []) if value in vocab]
        elif data.get(field) not in vocab:
            data[field] = next(iter(vocab), "")
    if data.get("event_date_from") and not data.get("event_date_to"):
        data["event_date_from"] = None
    if (
        data.get("event_date_to")
        and data.get("published_date")
        and data["event_date_to"] > data["published_date"]
    ):
        data["event_date_from"] = None
        data["event_date_to"] = None
    apply_hebrew_labels(data)
    data["source"] = data.get("source") or []
    data["reference"] = [
        v for v in (split_values(english.get("Reference"))) if re.match(r"https?://", v)
    ]
    data["followup_instructions"] = []
    if data.get("published_date") is None:
        raise ValueError(f"catalog {data['id']} has no publication date")
    return CatalogRecord.model_validate(data)


def apply_hebrew_labels(data: dict[str, Any]) -> None:
    """Derive the paired Hebrew labels from the current English values."""
    for field, hebrew_field in (
        ("language", "language_hebrew"),
        ("media", "media_hebrew"),
        ("type", "type_hebrew"),
        ("theme_tags", "theme_tags_hebrew"),
        ("countries_and_organizations_tags", "countries_and_organizations_tags_hebrew"),
        ("locations_tags", "locations_tags_hebrew"),
        ("figures_tags", "figures_tags_hebrew"),
    ):
        values = data.get(field) if isinstance(data.get(field), list) else [data.get(field)]
        mapped = [HEBREW_LABELS[field].get(v, v) for v in values if v]
        data[hebrew_field] = mapped[0] if field == "type" and mapped else mapped
