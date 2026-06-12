# Plan of Action and Milestones (POA&M) — Alcohol Label Verification PoC

| | |
|---|---|
| **System Name** | Alcohol Label Verification App (ALVA) — TTB COLA Automation PoC |
| **Document Status** | **FINAL** — Phase 4 (ISSUE 4.6, all tracked items resolved) |
| **Version** | 1.1 |
| **Date** | 2026-06-12 |
| **Issue** | [ISSUE 4.6 — Threat Model Documentation](../../project-management/PROJECT-PLAN.md) ([GitHub #48](https://github.com/hfenelsoftllc/alcohol-label-verification-app/issues/48)) |
| **FedRAMP Control** | **CA-5** (Plan of Action and Milestones) |
| **Related Documents** | [`SSP-final.md`](./SSP-final.md), [`SAST-RESULTS.md`](./SAST-RESULTS.md), [`THREAT-MODEL.md`](./THREAT-MODEL.md) |

> **Scope note.** This POA&M tracks every control gap identified across the ALVA documentation
> package (`SSP-draft.md` → `SSP-final.md`) that remains open as of this document's date, plus
> forward-looking scalability/operational items surfaced by
> [`THREAT-MODEL.md`](./THREAT-MODEL.md) (RA-3, ISSUE 4.6). Per CA-5, each open item below has a
> description, risk level, and remediation plan with a target milestone. Items that were
> previously tracked as "Planned" in `SSP-draft.md` §8 and have since been completed are
> recorded in [§2](#2-resolved-since-ssp-draftmd-closed-items) for traceability, not because
> they remain open.

---

## 1. Open Items

| # | Weakness / Control | NIST Control | Description | Risk Level | Status | Remediation Plan | Scheduled Completion | Responsible Party |
|---|---|---|---|---|---|---|---|---|
| 1 | No global cap on concurrent batch jobs across sessions | N/A — scalability hardening, not a NIST control gap (identified as Top-3 residual risk **T-D2** in [`THREAT-MODEL.md`](./THREAT-MODEL.md) §5) | `BATCH_MAX_WORKERS` (`asyncio.Semaphore`, default 10, `backend/batch/orchestrator.py`) bounds OCR concurrency **within** a single batch job, but no control currently limits the number of concurrent batch jobs **across** sessions, allowing aggregate resource exhaustion under heavy multi-session load. | **Moderate** (residual, per `THREAT-MODEL.md` §4.5) | **Open** | Add a global concurrency limit (process-wide `asyncio.Semaphore` or per-deployment max-concurrent-jobs setting) in `backend/batch/orchestrator.py` / `backend/batch/store.py`, sized to pilot host capacity. | Before pilot/production deployment (post-PoC; candidate for Phase 5). | Development team (this repository). |

---

## 2. Resolved Since `SSP-draft.md` (Closed Items)

The following items were tracked as **Planned** in `SSP-draft.md` §8 and are now
**Implemented**, confirmed in `SSP-final.md` §8:

| Control | Previously | Now | Evidence |
|---|---|---|---|
| **SI-12** (Information Management and Retention) | Planned (Phase 3, ISSUE 3.5) | **Implemented** | `backend/batch/store.py::_reap_expired` reaps jobs idle longer than `SESSION_TTL_HOURS` and emits `session_expired` (audit event), with lazy expiry also enforced in `get_job`. Verified by `backend/tests/test_session_store.py`. |
| **IR-8** (Incident Response Plan) | Planned (Phase 4, ISSUE 4.5) | **Implemented** | [`INCIDENT-RESPONSE-PLAN.md`](./INCIDENT-RESPONSE-PLAN.md) (this issue) defines detection, triage, and response procedures for OCR/processing failures, data exposure events, and availability incidents. |
| **RA-3** (Risk Assessment) | Planned (Phase 4, ISSUE 4.6) | **Implemented** | [`THREAT-MODEL.md`](./THREAT-MODEL.md) (this issue) applies STRIDE across all six required categories (Spoofing/session, Tampering/label image, Repudiation/audit logs, Information Disclosure/OCR data, Denial of Service/batch load, Elevation of Privilege/API auth), rates likelihood/impact/residual risk for 18 threats against an annotated trust-boundary diagram, and calls out the Top 3 residual risks with owners and mitigation timelines. Reviewed and signed off by the project lead (`THREAT-MODEL.md` §7). |

No further action is required for these controls; they are listed here only so a reader
comparing `SSP-draft.md` to `SSP-final.md` can see how each previously-tracked gap was closed.

---

## 3. Summary

- **Total controls tracked** (per [`CONTROL-MATRIX.xlsx`](./CONTROL-MATRIX.xlsx)): 33
- **Implemented**: 33
- **Planned (open, this POA&M)**: 0
- **Not Applicable / Inherited**: 0 distinct rows beyond those noted as Inherited within
  `SSP-final.md` §8 (AC-17 is Implemented/Inherited — network perimeter and TLS termination are
  inherited from the hosting GSS, but the application-level remote-access control is
  implemented)

All 33 tracked NIST controls are now **Implemented**. The only remaining item in this POA&M
is **T-D2** (§1) — a forward-looking scalability item for the pilot/production phase,
surfaced by [`THREAT-MODEL.md`](./THREAT-MODEL.md) and not a gap in any currently-assessed
control.
