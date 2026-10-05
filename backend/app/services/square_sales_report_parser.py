import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.services.square_item_normalization import ItemRow, normalize_items
from app.services.square_report_labels import clean_report_label


class SquareSalesReportParseError(ValueError):
    """Raised when report text cannot be safely normalized."""


class ParsedDiscount(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    discount_name: str = Field(min_length=1, max_length=200)
    usage_count: int = Field(ge=0)
    amount: int


class ParsedCategorySales(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    category_name: str = Field(min_length=1, max_length=200)
    quantity: Decimal = Field(ge=0)
    sales_amount: int


class ParsedItemSales(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    item_name: str = Field(min_length=1, max_length=200)
    variation_name: str | None = Field(default=None, max_length=200)
    quantity: Decimal = Field(ge=0)
    sales_amount: int


class ParsedSquareSalesReport(BaseModel):
    """Validated, transaction-free facts extracted from Square report text."""

    report_name: str | None = None
    report_start: date
    report_end: date
    reported_at: datetime | None = None

    gross_sales_amount: int
    item_sales_amount: int
    service_charge_amount: int
    returns_amount: int
    discount_comp_amount: int
    net_sales_amount: int
    tax_amount: int
    tips_amount: int
    gift_card_sales_amount: int
    refund_amount: int
    total_amount: int
    total_collected_amount: int
    fees_amount: int
    net_total_amount: int

    discounts: list[ParsedDiscount] = Field(default_factory=list)
    categories: list[ParsedCategorySales] = Field(default_factory=list)
    items: list[ParsedItemSales] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_period(self):
        if self.report_start >= self.report_end:
            raise ValueError("Report start date must be before report end date.")
        return self


_DATE = (
    r"(?:"
    r"\d{4}-\d{1,2}-\d{1,2}"
    r"|\d{1,2}/\d{1,2}/\d{4}"
    r"|(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
    r"Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|"
    r"Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2},?\s+\d{4}"
    r")"
)
_DATE_RANGE_RE = re.compile(
    rf"(?P<start>{_DATE})(?:\s+\d{{1,2}}:\d{{2}}\s*(?:AM|PM))?"
    rf"\s*(?:through|to|[-–—])\s*"
    rf"(?P<end>{_DATE})(?:\s+\d{{1,2}}:\d{{2}}\s*(?:AM|PM))?",
    re.IGNORECASE,
)
_QUANTITY_RE = re.compile(
    r"^[×x]\s*(?P<quantity>\d+(?:\.\d+)?)$",
    re.IGNORECASE,
)
_VERTICAL_MONEY_RE = re.compile(
    r"^\(?\s*-?\s*\$?\s*"
    r"(?:\d{1,3}(?:,\d{3})+|\d+)"
    r"(?:\.\d{1,2})?\s*\)?$"
)
_ROW_RE = re.compile(
    r"^(?P<label>.*?)\s+"
    r"(?P<quantity>\d+(?:\.\d+)?)\s+"
    r"(?P<amount>\(?\s*-?\s*\$?\s*"
    r"(?:\d{1,3}(?:,\d{3})+|\d+)"
    r"(?:\.\d{1,2})?\s*\)?)$"
)
_METRIC_ALIASES = {
    "gross sales": "gross_sales_amount",
    "items": "item_sales_amount",
    "item sales": "item_sales_amount",
    "service charges": "service_charge_amount",
    "returns": "returns_amount",
    "discounts & comps": "discount_comp_amount",
    "discounts and comps": "discount_comp_amount",
    "net sales": "net_sales_amount",
    "tax": "tax_amount",
    "tips": "tips_amount",
    "gift card sales": "gift_card_sales_amount",
    "refunds by amount": "refund_amount",
    "total": "total_amount",
}
_PAYMENT_ALIASES = {
    "total collected": "total_collected_amount",
    "fees": "fees_amount",
    "net total": "net_total_amount",
}
_REQUIRED_METRICS = tuple(
    dict.fromkeys((*_METRIC_ALIASES.values(), *_PAYMENT_ALIASES.values()))
)
_SECTION_ALIASES = {
    "sales": "sales",
    "payments": "payments",
    "discounts applied": "discounts",
    "category sales": "categories",
    "item sales": "items",
}
def parse_currency_to_cents(raw_value: str) -> int:
    """Parse a whole currency value into integer cents without rounding."""

    value = raw_value.strip()
    negative = value.startswith("(") and value.endswith(")")
    if negative:
        if "-" in value:
            raise ValueError(f"Invalid currency value: {raw_value!r}")
        value = value[1:-1].strip()
    value = value.replace("$", "").strip()
    if value.startswith("-"):
        if negative:
            raise ValueError(f"Invalid currency value: {raw_value!r}")
        negative = True
        value = value[1:].strip()
    if not re.fullmatch(
        r"(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{1,2})?",
        value,
    ):
        raise ValueError(f"Invalid currency value: {raw_value!r}")

    try:
        amount = Decimal(value.replace(",", ""))
    except InvalidOperation as error:
        raise ValueError(f"Invalid currency value: {raw_value!r}") from error
    cents = amount * 100
    if cents != cents.to_integral_value():
        raise ValueError(f"Currency value has fractions of a cent: {raw_value!r}")
    return -int(cents) if negative else int(cents)


def _parse_date(value: str) -> date:
    normalized = re.sub(r"\s+", " ", value.strip()).replace(",", "")
    formats = (
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%b %d %Y",
        "%B %d %Y",
    )
    for date_format in formats:
        try:
            return datetime.strptime(normalized, date_format).date()
        except ValueError:
            continue
    raise SquareSalesReportParseError(
        f"Unrecognized Square report date: {value!r}."
    )


def _parse_report_period(text: str) -> tuple[date, date]:
    for match in _DATE_RANGE_RE.finditer(text):
        try:
            start = _parse_date(match.group("start"))
            end = _parse_date(match.group("end"))
        except SquareSalesReportParseError:
            continue
        if start >= end:
            raise SquareSalesReportParseError(
                "Report start date must be before report end date."
            )
        return start, end
    raise SquareSalesReportParseError(
        "A report date range such as 'Sep 1, 2026 - Sep 30, 2026' is required."
    )


def _parse_reported_at(text: str) -> datetime | None:
    match = re.search(
        r"(?im)^\s*(?:reported|generated|created)\s+(?:at|on)\s*:?\s*(.+?)\s*$",
        text,
    )
    if match is None:
        return None
    raw_value = match.group(1).strip()
    try:
        return datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
    except ValueError:
        timezone_offsets = {
            "EST": "-05:00",
            "EDT": "-04:00",
            "CST": "-06:00",
            "CDT": "-05:00",
            "MST": "-07:00",
            "MDT": "-06:00",
            "PST": "-08:00",
            "PDT": "-07:00",
        }
        timestamp_parts = re.fullmatch(
            r"(.+?\b(?:AM|PM))\s+([A-Z]{3,4})",
            raw_value,
            re.IGNORECASE,
        )
        if timestamp_parts:
            local_time, timezone_name = timestamp_parts.groups()
            offset = timezone_offsets.get(timezone_name.upper())
            if offset is None:
                raise SquareSalesReportParseError(
                    f"Unrecognized report timezone: {timezone_name!r}."
                )
            for date_format in ("%b %d, %Y %I:%M %p", "%B %d, %Y %I:%M %p"):
                try:
                    return datetime.strptime(
                        f"{local_time}{offset}",
                        f"{date_format}%z",
                    )
                except ValueError:
                    continue
        for date_format in ("%b %d, %Y %I:%M %p", "%B %d, %Y %I:%M %p"):
            try:
                return datetime.strptime(raw_value, date_format)
            except ValueError:
                continue
    raise SquareSalesReportParseError(
        f"Unrecognized report timestamp: {raw_value!r}."
    )


def _section(line: str) -> str | None:
    cleaned = line.strip().rstrip(":").strip().casefold()
    return _SECTION_ALIASES.get(cleaned)


def _metric_for_line(line: str, current_section: str) -> tuple[str, str] | None:
    aliases = _METRIC_ALIASES if current_section == "sales" else _PAYMENT_ALIASES
    for label in sorted(aliases, key=len, reverse=True):
        match = re.match(
            rf"^\s*{re.escape(label)}(?:\s*:\s*|\s{{1,}}|\t+|$)(.*?)\s*$",
            line,
            re.IGNORECASE,
        )
        if match is not None:
            return aliases[label], match.group(1)
    return None


def _is_table_heading(line: str, section: str) -> bool:
    words = set(re.sub(r"[^a-z]+", " ", line.casefold()).split())
    if section == "discounts":
        return (
            "discount" in words
            and "amount" in words
            and bool(words & {"count", "usage"})
        )
    if section == "categories":
        return (
            bool(words & {"category", "categories"})
            and bool(words & {"quantity", "qty", "items", "sold"})
            and bool(words & {"sales", "amount", "net"})
        )
    return (
        bool(words & {"item", "items"})
        and bool(words & {"quantity", "qty", "sold"})
        and bool(words & {"sales", "amount", "net"})
    )


def _split_name_variation(
    label: str,
    allow_aligned_columns: bool,
) -> tuple[str, str | None]:
    if "\t" in label:
        fields = [field.strip() for field in label.split("\t") if field.strip()]
    elif allow_aligned_columns:
        fields = [
            field.strip()
            for field in re.split(r"\s{2,}", label.strip())
            if field.strip()
        ]
    else:
        fields = [label.strip()]
    if len(fields) >= 2:
        return fields[0], " ".join(fields[1:])
    return label.strip(), None


def _parse_table_row(line: str, section: str) -> tuple[str, Decimal, int] | None:
    match = _ROW_RE.fullmatch(line.strip())
    if match is None:
        return None

    label = clean_report_label(match.group("label"))
    if not label:
        return None

    try:
        quantity = Decimal(match.group("quantity"))
        amount = parse_currency_to_cents(match.group("amount"))
    except (InvalidOperation, ValueError) as error:
        raise SquareSalesReportParseError(
            f"Malformed {section} row {line!r}: {error}"
        ) from error
    return label, quantity, amount


def _parse_vertical_row(
    lines: list[tuple[int, str]],
    index: int,
    section: str,
) -> tuple[str, Decimal, int, int] | None:
    if index + 2 >= len(lines):
        return None
    quantity_text = lines[index + 1][1]
    quantity_match = _QUANTITY_RE.fullmatch(quantity_text)
    if quantity_match is None:
        quantity_match = re.fullmatch(r"(?P<quantity>\d+(?:\.\d+)?)", quantity_text)
    amount_text = lines[index + 2][1]
    if quantity_match is None or not _VERTICAL_MONEY_RE.fullmatch(amount_text):
        return None

    label = clean_report_label(lines[index][1])
    if not label:
        raise SquareSalesReportParseError(
            f"Line {lines[index][0]}: {section} name must not be blank."
        )
    try:
        quantity = Decimal(quantity_match.group("quantity"))
        amount = parse_currency_to_cents(amount_text)
    except (InvalidOperation, ValueError) as error:
        raise SquareSalesReportParseError(
            f"Line {lines[index][0]}: malformed {section} row: {error}"
        ) from error
    return label, quantity, amount, index + 3


def _parse_count_amount(
    label: str,
    quantity: Decimal,
    amount: int,
    section: str,
    line_number: int,
) -> tuple[str, Decimal, int]:
    if section == "discounts" and quantity != quantity.to_integral_value():
        raise SquareSalesReportParseError(
            f"Line {line_number}: discount usage count must be an integer."
        )
    return label, quantity, amount


def parse_square_sales_report(raw_text: str) -> ParsedSquareSalesReport:
    """Parse horizontal exports and Square's vertical email-report text.

    Money keeps the sign shown in the source report. Parenthesized or explicitly
    negative values remain negative; unmarked values remain positive.

    An immediate matching quantity/amount child is stored once with its parent
    when indentation or repeated parent/variation structure supplies evidence.
    Equal totals alone are ambiguous and do not justify merging distinct items.
    Both vertical email text and flattened one-line quantity markers work.
    """

    if not isinstance(raw_text, str) or not raw_text.strip():
        raise SquareSalesReportParseError("Square report text must not be empty.")

    normalized_text = raw_text.replace("\u00a0", " ")
    indentation = {
        number: len(line) - len(line.lstrip())
        for number, line in enumerate(normalized_text.splitlines(), start=1)
    }
    lines = [
        (line_number, re.sub(r"[ \t]+$", "", line).strip())
        for line_number, line in enumerate(normalized_text.splitlines(), start=1)
        if line.strip()
    ]
    report_start, report_end = _parse_report_period(normalized_text)
    reported_at = _parse_reported_at(normalized_text)

    report_name = None
    for _, line in lines:
        normalized_line = line.casefold().rstrip(":")
        if normalized_line in {"sales report", "all employees", "all devices"}:
            continue
        if _section(line) is not None or _DATE_RANGE_RE.search(line):
            continue
        if re.match(
            r"(?i)^(?:reported|generated|created)\s+(?:at|on)\b",
            line,
        ):
            continue
        if re.fullmatch(r"(?i)covers", line):
            continue
        if not re.search(r"\d{1,2}:\d{2}\s*(?:AM|PM)", line, re.IGNORECASE):
            report_name = line[:200]
            if report_name:
                break

    metrics: dict[str, int] = {}
    discounts: list[ParsedDiscount] = []
    categories: list[ParsedCategorySales] = []
    items: list[ParsedItemSales] = []
    item_rows: list[ItemRow] = []
    previous_item_indent = None
    previous_item_end = None
    warnings: list[str] = []
    seen_sections: set[str] = set()
    current_section: str | None = None
    pending_metric: str | None = None
    item_variation_column = False
    index = 0

    while index < len(lines):
        line_number, line = lines[index]

        recognized_section = _section(line)
        if recognized_section is not None:
            previous_item_indent = None
            current_section = recognized_section
            if current_section != "metadata":
                seen_sections.add(current_section)
            pending_metric = None
            index += 1
            continue

        if current_section in {"sales", "payments"}:
            metric = _metric_for_line(line, current_section)
            if metric is not None:
                metric_name, raw_amount = metric
                if not raw_amount:
                    pending_metric = metric_name
                    index += 1
                    continue
                try:
                    metrics[metric_name] = parse_currency_to_cents(raw_amount)
                except ValueError as error:
                    raise SquareSalesReportParseError(
                        f"Line {line_number}: {error}"
                    ) from error
                pending_metric = None
                index += 1
                continue
            if pending_metric is not None:
                try:
                    metrics[pending_metric] = parse_currency_to_cents(line)
                except ValueError as error:
                    raise SquareSalesReportParseError(
                        f"Line {line_number}: expected a currency amount for "
                        f"{pending_metric}: {error}"
                    ) from error
                pending_metric = None
                index += 1
                continue

        if current_section not in {"discounts", "categories", "items"}:
            index += 1
            continue

        if _is_table_heading(line, current_section):
            if current_section == "items":
                item_variation_column = bool(
                    re.search(r"\bvariation\b", line, re.IGNORECASE)
                )
            index += 1
            continue
        if re.fullmatch(r"[-=_\s]+", line):
            index += 1
            continue
        if line.casefold().startswith("total"):
            index += 1
            continue

        parsed_row = _parse_table_row(line, current_section)
        next_index = index + 1
        if parsed_row is None:
            vertical_row = _parse_vertical_row(lines, index, current_section)
            if vertical_row is not None:
                label, quantity, amount, next_index = vertical_row
                parsed_row = (label, quantity, amount)

        if parsed_row is None:
            if "$" in line or re.search(r"\d", line):
                raise SquareSalesReportParseError(
                    f"Line {line_number}: malformed {current_section} row: {line!r}."
                )
            if current_section == "items":
                warnings.append(
                    f"Line {line_number}: item or variation row {line!r} "
                    "was not followed by a quantity and amount."
                )
            else:
                warnings.append(
                    f"Line {line_number}: unrecognized {current_section} row "
                    f"was not imported."
                )
            index += 1
            continue

        label, quantity, amount = parsed_row
        if not label:
            raise SquareSalesReportParseError(
                f"Line {line_number}: {current_section} name must not be blank."
            )

        try:
            if current_section == "discounts":
                _, quantity, amount = _parse_count_amount(
                    label, quantity, amount, current_section, line_number
                )
                discounts.append(
                    ParsedDiscount(
                        discount_name=label,
                        usage_count=int(quantity),
                        amount=amount,
                    )
                )
            elif current_section == "categories":
                _, quantity, amount = _parse_count_amount(
                    label, quantity, amount, current_section, line_number
                )
                categories.append(
                    ParsedCategorySales(
                        category_name=label,
                        quantity=quantity,
                        sales_amount=amount,
                    )
                )
            else:
                variation_name = None
                item_name = label
                if next_index == index + 1:
                    item_name, variation_name = _split_name_variation(
                        label,
                        allow_aligned_columns=item_variation_column,
                    )
                item_rows.append(
                    ItemRow(
                        item_name=item_name,
                        variation_name=variation_name,
                        quantity=quantity,
                        sales_amount=amount,
                        child_like=(previous_item_end == index and previous_item_indent is not None and indentation[line_number] > previous_item_indent),
                        follows_previous=previous_item_end == index,
                    )
                )
                previous_item_indent = indentation[line_number]
                previous_item_end = next_index
        except ValueError as error:
            raise SquareSalesReportParseError(
                f"Line {line_number}: invalid {current_section} row: {error}"
            ) from error
        index = next_index

    if pending_metric is not None:
        raise SquareSalesReportParseError(
            f"Missing currency value for required metric {pending_metric}."
        )

    normalized_items, item_warnings = normalize_items(item_rows)
    items = [ParsedItemSales(
        item_name=row.item_name, variation_name=row.variation_name,
        quantity=row.quantity, sales_amount=row.sales_amount,
    ) for row in normalized_items]
    warnings.extend(item_warnings)
    missing_metrics = [name for name in _REQUIRED_METRICS if name not in metrics]
    if missing_metrics:
        raise SquareSalesReportParseError(
            "Missing required report metrics: " + ", ".join(missing_metrics) + "."
        )

    for section, rows in (
        ("discounts", discounts),
        ("categories", categories),
        ("items", items),
    ):
        if section not in seen_sections:
            warnings.append(f"Optional {section} section is missing.")
        elif not rows:
            warnings.append(f"Optional {section} section contains no imported rows.")

    expected_net_sales = (
        metrics["gross_sales_amount"]
        + metrics["service_charge_amount"]
        + metrics["returns_amount"]
        + metrics["discount_comp_amount"]
    )
    if expected_net_sales != metrics["net_sales_amount"]:
        warnings.append(
            "Net sales does not equal gross sales plus the signed service-charge, "
            "return, and discount/comps amounts; source values were preserved."
        )

    net_total_by_signed_fees = (
        metrics["total_collected_amount"] + metrics["fees_amount"]
    )
    net_total_by_fee_deduction = (
        metrics["total_collected_amount"] - metrics["fees_amount"]
    )
    if metrics["net_total_amount"] not in {
        net_total_by_signed_fees,
        net_total_by_fee_deduction,
    }:
        warnings.append(
            "Net total does not match total collected using either signed fees "
            "or a fee deduction; source values were preserved."
        )

    return ParsedSquareSalesReport(
        report_name=report_name,
        report_start=report_start,
        report_end=report_end,
        reported_at=reported_at,
        **metrics,
        discounts=discounts,
        categories=categories,
        items=items,
        warnings=warnings,
    )
