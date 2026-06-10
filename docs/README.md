# Docs

Project documentation: architecture decisions, the FedRAMP package, and
operational guides.

## Layout

```
docs/
├── architecture/   # ADRs (ADR-001 System Architecture, ...)
├── fedramp/        # FedRAMP Moderate package: SSP, data flow, threat model, SAST results
├── DEPLOYMENT-GUIDE.md     # (Phase 4) install & air-gapped operation
├── LOAD-TEST-RESULTS.md    # (Phase 4) performance evidence
└── ACCESSIBILITY-REPORT.md # (Phase 4) WCAG AA audit results
```

The FedRAMP artifacts are produced across all four phases — the SSP draft and
data-flow docs begin in Phase 1 (ISSUE 1.6, 1.7) so assessment can start while
the system is still being built.
