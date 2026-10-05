"""Conservative interpretation of repeated Square item/variation aggregates."""

from collections import defaultdict
from dataclasses import dataclass, replace
from decimal import Decimal
from app.services.square_report_labels import clean_report_label


@dataclass(frozen=True)
class ItemRow:
    item_name: str
    variation_name: str | None
    quantity: Decimal
    sales_amount: int
    # Only the text parser has layout evidence. Stored rows retain source order.
    child_like: bool = False
    follows_previous: bool = True


def normalize_items(rows: list[ItemRow]) -> tuple[list[ItemRow], list[str]]:
    """Fold exact repeats only with child indentation or repeated-label evidence.

    Identical totals alone do not prove a variation. In flattened email text,
    the same label must follow at least two different matching parent names.
    Explicit variation columns also supply known variation labels. Ambiguous
    pairs remain separate; unsupported child rows are excluded with a warning.
    No database rows are mutated.
    """
    rows = [replace(row, item_name=clean_report_label(row.item_name),
                    variation_name=clean_report_label(row.variation_name) if row.variation_name else None)
            for row in rows]
    parents_by_label: dict[str, set[str]] = defaultdict(set)
    known_variations = {r.variation_name.casefold() for r in rows if r.variation_name}
    for parent, child in zip(rows, rows[1:]):
        if (child.follows_previous and parent.variation_name is None and child.variation_name is None
                and parent.item_name.casefold() != child.item_name.casefold()
                and parent.quantity == child.quantity
                and parent.sales_amount == child.sales_amount):
            parents_by_label[child.item_name.casefold()].add(parent.item_name.casefold())
    known_variations.update(label for label, parents in parents_by_label.items() if len(parents) >= 2)
    result: list[ItemRow] = []
    warnings: list[str] = []
    index = 0
    while index < len(rows):
        parent = rows[index]
        if parent.child_like or (parent.variation_name is None and parent.item_name.casefold() in known_variations):
            warnings.append(f"Unassociated variation row {parent.item_name!r} excluded from item analysis; review the source layout.")
            index += 1
            continue
        child = rows[index + 1] if index + 1 < len(rows) else None
        if child and child.follows_previous and parent.variation_name is None and child.variation_name is None:
            matches = parent.quantity == child.quantity and parent.sales_amount == child.sales_amount
            child_evidence = child.child_like or child.item_name.casefold() in known_variations
            if matches and child_evidence and parent.item_name.casefold() != child.item_name.casefold():
                result.append(replace(parent, variation_name=child.item_name))
                index += 2
                continue
            if matches and not child_evidence:
                warnings.append(f"Equal adjacent item totals for {parent.item_name!r} and {child.item_name!r} lack variation evidence; kept separate.")
        result.append(parent)
        index += 1
    return result, list(dict.fromkeys(warnings))
