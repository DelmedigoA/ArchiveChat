from uuid import UUID

import pytest
from pydantic import ValidationError

from archivelens.catalog import CatalogRecord
from archivelens.models.item import Item


def test_item_requires_identity():
    with pytest.raises(ValidationError) as exc:
        Item.model_validate({})

    assert any(
        error["loc"] == ("id",) and error["type"] == "missing"
        for error in exc.value.errors()
    )


def test_item_rejects_invalid_identity():
    with pytest.raises(ValidationError) as exc:
        Item(id="not-a-uuid")

    assert any(error["loc"] == ("id",) for error in exc.value.errors())


def test_item_reports_missing_catalog_title(item_data):
    del item_data["catalog_record"]["english_title"]

    with pytest.raises(ValidationError) as exc:
        Item.model_validate(item_data)

    assert any(
        error["loc"] == ("catalog_record", "english_title")
        and error["type"] == "missing"
        for error in exc.value.errors()
    )


def test_cataloged_item_does_not_require_a_content_file(item_data):
    item = Item.model_validate({
        "id": item_data["id"],
        "catalog_record": item_data["catalog_record"],
    })

    assert item.id == UUID(item_data["id"])
    assert isinstance(item.catalog_record, CatalogRecord)
    assert item.catalog_record.id == 1
    assert item.catalog_record.english_title == "Cats"
    assert Item.model_validate_json(item.model_dump_json()) == item


def test_item_can_exist_without_rich_catalog_metadata(item_data):
    item = Item(id=item_data["id"])

    assert item.catalog_record is None


def test_item_preserves_catalog_validation(item_data):
    record = item_data["catalog_record"]
    record["theme_tags"] = ["not-a-catalog-tag"]

    with pytest.raises(ValidationError) as exc:
        Item(id=item_data["id"], catalog_record=record)

    assert any(
        error["loc"] == ("catalog_record", "theme_tags", 0)
        for error in exc.value.errors()
    )
