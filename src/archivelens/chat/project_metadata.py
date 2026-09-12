"""Project-level metadata records, separate from evidence retrieval."""

import json
from pathlib import Path
from typing import Any

PROJECT_METADATA_PATH = Path(__file__).resolve().parents[3] / 'data' / 'project-metadata' / 'bearing-witness.json'


class ProjectMetadataCollection:
    """Read metadata records about the project, document, website crawl, and author context."""

    def __init__(self, path: Path = PROJECT_METADATA_PATH):
        self.path = path
        raw = json.loads(path.read_text())
        self.records: dict[str, dict[str, Any]] = {}
        for record in raw:
            record_id = str(record['id'])
            if record_id in self.records:
                raise ValueError(f'Duplicate project metadata record ID: {record_id}')
            self.records[record_id] = {
                'record_id': record_id,
                'kind': str(record['kind']),
                'title': str(record['title']),
                'description': str(record.get('description') or ''),
                'language': str(record.get('language') or ''),
                'source_url': str(record.get('source_url') or ''),
                'content': record.get('content'),
            }
        if not self.records:
            raise ValueError(f'No project metadata records in {path}')

    def list_records(self) -> list[dict]:
        """List metadata records without returning full content."""
        listed = []
        for record in self.records.values():
            item = {
                'record_id': record['record_id'],
                'kind': record['kind'],
                'title': record['title'],
                'description': record['description'],
                'language': record['language'],
            }
            if record['source_url']:
                item['source_url'] = record['source_url']
            crawled_at = record['content'].get('crawled_at') if isinstance(record['content'], dict) else None
            if crawled_at:
                item['crawled_at'] = str(crawled_at)
            listed.append(item)
        return listed

    def read(self, record_id: str) -> dict:
        """Read a project metadata record by ID."""
        return self.records.get(record_id) or {'error': 'Unknown project metadata record ID'}
