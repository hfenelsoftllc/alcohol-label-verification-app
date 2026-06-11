"""Parsing for the `application_csv` upload (ISSUE 3.2).

Each row corresponds, in order, to one uploaded label image and must supply
every column in `LABEL_FIELD_NAMES`. Any structural problem (missing
columns, wrong row count, an invalid value) is reported as HTTP 422 so the
client can fix the file before resubmitting (FedRAMP SI-10).
"""

from __future__ import annotations

import csv
import io

from fastapi import HTTPException, status
from pydantic import ValidationError

from app.models import LABEL_FIELD_NAMES, ApplicationData


def parse_application_csv(data: bytes, expected_rows: int) -> list[ApplicationData]:
    """Parse `data` into one `ApplicationData` per row, in row order."""
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="application_csv is not valid UTF-8",
        ) from exc

    reader = csv.DictReader(io.StringIO(text))
    fieldnames = reader.fieldnames or []
    missing = [name for name in LABEL_FIELD_NAMES if name not in fieldnames]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"application_csv is missing required column(s): {', '.join(missing)}",
        )

    rows = list(reader)
    if len(rows) != expected_rows:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"application_csv has {len(rows)} row(s) but {expected_rows} "
                "image file(s) were uploaded"
            ),
        )

    application_data: list[ApplicationData] = []
    for index, row in enumerate(rows):
        try:
            application_data.append(ApplicationData(**{name: row.get(name, "") for name in LABEL_FIELD_NAMES}))
        except ValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"application_csv row {index + 1}: {exc.errors()[0]['msg']}",
            ) from exc

    return application_data
