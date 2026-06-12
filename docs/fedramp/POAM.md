# Plan of Action and Milestones (POA&M) — Alcohol Label Verification PoC

| | |
|---|---|
| **System Name** | Alcohol Label Verification App (ALVA) — TTB COLA Automation PoC |
| **Document Status** | **FINAL** — Phase 4 (ISSUE 4.5, complete FedRAMP documentation package) |
| **Version** | 1.0 |
| **Date** | 2026-06-11 |
| **Issue** | [ISSUE 4.5 — Complete FedRAMP Documentation Package](../../project-management/PROJECT-PLAN.md) |
| **FedRAMP Control** | **CA-5** (Plan of Action and Milestones) |
| **Related Documents** | [`SSP-final.md`](./SSP-final.md), [`SAST-RESULTS.md`](./SAST-RESULTS.md) |

> **Scope note.** This POA&M tracks every control gap identified across the ALVA documentation
> package (`SSP-draft.md` → `SSP-final.md`) that remains open as of this document's date. Per
> CA-5, each open item below has a description, risk level, and remediation plan with a target
> milestone. Items that were previously tracked as "Planned" in `SSP-draft.md` §8 and have since
> been completed are recorded in [§2](#2-resolved-since-ssp-draftmd-closed-items) for
> traceability, not because they remain open.

---

## 1. Open Items

| # | Weakness / Control | NIST Control | Description | Risk Level | Status | Remediation Plan | Scheduled Completion | Responsible Party |
|---|---|---|---|---|---|---|---|---|
| 1 | Threat model / attack surface analysis not yet documented | **RA-3** (Risk Assessment) | `SSP-final.md` §8 and `CONTROL-MATRIX.xlsx` mark RA-3 as the sole **Planned** control. A dedicated `THREAT-MODEL.md` covering STRIDE-style threat enumeration, attack surface analysis, and data-flow-derived risk ratings has not yet been produced — `DATA-FLOW-final.md` and `ADR-001` provide the inputs but not the formal analysis. | **Low** — the system's attack surface is small (single external dependency, no persistent storage, in-memory ephemeral processing per `DATA-FLOW-final.md` §7) and the relevant controls (AC-3, IA-2, SC-23, SI-10, SI-16, SI-17) are already implemented and tested. The gap is in *formal documentation* of the risk assessment, not in unmitigated technical risk. | **Open** | Complete **ISSUE 4.6 — Threat Model Documentation** ([GitHub #48](https://github.com/hfenelsoftllc/alcohol-label-verification-app/issues/48)), producing `docs/fedramp/THREAT-MODEL.md` using `DATA-FLOW-final.md`'s trust boundaries (TB-0..TB-3) and `ADR-001`'s architecture as inputs. | Next issue in Phase 4 sequence (ISSUE 4.6), prior to ATO submission. | Development team (this repository); reviewed by TTB ISSO at hand-off. |

---

## 2. Resolved Since `SSP-draft.md` (Closed Items)

The following items were tracked as **Planned** in `SSP-draft.md` §8 and are now
**Implemented**, confirmed in `SSP-final.md` §8:

| Control | Previously | Now | Evidence |
|---|---|---|---|
| **SI-12** (Information Management and Retention) | Planned (Phase 3, ISSUE 3.5) | **Implemented** | `backend/batch/store.py::_reap_expired` reaps jobs idle longer than `SESSION_TTL_HOURS` and emits `session_expired` (audit event), with lazy expiry also enforced in `get_job`. Verified by `backend/tests/test_session_store.py`. |
| **IR-8** (Incident Response Plan) | Planned (Phase 4, ISSUE 4.5) | **Implemented** | [`INCIDENT-RESPONSE-PLAN.md`](./INCIDENT-RESPONSE-PLAN.md) (this issue) defines detection, triage, and response procedures for OCR/processing failures, data exposure events, and availability incidents. |

No further action is required for these controls; they are listed here only so a reader
comparing `SSP-draft.md` to `SSP-final.md` can see how each previously-tracked gap was closed.

---

## 3. Summary

- **Total controls tracked** (per [`CONTROL-MATRIX.xlsx`](./CONTROL-MATRIX.xlsx)): 33
- **Implemented**: 32
- **Planned (open, this POA&M)**: 1 (RA-3)
- **Not Applicable / Inherited**: 0 distinct rows beyond those noted as Inherited within
  `SSP-final.md` §8 (AC-17 is Implemented/Inherited — network perimeter and TLS termination are
  inherited from the hosting GSS, but the application-level remote-access control is
  implemented)

This POA&M will be updated if `THREAT-MODEL.md` (ISSUE 4.6) surfaces additional findings that
require their own remediation items.
