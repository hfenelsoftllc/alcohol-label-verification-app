"""OCR / vision extraction package.

`adapter.extract_fields` is the single entry point: it tries the Claude Vision
API and falls back to local Tesseract when the API is unreachable.
"""
