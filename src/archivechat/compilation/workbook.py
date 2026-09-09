"""Import the ArchiveAI ground-truth workbook as ArchiveLens catalog records.

The workbook is catalog metadata, not article text.  This importer therefore
creates valid catalog-only items and records whether matching ArchiveAI text
was found in the supplied export directory.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from openpyxl import load_workbook

from ..catalog import CatalogRecord
from ..models import Item
from ..catalog.vocabularies.countries_organizations import COUNTRIES_ORGANIZATIONS_LABELS_HE, COUNTRIES_ORGANIZATIONS_VALUES
from ..catalog.vocabularies.figures import FIGURE_LABELS_HE, FIGURE_VALUES
from ..catalog.vocabularies.languages import LANGUAGE_LABELS_HE, LANGUAGE_VALUES
from ..catalog.vocabularies.locations import LOCATION_LABELS_HE, LOCATION_VALUES
from ..catalog.vocabularies.media import MEDIA_LABELS_HE, MEDIA_VALUES
from ..catalog.vocabularies.platforms import PLATFORM_LABELS_HE, PLATFORM_VALUES
from ..catalog.vocabularies.themes import THEME_LABELS_HE, THEME_VALUES
from ..catalog.vocabularies.types import TYPE_LABELS_HE, TYPE_VALUES

ARTICLE_TYPES = frozenset({
    "Journalistic Report", "Journalistic report", "News", "Analysis", "Opinion",
    "Official Report", "Official Statement", "Press Release", "Open Letter",
    "Interview", "Poll", "Testimony",
})
LIST_FIELDS = {
    "source", "language", "media", "theme_tags", "countries_and_organizations_tags",
    "locations_tags", "figures_tags",
}
VOCABS = {
    "platform": PLATFORM_VALUES, "source": PLATFORM_VALUES, "language": LANGUAGE_VALUES,
    "type": TYPE_VALUES, "media": MEDIA_VALUES, "theme_tags": THEME_VALUES,
    "countries_and_organizations_tags": COUNTRIES_ORGANIZATIONS_VALUES,
    "locations_tags": LOCATION_VALUES, "figures_tags": FIGURE_VALUES,
}
HEBREW_LABELS = {
    "platform": PLATFORM_LABELS_HE, "language": LANGUAGE_LABELS_HE, "type": TYPE_LABELS_HE,
    "media": MEDIA_LABELS_HE, "theme_tags": THEME_LABELS_HE,
    "countries_and_organizations_tags": COUNTRIES_ORGANIZATIONS_LABELS_HE,
    "locations_tags": LOCATION_LABELS_HE, "figures_tags": FIGURE_LABELS_HE,
}
ALIASES = {("type", "Journalistic report"): "Journalistic Report"}
ENGLISH_COLUMNS = {
    "id": "Number", "link": "Link", "english_title": "Title", "english_description": "Description*",
    "published_date": "published Date", "event_date_from": "Event date from", "event_date_to": "Event date to",
    "platform": "Platform", "author": "Author", "source": "Source", "reference": "Reference",
    "location": "Location", "language": "Language", "type": "Type", "media": "Media",
    "theme_tags": "Theme (tag)", "countries_and_organizations_tags": "Countries & Organizations (tag)",
    "locations_tags": "Locations (tag)", "figures_tags": "Figures (tag)",
}


def _blank(value: Any) -> bool:
    return value is None or str(value).strip() in {"", "########"}


def _split(value: Any) -> list[str]:
    if _blank(value):
        return []
    return [part.strip().strip('"') for part in str(value).split(",") if part.strip().strip('"')]


def _date(value: Any) -> date | None:
    if _blank(value):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


def _value(field: str, value: Any) -> Any:
    if field in {"published_date", "event_date_from", "event_date_to"}:
        return _date(value)
    if field in LIST_FIELDS:
        values = _split(value)
        vocab = VOCABS.get(field, ())
        lookup = {str(v).casefold(): v for v in vocab}
        return [lookup.get(v.casefold(), ALIASES.get((field, v), v)) for v in values]
    if _blank(value):
        return None
    text = str(value).strip().strip('"')
    text = ALIASES.get((field, text), text)
    vocab = VOCABS.get(field, ())
    return {str(v).casefold(): v for v in vocab}.get(text.casefold(), text)


def _row_map(rows: list[tuple[Any, ...]]) -> dict[int, dict[str, Any]]:
    headers = [str(value).strip() if value is not None else None for value in rows[0]]
    result: dict[int, dict[str, Any]] = {}
    for row in rows[1:]:
        data = {header: value for header, value in zip(headers, row) if header}
        if _blank(data.get("Number")):
            continue
        result[int(data["Number"])] = data
    return result


def _catalog(english: dict[str, Any], hebrew: dict[str, Any]) -> CatalogRecord:
    data = {field: _value(field, english.get(column)) for field, column in ENGLISH_COLUMNS.items()}
    # The Hebrew sheet supplies missing dates and required Hebrew fields.
    for field, column in (("published_date", "published Date"), ("event_date_from", "Event date from"), ("event_date_to", "Event date to")):
        if data[field] is None:
            data[field] = _value(field, hebrew.get(column))
    data["hebrew_title"] = _value("hebrew_title", hebrew.get("Title")) or data["english_title"]
    data["hebrew_description"] = _value("hebrew_description", hebrew.get("Description*")) or data["english_description"]
    data["author_hebrew"] = _value("author_hebrew", hebrew.get("Author"))
    data["location_hebrew"] = _value("location_hebrew", hebrew.get("Location"))
    # These are deterministic labels in ArchiveAI; retain the source values.
    data["platform_hebrew"] = HEBREW_LABELS["platform"].get(data["platform"], data["platform"])
    for field, hebrew_field in (("language", "language_hebrew"), ("media", "media_hebrew"), ("type", "type_hebrew"), ("theme_tags", "theme_tags_hebrew"), ("countries_and_organizations_tags", "countries_and_organizations_tags_hebrew"), ("locations_tags", "locations_tags_hebrew"), ("figures_tags", "figures_tags_hebrew")):
        values = data.get(field) or [] if isinstance(data.get(field), list) else [data.get(field)]
        mapped = [HEBREW_LABELS[field].get(v, v) for v in values if v]
        data[hebrew_field] = mapped[0] if field == "type" and mapped else mapped
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
    if data.get("event_date_to") and data.get("published_date") and data["event_date_to"] > data["published_date"]:
        data["event_date_from"] = None
        data["event_date_to"] = None
    for field, hebrew_field in (("language", "language_hebrew"), ("media", "media_hebrew"), ("type", "type_hebrew"), ("theme_tags", "theme_tags_hebrew"), ("countries_and_organizations_tags", "countries_and_organizations_tags_hebrew"), ("locations_tags", "locations_tags_hebrew"), ("figures_tags", "figures_tags_hebrew")):
        values = data.get(field) if isinstance(data.get(field), list) else [data.get(field)]
        mapped = [HEBREW_LABELS[field].get(v, v) for v in values if v]
        data[hebrew_field] = mapped[0] if field == "type" and mapped else mapped
    data["source"] = data.get("source") or []
    data["reference"] = [v for v in (_split(english.get("Reference"))) if re.match(r"https?://", v)]
    data["followup_instructions"] = []
    if data.get("published_date") is None:
        raise ValueError(f"catalog {data['id']} has no publication date")
    return CatalogRecord.model_validate(data)


@dataclass(frozen=True)
class ManifestEntry:
    catalog_id: int
    item_id: str
    url: str
    type: str
    status: str
    archiveai_export: str | None = None
    error: str | None = None


def import_workbook(workbook: Path, *, export_dir: Path | None = None, output_dir: Path | None = None) -> list[ManifestEntry]:
    wb = load_workbook(workbook, read_only=True, data_only=True)
    english = _row_map(list(wb["english"].iter_rows(values_only=True)))
    hebrew = _row_map(list(wb["hebrew"].iter_rows(values_only=True)))
    exports = {}
    if export_dir:
        for folder in export_dir.iterdir():
            if not folder.is_dir() or not (folder / "output.json").exists():
                continue
            raw = json.loads((folder / "output.json").read_text())
            raw = json.loads(raw) if isinstance(raw, str) else raw
            exports[int(raw["id"])] = folder
    entries: list[ManifestEntry] = []
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        # The RAG directory is content-backed only. Remove catalog-only item
        # files produced by older importer versions; their metadata remains in
        # the manifest and can still be queued for acquisition.
        for path in output_dir.glob("*.json"):
            try:
                if not json.loads(path.read_text()).get("contents"):
                    path.unlink()
            except (OSError, ValueError, TypeError):
                continue
    for catalog_id, row in sorted(english.items()):
        if row.get("Type") not in ARTICLE_TYPES:
            continue
        try:
            record = _catalog(row, hebrew.get(catalog_id, {}))
        except (ValueError, TypeError) as exc:
            entries.append(ManifestEntry(catalog_id, "", str(row.get("Link", "")), str(row.get("Type", "")), "invalid", error=str(exc)))
            continue
        item_id = str(uuid5(NAMESPACE_URL, str(record.link)))
        export = exports.get(catalog_id)
        status = "content_available" if export else "catalog_only"
        entries.append(ManifestEntry(catalog_id, item_id, str(record.link), str(record.type), status, str(export) if export else None))
        if output_dir and export:
            from .articles import compile_article
            compiled = compile_article(export)
            item_path = output_dir / f"{item_id}.json"
            item_path.write_text(compiled.model_dump_json(indent=2) + "\n")
    return entries


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workbook", type=Path)
    parser.add_argument("--export-dir", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    entries = import_workbook(args.workbook, export_dir=args.export_dir, output_dir=args.output)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps([asdict(entry) for entry in entries], indent=2) + "\n")
    from collections import Counter
    print(json.dumps({"selected": len(entries), "statuses": Counter(e.status for e in entries)}, default=dict))


if __name__ == "__main__":
    main()
