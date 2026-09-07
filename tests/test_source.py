from pathlib import Path
from uuid import UUID

import pytest
from pydantic import ValidationError

from src.catalog import CatalogRecord
from src.source import Source


@pytest.fixture
def source_data():
    """A source payload as it might be loaded from stored JSON."""
    return {
        "id": "b9c9d64b-7243-4f0f-a15e-937efb7c3d28",
        "path": "data/dummy_docs/doc_1.txt",
        "archive_record": {
            "id": 1,
            "link": "https://example.com/cats",
            "english_title": "Cats",
            "hebrew_title": "חתולים",
            "english_description": "Cats are beautiful creatures.",
            "hebrew_description": "חתולים הם יצורים יפים.",
            "published_date": "2026-09-07",
            "platform": "BBC",
            "platform_hebrew": "BBC",
            "author": "Example Author",
            "language": ["English"],
            "language_hebrew": ["אנגלית"],
            "type": "News",
            "type_hebrew": "חדשות",
            "media": ["Text"],
            "media_hebrew": ["טקסט"],
            "theme_tags": [],
            "theme_tags_hebrew": [],
            "figures_tags_hebrew": [],
        },
    }


def test_source_parses_strings_and_nested_catalog(source_data):
    source = Source.model_validate(source_data)

    assert source.id == UUID(source_data["id"])
    assert source.path == Path("data/dummy_docs/doc_1.txt")
    assert isinstance(source.archive_record, CatalogRecord)
    assert source.archive_record.english_description == "Cats are beautiful creatures."
    assert source.archive_record.id == 1  # Catalog row ID is separate from source UUID.


def test_source_json_round_trip(source_data):
    source = Source.model_validate(source_data)

    restored = Source.model_validate_json(source.model_dump_json())

    assert restored == source


@pytest.mark.parametrize("field", ["id", "path", "archive_record"])
def test_source_requires_fields(source_data, field):
    del source_data[field]

    with pytest.raises(ValidationError) as exc:
        Source.model_validate(source_data)

    assert any(
        error["loc"] == (field,) and error["type"] == "missing"
        for error in exc.value.errors()
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [("id", "not-a-uuid"), ("path", 123), ("archive_record", None)],
)
def test_source_rejects_invalid_values(source_data, field, value):
    source_data[field] = value

    with pytest.raises(ValidationError) as exc:
        Source.model_validate(source_data)

    assert any(error["loc"] == (field,) for error in exc.value.errors())


def test_source_validates_nested_catalog_tags(source_data):
    source_data["archive_record"]["theme_tags"] = ["not-a-catalog-tag"]

    with pytest.raises(ValidationError) as exc:
        Source.model_validate(source_data)

    assert any(
        error["loc"] == ("archive_record", "theme_tags", 0)
        for error in exc.value.errors()
    )


def test_source_reports_missing_catalog_title(source_data):
    del source_data["archive_record"]["english_title"]

    with pytest.raises(ValidationError) as exc:
        Source.model_validate(source_data)

    assert any(
        error["loc"] == ("archive_record", "english_title")
        and error["type"] == "missing"
        for error in exc.value.errors()
    )
