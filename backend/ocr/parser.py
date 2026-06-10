"""Parse raw OCR text into the structured label fields (ISSUE 2.3).

Tesseract output is noisy: spurious line breaks split words and phrases, and
adjacent characters merge ("byVol."). `parse_raw_text` is heuristic and
best-effort by design (FedRAMP SI-10) — it never raises, and a field that
can't be confidently located is simply left as ``None`` for the matching
engine to flag, rather than guessed at or rejected outright.
"""

from __future__ import annotations

import re

from app.models import LABEL_FIELD_NAMES

_GOV_WARNING_RE = re.compile(r"government\s*warning", re.IGNORECASE)

_ABV_RE = re.compile(
    r"\b\d{1,2}(?:\.\d+)?\s*%\s*alc(?:\.|ohol)?(?:\s*by\s*vol(?:ume)?\.?)?", re.IGNORECASE
)
_PROOF_RE = re.compile(r"\b\d{1,3}(?:\.\d+)?\s*proof\b", re.IGNORECASE)

# Amount + unit, e.g. "750mL", "750 ml", "1.75 L", "12 FL. OZ".
_NET_RE = re.compile(r"\b(\d+(?:\.\d+)?)\s*(m\s*l|c\s*l|l|fl\.?\s*oz)\b", re.IGNORECASE)
_NET_UNIT_NAMES = {
    "ml": "mL",
    "cl": "cL",
    "l": "L",
    "floz": "fl oz",
}

# "Product of France", "Made in Italy", "Imported from Scotland".
_ORIGIN_RE = re.compile(r"\b(?:product of|made in|imported from)\s+([A-Za-z][A-Za-z .'-]*)", re.IGNORECASE)

# "Bottled by", "Distilled and Bottled by", "Imported by", etc.
_PRODUCER_RE = re.compile(
    r"\b(?:bottled|produced|distilled|brewed|vinted|imported)"
    r"(?:\s+and\s+(?:bottled|imported))?\s+by\b",
    re.IGNORECASE,
)

# Class/type keywords, longest/most-specific phrases first so they win over a
# shorter keyword they contain (e.g. "india pale ale" before "ale").
_CLASS_TYPE_KEYWORDS = (
    "cabernet sauvignon", "sauvignon blanc", "pinot noir", "pinot grigio", "pinot gris",
    "sparkling wine", "india pale ale", "blended whiskey", "single malt scotch whisky",
    "straight bourbon whiskey",
    "vodka", "whiskey", "whisky", "bourbon", "scotch", "gin", "rum",
    "tequila", "brandy", "cognac", "liqueur", "mezcal",
    "beer", "ale", "lager", "stout", "porter", "ipa", "cider", "mead", "sake",
    "wine", "champagne", "chardonnay", "merlot", "zinfandel", "riesling",
    "malbec", "syrah", "shiraz", "rose", "rosé",
)
_CLASS_TYPE_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(keyword) for keyword in _CLASS_TYPE_KEYWORDS) + r")\b",
    re.IGNORECASE,
)


def parse_raw_text(text: str) -> dict[str, str | None]:
    """Best-effort mapping of OCR text to the seven label fields.

    Returns a dict keyed by every name in ``LABEL_FIELD_NAMES``; unresolved
    fields are ``None``.
    """
    fields: dict[str, str | None] = {name: None for name in LABEL_FIELD_NAMES}

    lines = [" ".join(line.split()) for line in text.splitlines()]
    lines = [line for line in lines if line]
    if not lines:
        return fields

    fields["brand"] = lines[0]
    fields["class_type"] = _extract_class_type(lines)
    fields["abv"] = _extract_abv(text)
    fields["net_contents"] = _extract_net_contents(text)
    fields["name_address"] = _extract_name_address(lines)
    fields["country_of_origin"] = _extract_country_of_origin(text)
    fields["government_warning"] = _extract_government_warning(text)

    return fields


def _extract_class_type(lines: list[str]) -> str | None:
    """The line containing a recognized class/type keyword (e.g. "Vodka")."""
    for line in lines:
        if _CLASS_TYPE_RE.search(line):
            return line
    return None


def _extract_abv(text: str) -> str | None:
    """The "XX% Alc. by Vol." or "XX Proof" substring, exactly as printed."""
    match = _ABV_RE.search(text) or _PROOF_RE.search(text)
    return " ".join(match.group(0).split()) if match else None


def _extract_net_contents(text: str) -> str | None:
    """The amount + unit, with the unit normalized (e.g. "750ml" -> "750 mL")."""
    match = _NET_RE.search(text)
    if not match:
        return None
    amount, unit = match.groups()
    unit_key = re.sub(r"[\s.]", "", unit).lower()
    return f"{amount} {_NET_UNIT_NAMES.get(unit_key, unit)}"


def _extract_name_address(lines: list[str]) -> str | None:
    """The bottler/producer line plus following address lines (TTB convention).

    Starts at the first "Bottled by" / "Imported by" / etc. line and gathers
    subsequent lines until one looks like a different field (origin, ABV, net
    contents, or the Government Warning).
    """
    for i, line in enumerate(lines):
        if not _PRODUCER_RE.search(line):
            continue
        block = [line]
        for next_line in lines[i + 1 :]:
            if (
                next_line.upper().startswith("GOVERNMENT")
                or _ORIGIN_RE.search(next_line)
                or _ABV_RE.search(next_line)
                or _PROOF_RE.search(next_line)
                or _NET_RE.search(next_line)
            ):
                break
            block.append(next_line)
        return ", ".join(block)
    return None


def _extract_country_of_origin(text: str) -> str | None:
    """The country name from a "Product of X" / "Made in X" phrase."""
    match = _ORIGIN_RE.search(text)
    return match.group(1).strip().rstrip(".,") if match else None


def _extract_government_warning(text: str) -> str | None:
    """The full Government Warning block, verbatim from "GOVERNMENT WARNING" onward.

    Internal whitespace (including spurious OCR line breaks) is collapsed to
    single spaces so the legally-mandated wording reads as one block.
    """
    match = _GOV_WARNING_RE.search(text)
    return " ".join(text[match.start() :].split()) if match else None
