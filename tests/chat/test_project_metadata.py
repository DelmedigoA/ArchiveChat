import json

from archivechat.chat.project_metadata import PROJECT_METADATA_PATH, ProjectMetadataCollection


def test_project_metadata_lists_records_without_full_content(tmp_path):
    path = tmp_path / 'metadata.json'
    path.write_text(json.dumps([
        {
            'id': 'overview',
            'kind': 'project_metadata',
            'title': 'Project overview',
            'description': 'What this archive is',
            'language': 'en',
            'content': 'Full private-ish project context.',
        }
    ]))

    metadata = ProjectMetadataCollection(path)

    assert metadata.list_records() == [{
        'record_id': 'overview',
        'kind': 'project_metadata',
        'title': 'Project overview',
        'description': 'What this archive is',
        'language': 'en',
    }]


def test_project_metadata_reads_full_record_and_handles_missing_ids(tmp_path):
    path = tmp_path / 'metadata.json'
    path.write_text(json.dumps([
        {
            'id': 'document-record',
            'kind': 'document_metadata',
            'title': 'Bearing Witness - Gaza Document',
            'description': 'Document metadata',
            'language': 'en',
            'content': {'version': 'v6.7.0'},
        }
    ]))

    metadata = ProjectMetadataCollection(path)

    assert metadata.read('document-record')['content'] == {'version': 'v6.7.0'}
    assert metadata.read('missing') == {'error': 'Unknown project metadata record ID'}


def test_default_project_metadata_contains_document_and_hebrew_about_records():
    metadata = ProjectMetadataCollection(PROJECT_METADATA_PATH)

    records = {record['record_id']: record for record in metadata.list_records()}

    assert records['about-bearing-witness-gaza']['kind'] == 'project_about_metadata'
    assert records['document-record']['kind'] == 'document_metadata'
    assert records['lee-mordechai-author']['kind'] == 'author_metadata'
    assert records['author-and-document-about-he']['language'] == 'he'
    assert records['about-bearing-witness-gaza']['source_url'] == 'https://bearing-witness.com/about/'
    assert 'open knowledge space' in metadata.read('about-bearing-witness-gaza')['content']
    assert metadata.read('document-record')['content']['version'] == 'v6.7.0'
    lee = metadata.read('lee-mordechai-author')['content']
    assert lee['name'] == 'Dr. Lee Mordechai'
    assert 'working at an Israeli university' in lee['summary']
    assert lee['source_record_id'] == 'author-and-document-about-he'
    assert 'לי מרדכי' in metadata.read('author-and-document-about-he')['content']


def test_default_project_metadata_contains_website_navigation_records():
    metadata = ProjectMetadataCollection(PROJECT_METADATA_PATH)

    records = {record['record_id']: record for record in metadata.list_records()}
    navigation = metadata.read('website-navigation-directory')['content']
    sitemap = metadata.read('website-sitemap-inventory')['content']

    assert records['website-navigation-directory']['kind'] == 'website_metadata'
    assert records['website-navigation-directory']['crawled_at'] == '2026-09-08'
    assert records['website-sitemap-inventory']['kind'] == 'website_sitemap_metadata'
    assert records['website-sitemap-inventory']['crawled_at'] == '2026-09-08'
    destruction_example = next(
        example for example in navigation['recommendation_examples']
        if example['recommended_url'] == 'https://bearing-witness.com/destruction/'
    )
    assert 'building damage' in destruction_example['user_interest']
    assert 'built environment' in destruction_example['user_interest']
    assert 'satellite-based damage assessment' in destruction_example['user_interest']
    assert any(
        item['url'] == 'https://www.instagram.com/bearingwitnessgaza/'
        for item in navigation['social_links']
    )
    assert sitemap['total_sitemap_url_entries'] == 961
