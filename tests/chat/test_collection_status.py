import json
from uuid import uuid4

import pytest

from archivelens.chat.collection import Collection


def test_catalog_only_item_is_excluded_from_rag_collection(tmp_path, item_data):
    data = item_data["catalog_record"].copy()
    data["english_title"] = "Catalog-only famine report"
    data["hebrew_title"] = "דוח רעב"
    data["english_description"] = "A catalog record without fetched article text."
    data["hebrew_description"] = "רשומת קטלוג ללא טקסט."
    item = {"id": str(uuid4()), "catalog_record": data, "contents": []}
    (tmp_path / "item.json").write_text(json.dumps(item))
    with pytest.raises(ValueError, match="No compiled items"):
        Collection(tmp_path)


def test_catalog_only_item_can_be_included_as_shallow_item(tmp_path, item_data):
    data = item_data["catalog_record"].copy()
    data["english_title"] = "Catalog-only famine report"
    data["english_description"] = "A catalog record without fetched article text."
    item = {"id": str(uuid4()), "catalog_record": data, "contents": []}
    (tmp_path / "item.json").write_text(json.dumps(item))

    collection = Collection(tmp_path, include_shallow_items=True)

    item_id = item["id"]
    assert collection.read(item_id)["contents"] == []
    assert collection.content_available[item_id] is False
    hit = collection.search("famine")[0]
    assert hit["item_id"] == item_id
    assert hit["content_status"] == "catalog_only"
    assert hit["content_available"] is False
