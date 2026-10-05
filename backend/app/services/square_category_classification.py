"""Application interpretation of raw Square labels, not Square metadata."""
from app.services.square_report_labels import clean_report_label

CATEGORY_GROUPS = {
    "operational_routing": {"Kitchen Print", "Sushi Print", "Both Printers"},
    "menu_category": {
        "Beer", "Wine", "Coffee & Tea", "Salads & Soups", "Poke Bowls",
        "Yaki Soba & Yaki Udon", "Beverage", "Beverages & Extra Sauces",
        "Beverage / Beverages & Extra Sauces", "Sushi Rolls", "Donburi & Katsu",
        "Appetizers",
    },
    "uncategorized": {"Uncategorized"},
}


def _key(label: str) -> str:
    return " ".join(clean_report_label(label).split()).casefold()


CATEGORY_CLASSIFICATIONS = {
    _key(label): kind for kind, labels in CATEGORY_GROUPS.items() for label in labels
}


def classify_category(label: str) -> str:
    return CATEGORY_CLASSIFICATIONS.get(_key(label), "unknown")
