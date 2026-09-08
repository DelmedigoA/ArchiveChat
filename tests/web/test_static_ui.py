from pathlib import Path


STATIC_APP = Path('src/archivechat/web/static/app.js')
STATIC_CSS = Path('src/archivechat/web/static/styles.css')


def test_archive_markdown_links_render_as_clickable_inline_citations():
    app_js = STATIC_APP.read_text()

    assert 'class="citation-link"' in app_js
    assert 'data-item-id' in app_js
    assert '[${number}]' in app_js
    assert 'citationNumbers' in app_js


def test_citation_links_are_styled():
    styles = STATIC_CSS.read_text()

    assert '.citation-link' in styles
    assert 'border-radius: 999px' in styles
