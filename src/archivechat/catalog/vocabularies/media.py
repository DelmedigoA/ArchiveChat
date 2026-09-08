"""Catalog media vocabulary generated from ArchiveAI Schema.xlsx."""

MEDIA_LABELS_HE: dict[str, str] = {
    "Video": "וידאו",
    "Photo": "תמונה",
    "Audio": "אודיו",
    "Text": "טקסט",
    "Map": "מפה",
    "Chart": "גרף",
}

MEDIA_VALUES = tuple(MEDIA_LABELS_HE)
MEDIA_HEBREW_VALUES = tuple(
    value for value in MEDIA_LABELS_HE.values() if value is not None
)
