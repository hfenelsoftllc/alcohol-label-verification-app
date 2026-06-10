"""Parse raw OCR text into the structured label fields.

Phase 2 stub: enough heuristics to give the Tesseract fallback a useful result.
The full field parser — brand/class/address extraction, unit normalization, the
verbatim Government Warning block — is ISSUE 2.3, which expands this module.
"""

from __future__ import annotations

import re

from app.models import LABEL_FIELD_NAMES

_ABV_RE = re.compile(
    r"\b\d{1,2}(?:\.\d+)?\s*%\s*alc(?:\.|ohol)?(?:\s*by\s*vol(?:ume)?\.?)?", re.IGNORECASE
)
_PROOF_RE = re.compile(r"\b\d{1,3}(?:\.\d+)?\s*proof\b", re.IGNORECASE)
_NET_RE = re.compile(r"\b\d+(?:\.\d+)?\s*(?:ml|l|fl\.?\s*oz)\b", re.IGNORECASE)
_GOV_WARNING = "GOVERNMENT WARNING"


def parse_raw_text(text: str) -> dict[str, str | None]:
    """Best-effort mapping of OCR text to the seven label fields.

    Returns a dict keyed by every name in ``LABEL_FIELD_NAMES``; unresolved
    fields are ``None``.
    """
    fields: dict[str, str | None] = {name: None for name in LABEL_FIELD_NAMES}

    abv = _ABV_RE.search(text) or _PROOF_RE.search(text)
    if abv:
        fields["abv"] = abv.group(0).strip()

    net = _NET_RE.search(text)
    if net:
        fields["net_contents"] = net.group(0).strip()

    # Government Warning is a verbatim block; capture from the prefix onward.
    idx = text.upper().find(_GOV_WARNING)
    if idx != -1:
        fields["government_warning"] = text[idx:].strip()

    return fields
