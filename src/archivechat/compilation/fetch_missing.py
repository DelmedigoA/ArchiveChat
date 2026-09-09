"""Create an idempotent acquisition queue for ArchiveAI's fetcher."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def build_queue(manifest: Path, output: Path, limit: int | None = None) -> list[dict]:
    rows = json.loads(manifest.read_text())
    existing = {}
    if output.exists():
        existing = {row["catalog_id"]: row for row in (json.loads(line) for line in output.read_text().splitlines() if line.strip())}
    queue = []
    for row in rows:
        if row["status"] != "catalog_only" or not row.get("url"):
            continue
        if row["catalog_id"] in existing:
            continue
        queue.append({
            "catalog_id": row["catalog_id"],
            "url": row["url"],
            "item_id": row["item_id"],
            "status": "pending",
        })
        if limit is not None and len(queue) >= limit:
            break
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("a") as handle:
        for row in queue:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return queue


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("data/archiveai/acquisition-queue.jsonl"))
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    queue = build_queue(args.manifest, args.output, args.limit)
    print(json.dumps({"queued": len(queue), "output": str(args.output)}))


if __name__ == "__main__":
    main()
