import json

from archivechat.compilation.fetch_missing import build_queue


def test_build_queue_is_bounded_and_idempotent(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps([
        {"catalog_id": 1, "item_id": "a", "url": "https://a", "status": "catalog_only"},
        {"catalog_id": 2, "item_id": "b", "url": "https://b", "status": "content_available"},
        {"catalog_id": 3, "item_id": "c", "url": "https://c", "status": "catalog_only"},
    ]))
    queue = tmp_path / "queue.jsonl"
    assert len(build_queue(manifest, queue, limit=1)) == 1
    assert len(build_queue(manifest, queue, limit=1)) == 1
    assert len(queue.read_text().splitlines()) == 2
