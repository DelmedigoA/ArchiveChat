from datetime import date

from archivechat.compilation.workbook import _catalog, ARTICLE_TYPES


def test_article_type_scope_excludes_posts():
    assert "Post" not in ARTICLE_TYPES
    assert {"News", "Journalistic Report", "Analysis", "Testimony"} <= ARTICLE_TYPES


def test_catalog_normalizes_type_and_partial_event_dates():
    english = {
        "Number": 7,
        "Link": "https://example.com/article",
        "Title": "An article",
        "Description*": "A description.",
        "published Date": date(2024, 1, 20),
        "Event date from": date(2024, 1, 1),
        "Event date to": None,
        "Platform": "BBC",
        "Author": "Reporter",
        "Language": "English",
        "Type": "Journalistic report",
        "Media": "Text",
        "Theme (tag)": "News",
    }
    record = _catalog(english, {"Title": "מאמר", "Description*": "תיאור."})
    assert record.type == "Journalistic Report"
    assert record.published_date == date(2024, 1, 20)
    assert record.event_date_from is None
    assert record.event_date_to is None


def test_workbook_import_preserves_manifest_and_output_side_effects(tmp_path):
    import json

    from openpyxl import Workbook

    from archivechat.compilation.workbook import import_workbook

    english = {
        'Number': 1, 'Link': 'https://example.com/1', 'Title': 'An article',
        'Description*': 'A description.', 'published Date': date(2024, 1, 20),
        'Platform': 'BBC', 'Author': 'Reporter', 'Language': 'English',
        'Type': 'News', 'Media': 'Text',
    }
    rows = [
        english,
        {**english, 'Number': 2, 'Link': 'https://example.com/2'},
        {**english, 'Number': 3, 'Type': 'Post'},
        {**english, 'Number': 4, 'published Date': None},
    ]
    book = Workbook()
    book.active.title = 'english'
    book.active.append(list(english))
    for row in rows:
        book.active.append(list(row.values()))
    book.create_sheet('hebrew').append(['Number', 'Title', 'Description*'])
    workbook_path = tmp_path / 'catalog.xlsx'
    book.save(workbook_path)
    book.close()

    export_dir = tmp_path / 'exports'
    export = export_dir / 'saved'
    export.mkdir(parents=True)
    # ArchiveAI also emits JSON-encoded catalog strings.
    (export / 'output.json').write_text(json.dumps(_catalog(english, {}).model_dump_json()))
    (export / 'raw_content.json').write_text(json.dumps({
        'url': english['Link'], 'title': 'Saved title', 'text_body': '  Saved body.  ',
    }))
    output = tmp_path / 'compiled'
    output.mkdir()
    (output / 'catalog-only.json').write_text('{"contents": []}')
    (output / 'malformed.json').write_text('not json')

    entries = import_workbook(workbook_path, export_dir=export_dir, output_dir=output)

    assert [(entry.catalog_id, entry.status) for entry in entries] == [
        (1, 'content_available'), (2, 'catalog_only'), (4, 'invalid'),
    ]
    assert entries[0].archiveai_export == str(export)
    assert entries[2].error == 'catalog 4 has no publication date'
    assert not (output / 'catalog-only.json').exists()
    assert (output / 'malformed.json').read_text() == 'not json'
    compiled = output / f'{entries[0].item_id}.json'
    original_bytes = compiled.read_bytes()
    payload = json.loads(original_bytes)
    assert payload['contents'][0]['text_body'] == '  Saved body.  '
    assert payload['contents'][0]['representations'][0]['text'] == 'Saved body.'
    assert not (output / f'{entries[1].item_id}.json').exists()

    assert import_workbook(workbook_path, export_dir=export_dir, output_dir=output) == entries
    assert compiled.read_bytes() == original_bytes
