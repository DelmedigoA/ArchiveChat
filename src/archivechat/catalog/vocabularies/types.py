"""Catalog type vocabulary generated from ArchiveAI Schema.xlsx."""

TYPE_LABELS_HE: dict[str, str] = {
    "Official Report": "דוח רשמי",
    "Official Statement": "הצהרה רשמית",
    "Opinion": "דעה",
    "Testimony": "עדות",
    "Journalistic Report": "דיווח עיתונאי",
    "Analysis": "ניתוח",
    "Open Letter": "מכתב פתוח",
    "News": "חדשות",
    "Post": "פוסט",
    "Poll": "סקר",
    "Press Release": "הודעה לעיתונות",
    "Interview": "ראיון",
}

TYPE_VALUES = tuple(TYPE_LABELS_HE)
TYPE_HEBREW_VALUES = tuple(
    value for value in TYPE_LABELS_HE.values() if value is not None
)

TYPES_EN = TYPE_VALUES
TYPES_HE = TYPE_HEBREW_VALUES
