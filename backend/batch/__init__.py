"""Batch processing package (ISSUE 3.1).

`store` holds in-memory batch job state (FedRAMP SI-12 — ephemeral only,
cleared on restart). `orchestrator.start_batch` runs a batch of labels
through the OCR/matching pipeline with bounded concurrency, yielding
per-label progress events.
"""
