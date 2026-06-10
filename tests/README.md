# Tests — Integration & Load

Cross-cutting tests that span the stack. Component-level unit tests live next to
the code they cover (`backend/tests/`, `frontend/src/**/*.test.tsx`).

## Planned layout

```
tests/
├── integration/   # End-to-end API + UI flows
└── load/          # Locust / pytest-benchmark batch performance (300 labels, ≤5s avg)
```

> Load testing is formalized in ISSUE 4.2 (Load Testing & Performance Validation).
