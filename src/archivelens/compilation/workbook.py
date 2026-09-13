"""Import the ArchiveAI ground-truth workbook as ArchiveLens catalog records.

The workbook is catalog metadata, not article text.  This importer therefore
creates valid catalog-only items and records whether matching ArchiveAI text
was found in the supplied export directory.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from openpyxl import load_workbook

# Compatibility imports retain the original workbook helper names.
from .workbook_rows import (
    ALIASES,
    ENGLISH_COLUMNS,
    HEBREW_LABELS,
    LIST_FIELDS,
    VOCABS,
    catalog_from_rows,
    rows_by_catalog_id,
    catalog_from_rows as _catalog,
    rows_by_catalog_id as _row_map,
    is_blank as _blank,
    split_values as _split,
    clean_date as _date,
    normalize_value as _value,
)
from ..models import Item

ARTICLE_TYPES = frozenset(
    {
        "Journalistic Report",
        "Journalistic report",
        "News",
        "Analysis",
        "Opinion",
        "Official Report",
        "Official Statement",
        "Press Release",
        "Open Letter",
        "Interview",
        "Poll",
        "Testimony",
    }
)


@dataclass(frozen=True)
class ManifestEntry:
    catalog_id: int
    item_id: str
    url: str
    type: str
    status: str
    archiveai_export: str | None = None
    error: str | None = None


def import_workbook(
    workbook: Path, *, export_dir: Path | None = None, output_dir: Path | None = None
) -> list[ManifestEntry]:
    wb = load_workbook(workbook, read_only=True, data_only=True)
    english = rows_by_catalog_id(list(wb["english"].iter_rows(values_only=True)))
    hebrew = rows_by_catalog_id(list(wb["hebrew"].iter_rows(values_only=True)))
    exports = find_exports(export_dir)
    entries: list[ManifestEntry] = []
    prepare_output_directory(output_dir)
    for catalog_id, row in sorted(english.items()):
        if row.get("Type") not in ARTICLE_TYPES:
            continue
        try:
            record = catalog_from_rows(row, hebrew.get(catalog_id, {}))
        except (ValueError, TypeError) as exc:
            entries.append(
                ManifestEntry(
                    catalog_id,
                    "",
                    str(row.get("Link", "")),
                    str(row.get("Type", "")),
                    "invalid",
                    error=str(exc),
                )
            )
            continue
        item_id = str(uuid5(NAMESPACE_URL, str(record.link)))
        export = exports.get(catalog_id)
        status = "content_available" if export else "catalog_only"
        entries.append(
            ManifestEntry(
                catalog_id,
                item_id,
                str(record.link),
                str(record.type),
                status,
                str(export) if export else None,
            )
        )
        if output_dir:
            if export:
                from .articles import compile_article

                compiled = compile_article(export)
            else:
                compiled = Item(id=item_id, catalog_record=record)
            item_path = output_dir / f"{item_id}.json"
            item_path.write_text(compiled.model_dump_json(indent=2) + "\n")
    return entries


def find_exports(export_dir: Path | None) -> dict[int, Path]:
    """Index saved ArchiveAI catalog exports by their source catalog ID."""
    exports = {}
    if export_dir:
        for folder in export_dir.iterdir():
            if not folder.is_dir() or not (folder / "output.json").exists():
                continue
            raw = json.loads((folder / "output.json").read_text())
            raw = json.loads(raw) if isinstance(raw, str) else raw
            exports[int(raw["id"])] = folder
    return exports


def prepare_output_directory(output_dir: Path | None) -> None:
    """Prepare the retrieval directory while preserving valid catalog items."""
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        # Remove only legacy placeholder files. Valid catalog-only items have
        # an id and catalog record, and remain available to the opt-in
        # full-catalog runtime.
        for path in output_dir.glob("*.json"):
            try:
                payload = json.loads(path.read_text())
                if payload.get("contents") == [] and not payload.get("id"):
                    path.unlink()
            except OSError, ValueError, TypeError:
                continue


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

    print(
        json.dumps(
            {"selected": len(entries), "statuses": Counter(e.status for e in entries)}, default=dict
        )
    )


if __name__ == "__main__":
    main()
