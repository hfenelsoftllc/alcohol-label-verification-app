"""Tests for the batch submission and /jobs/* endpoints."""

from tests.conftest import PNG_1X1


def _submit_batch(client, n_images=3):
    files = [("images", (f"label_{i}.png", PNG_1X1, "image/png")) for i in range(n_images)]
    files.append(("application_csv", ("data.csv", b"brand,abv\nX,40", "text/csv")))
    return client.post("/verify/batch", files=files)


def test_batch_returns_job_id(client):
    resp = _submit_batch(client, n_images=3)
    assert resp.status_code == 202
    body = resp.json()
    assert body["total"] == 3
    assert body["state"] == "PENDING"
    assert body["job_id"]


def test_batch_rejects_non_image_415(client):
    files = [("images", ("notes.txt", b"hello", "text/plain"))]
    files.append(("application_csv", ("data.csv", b"brand\nX", "text/csv")))
    resp = client.post("/verify/batch", files=files)
    assert resp.status_code == 415


def test_job_status_results_export_roundtrip(client):
    job_id = _submit_batch(client).json()["job_id"]

    status_resp = client.get(f"/jobs/{job_id}/status")
    assert status_resp.status_code == 200
    assert status_resp.json()["total"] == 3

    results_resp = client.get(f"/jobs/{job_id}/results")
    assert results_resp.status_code == 200
    assert results_resp.json()["summary"]["match"] == 0  # nothing processed yet

    export_resp = client.get(f"/jobs/{job_id}/export")
    assert export_resp.status_code == 200
    assert export_resp.headers["content-type"].startswith("text/csv")
    assert "filename" in export_resp.text.splitlines()[0]


def test_unknown_job_404(client):
    assert client.get("/jobs/does-not-exist/status").status_code == 404
    assert client.get("/jobs/does-not-exist/results").status_code == 404
    assert client.get("/jobs/does-not-exist/export").status_code == 404


def test_openapi_docs_available(client):
    assert client.get("/openapi.json").status_code == 200
