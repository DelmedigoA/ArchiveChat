"""Catalog language vocabulary generated from ArchiveAI Schema.xlsx."""

LANGUAGE_LABELS_HE: dict[str, str] = {
    "English": "אנגלית",
    "French": "צרפתית",
    "Hebrew": "עברית",
    "Arabic": "ערבית",
}

LANGUAGE_VALUES = tuple(LANGUAGE_LABELS_HE)
LANGUAGE_HEBREW_VALUES = tuple(
    value for value in LANGUAGE_LABELS_HE.values() if value is not None
)
