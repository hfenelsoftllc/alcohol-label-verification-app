import './style.css';

// nginx reverse-proxies `/api` to the backend; VITE_API_URL can override it.
const API_BASE = import.meta.env.VITE_API_URL || '/api';

const app = document.getElementById('app');
app.innerHTML = `
  <main class="card" role="main">
    <h1>Alcohol Label Verification</h1>
    <p class="subtitle">TTB COLA Automation &mdash; Proof of Concept</p>
    <p class="status" id="status" aria-live="polite">Checking backend&hellip;</p>
    <p class="note">
      Placeholder shell (ISSUE 1.3). The accessible React reviewer UI lands in ISSUE 1.5.
    </p>
  </main>
`;

const statusEl = document.getElementById('status');

fetch(`${API_BASE}/health`)
  .then((r) => {
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json();
  })
  .then((d) => {
    statusEl.textContent = `Backend: ${d.status} (v${d.version})`;
    statusEl.classList.add('ok');
  })
  .catch(() => {
    statusEl.textContent = 'Backend: unreachable';
    statusEl.classList.add('err');
  });
