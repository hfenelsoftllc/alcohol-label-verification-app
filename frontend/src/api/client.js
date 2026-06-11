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

async function request(path, options = {}) {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });
  if (!res.ok) {
    let message = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      message = body.message || body.error || message;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(message, res.status);
  }
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

export { API_URL };
