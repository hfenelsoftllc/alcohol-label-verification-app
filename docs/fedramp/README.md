# FedRAMP Package

Documentation package targeting the **FedRAMP Moderate** baseline (NIST 800-53r5),
prepared for hand-off to the TTB ISSO. Full ATO is out of scope for the PoC; the
deliverable is a complete, assessable package.

## Artifacts (built across phases)

| File | Phase | Issue | Status |
|------|-------|-------|--------|
| `SSP-draft.md` → `SSP-final.md` | 1 → 4 | 1.6, 4.5 | **Final** |
| `DATA-FLOW.md` → `DATA-FLOW-final.md` | 1 → 4 | 1.7, 4.5 | **Final** |
| `SAST-RESULTS.md` | 2, 4 | 2.6, 4.5 | **Final** |
| `SESSION-MANAGEMENT.md` | 3 | 3.7 | Complete |
| `PREPROCESSING-AB-TEST.md` | 4 | 4.1 | Complete |
| `LOAD-TEST-RESULTS.md` (in `/docs`) | 4 | 4.2 | Complete |
| `ACCESSIBILITY-REPORT.md` (in `/docs`) | 4 | 4.3 | Complete |
| `POAM.md` | 4 | 4.5, 4.6 | Complete |
| `CONTROL-MATRIX.xlsx` | 4 | 4.5, 4.6 | Complete |
| `INCIDENT-RESPONSE-PLAN.md` | 4 | 4.5 | Complete |
| `SYSTEM-BOUNDARY.png` | 4 | 4.5 | Complete |
| `PEER-REVIEW.md` | 4 | 4.5 | Complete |
| `THREAT-MODEL.md` | 4 | 4.6 | Complete |

This package (everything marked **Final**/Complete above) is ready for hand-off to the TTB
ISSO per [`SSP-final.md`](./SSP-final.md) §11. All 33 tracked NIST controls are
**Implemented** — `THREAT-MODEL.md` (RA-3, ISSUE 4.6) closed the package's last open item.
[`POAM.md`](./POAM.md) retains one forward-looking scalability item (T-D2, global batch-job
concurrency cap) for the pilot/production phase.

System categorization: **Moderate** (C=M, I=M, A=M) per FIPS 199.
