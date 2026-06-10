# Backend — FastAPI Service

Python FastAPI application: OCR/vision adapter, matching engine, batch
orchestrator, and the in-memory session store. No database; all processing is
ephemeral per the architecture decision in
[ADR-001](../docs/architecture/ADR-001-System-Architecture.md).

## Planned layout

```
backend/
├── app/            # FastAPI app, routers, Pydantic models
├── ocr/            # Vision adapter (Claude Vision + Tesseract fallback), parser, quality
├── matching/       # Fuzzy engine + Government Warning exact validator
├── batch/          # Async batch orchestrator + in-memory job store
├── store/          # Session store + CSV/XLSX export
└── tests/          # Backend unit tests (pytest)
```

## Local development

```bash
cd backend
python -m venv .venv && . .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

OpenAPI docs are served at `http://localhost:8000/docs`.

> Scaffolding lands in ISSUE 1.4 (FastAPI Backend Skeleton).
