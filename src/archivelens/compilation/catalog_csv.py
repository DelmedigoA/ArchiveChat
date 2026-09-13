"""Compile the Bearing Witness archive CSV into catalog-only ArchiveLens items."""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from ..models import Item, ShallowCatalogRecord


@dataclass(frozen=True)
class CsvManifestEntry:
    row_number: int
    item_id: str
    url: str
    status: str


def import_catalog_csv(csv_path: Path, *, output_dir: Path | None = None) -> list[CsvManifestEntry]:
    """Compile every CSV row while preserving fetched content for matching URLs."""
    existing = _items_by_url(output_dir) if output_dir else {}
    entries: list[CsvManifestEntry] = []
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
    with csv_path.open(newline='', encoding='utf-8-sig') as source:
        for row_number, row in enumerate(csv.DictReader(source), 1):
            record = catalog_from_csv_row(row, row_number)
            identity = record.link or f'{csv_path.name}:{row_number}'
            item_id = str(uuid5(NAMESPACE_URL, identity))
            prior = existing.get(record.link)
            item = Item(
                id=item_id,
                catalog_record=record,
                contents=prior.contents if prior else [],
            )
            status = 'content_available' if item.contents else 'catalog_only'
            entries.append(CsvManifestEntry(row_number, item_id, record.link, status))
            if output_dir:
                (output_dir / f'{item_id}.json').write_text(item.model_dump_json(indent=2) + '\n')
    return entries


def catalog_from_csv_row(row: dict[str, str | None], row_number: int) -> ShallowCatalogRecord:
    return ShallowCatalogRecord(
        id=str(row_number),
        english_title=_value(row, 'Title'),
        english_description=_value(row, 'Description'),
        link=_value(row, 'Link'),
        platform=_value(row, 'Platform'),
        published_date=_value(row, 'Published Date'),
        event_date_from=_value(row, 'Event Date From'),
        event_date_to=_value(row, 'Event Date To'),
        author=_value(row, 'Author'),
        reference=_value(row, 'Reference'),
        language=_values(row, 'Language'),
        location=_value(row, 'Location'),
        type=_value(row, 'Type'),
        media=_values(row, 'Media'),
        theme_tags=_values(row, 'Theme Tags'),
        countries_and_organizations_tags=_values(row, 'Organizations Tags'),
        locations_tags=_values(row, 'Location Tags'),
        figures_tags=_values(row, 'Figures Tags'),
    )


def _items_by_url(output_dir: Path) -> dict[str, Item]:
    if not output_dir.exists():
        return {}
    records = {}
    for path in output_dir.glob('*.json'):
        item = Item.model_validate_json(path.read_text())
        if item.catalog_record and item.catalog_record.link:
            records[str(item.catalog_record.link)] = item
    return records


def _value(row: dict[str, str | None], field: str) -> str:
    return (row.get(field) or '').strip()


def _values(row: dict[str, str | None], field: str) -> list[str]:
    return [part.strip() for part in _value(row, field).split(',') if part.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv_path', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--manifest', type=Path)
    args = parser.parse_args()
    entries = import_catalog_csv(args.csv_path, output_dir=args.output)
    if args.manifest:
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(json_dumps([asdict(entry) for entry in entries]) + '\n')
    print(f'Compiled {len(entries)} CSV rows into {args.output}')


def json_dumps(value) -> str:
    import json

    return json.dumps(value, indent=2)


if __name__ == '__main__':
    main()
