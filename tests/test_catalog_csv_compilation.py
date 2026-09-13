import json
from pathlib import Path
from uuid import NAMESPACE_URL, uuid4, uuid5

from archivelens.chat.collection import Collection
from archivelens.compilation.catalog_csv import import_catalog_csv


def test_csv_compilation_creates_searchable_catalog_only_items(tmp_path: Path):
    source = tmp_path / 'archive.csv'
    source.write_text(
        'Title,Link,Platform,Published Date,Language,Type,Media,Theme Tags,Description\n'
        'Famine report,https://example.org/famine,Example,2024-01-01,English,Official Report,'
        'Text,"Famine, Humanitarian Aid",A catalog-only famine report.\n'
    )
    output = tmp_path / 'items'

    entries = import_catalog_csv(source, output_dir=output)

    item_id = str(uuid5(NAMESPACE_URL, 'https://example.org/famine'))
    assert entries[0].item_id == item_id
    item = json.loads((output / f'{item_id}.json').read_text())
    assert item['contents'] == []
    assert item['catalog_record']['english_title'] == 'Famine report'
    collection = Collection(output, include_shallow_items=True)
    assert collection.search('famine')[0]['item_id'] == item_id


def test_csv_compilation_preserves_existing_source_content(tmp_path: Path, item_data):
    url = item_data['catalog_record']['link']
    item_id = str(uuid5(NAMESPACE_URL, url))
    item_data['id'] = item_id
    item_data['contents'] = [
        {
            'kind': 'article',
            'id': str(uuid4()),
            'title': 'Fetched report',
            'url': url,
            'text_body': 'Readable source text.',
        }
    ]
    output = tmp_path / 'items'
    output.mkdir()
    (output / f'{item_id}.json').write_text(json.dumps(item_data))
    source = tmp_path / 'archive.csv'
    source.write_text(
        'Title,Link,Description\n'
        f'Refreshed catalog title,{url},Refreshed catalog description.\n'
    )

    import_catalog_csv(source, output_dir=output)

    item = json.loads((output / f'{item_id}.json').read_text())
    assert item['contents'][0]['text_body'] == 'Readable source text.'
    assert item['catalog_record']['english_title'] == 'Refreshed catalog title'
