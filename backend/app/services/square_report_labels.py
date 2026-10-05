import re


def clean_report_label(label: str) -> str:
    """Remove Square's trailing quantity marker left by older one-line imports."""
    return re.sub(r"\s+\u00d7$", "", label.strip()).strip()
