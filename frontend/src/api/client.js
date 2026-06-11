// Backend client. Base URL comes from VITE_API_URL (baked at build time);
// nginx reverse-proxies the default `/api` to the FastAPI service.
const API_URL = import.meta.env.VITE_API_URL || '/api';

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function throwIfError(res) {
  if (res.ok) return;
  let message = `Request failed (${res.status})`;
  try {
    const body = await res.json();
    message = body.message || body.error || message;
  } catch {
    /* non-JSON error body */
  }
  throw new ApiError(message, res.status);
}

async function request(path, options = {}) {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });
  await throwIfError(res);
  return res.json();
}

export function getHealth() {
  return request('/health');
}

export function verify(image, applicationData) {
  return request('/verify', {
    method: 'POST',
    body: JSON.stringify({ image, application_data: applicationData }),
  });
}

// URL for the batch progress stream (ISSUE 3.2). Returned as a string,
// rather than fetched here, since EventSource opens its own connection.
export function jobStreamUrl(jobId) {
  return `${API_URL}/jobs/${encodeURIComponent(jobId)}/stream`;
}

// URL for the "Download Full Report" button (ISSUE 3.4) — a plain link
// download, since the response is a file rather than JSON.
export function jobExportUrl(jobId) {
  return `${API_URL}/jobs/${encodeURIComponent(jobId)}/export`;
}

// Submits a batch (ISSUE 3.4): `images` are extracted from the reviewer's
// ZIP, `applicationCsv` is the matching application_csv File. Sent as
// multipart/form-data — the browser sets the Content-Type boundary, so this
// bypasses `request()`'s JSON default.
export async function submitBatch(images, applicationCsv) {
  const formData = new FormData();
  for (const image of images) {
    formData.append('images', image, image.name);
  }
  formData.append('application_csv', applicationCsv, applicationCsv.name);

  const res = await fetch(`${API_URL}/verify/batch`, { method: 'POST', body: formData });
  await throwIfError(res);
  return res.json();
}

export { API_URL };
