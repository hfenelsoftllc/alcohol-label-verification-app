import { useEffect, useState } from 'react';

import { getHealth } from '../api/client.js';

// Demonstrates the backend connection + a loading state for an async op.
export default function BackendStatus() {
  const [state, setState] = useState({ status: 'loading' });

  useEffect(() => {
    let active = true;
    getHealth()
      .then((data) => active && setState({ status: 'ok', version: data.version }))
      .catch(() => active && setState({ status: 'error' }));
    return () => {
      active = false;
    };
  }, []);

  const map = {
    loading: { dot: 'bg-muted', text: 'Checking backend…' },
    ok: { dot: 'bg-success', text: `Backend online (v${state.version})` },
    error: { dot: 'bg-danger', text: 'Backend unreachable' },
  };
  const { dot, text } = map[state.status];

  return (
    <span className="inline-flex items-center gap-2 text-sm text-muted" aria-live="polite">
      <span className={`h-2.5 w-2.5 rounded-full ${dot}`} aria-hidden="true" />
      {text}
    </span>
  );
}
