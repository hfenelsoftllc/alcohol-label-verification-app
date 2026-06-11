# Tests — Integration & Load

Cross-cutting tests that span the stack. Component-level unit tests live next to
the code they cover (`backend/tests/`, `frontend/src/**/*.test.tsx`).

## Layout

```
tests/
├── integration/   # End-to-end API + UI flows (planned)
└── load/          # 300-label batch performance test (ISSUE 4.2)
```

`tests/load/` is a manual script (not part of the CI gate) that drives the
FastAPI app in-process for a 300-label batch against both OCR paths. See
[`tests/load/README.md`](load/README.md) for how to run it and
[`docs/LOAD-TEST-RESULTS.md`](../docs/LOAD-TEST-RESULTS.md) for the documented
results (FedRAMP AU-14/CP-10 evidence).
