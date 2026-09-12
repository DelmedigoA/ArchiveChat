import pytest


@pytest.fixture
def item_data():
    """An item payload as it might be loaded from stored JSON."""
    return {
        "id": "b9c9d64b-7243-4f0f-a15e-937efb7c3d28",
        "catalog_record": {
            "id": 1,
            "link": "https://example.com/cats",
            "english_title": "Cats",
            "hebrew_title": "חתולים",
            "english_description": "Cats are beautiful creatures.",
            "hebrew_description": "חתולים הם יצורים יפים.",
            "published_date": "2026-09-07",
            "platform": "BBC",
            "platform_hebrew": "BBC",
            "author": "Example Author",
            "language": ["English"],
            "language_hebrew": ["אנגלית"],
            "type": "News",
            "type_hebrew": "חדשות",
            "media": ["Text"],
            "media_hebrew": ["טקסט"],
            "theme_tags": [],
            "theme_tags_hebrew": [],
            "figures_tags_hebrew": [],
        },
    }
