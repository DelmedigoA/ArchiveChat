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
