# Frontend — React + Vite SPA

Single-page React 18 application built with Vite and Tailwind CSS. Provides the
reviewer workflow: single-label upload, side-by-side results review, and batch
upload with live progress. Accessibility (WCAG 2.1 AA) is a first-class
requirement — see [ADR-001](../docs/architecture/ADR-001-System-Architecture.md).

## Planned layout

```
frontend/
├── src/
│   ├── pages/        # Upload (/), Review (/results/:sessionId), Batch (/batch)
│   ├── components/   # Shared UI components
│   └── api/          # Backend client (uses VITE_API_URL)
├── public/
└── index.html
```

## Local development

```bash
cd frontend
npm install
npm run dev
```

The dev server runs at `http://localhost:3000` and talks to the backend via the
`VITE_API_URL` environment variable.

> Scaffolding lands in ISSUE 1.5 (React Frontend Shell).
