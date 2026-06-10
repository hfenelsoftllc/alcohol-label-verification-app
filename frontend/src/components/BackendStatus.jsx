import { useEffect, useState } from 'react';

import { getHealth } from '../api/client.js';

// Live backend indicator on the dark header. Demonstrates an async op + loading
// state. Status is conveyed by dot color *and* text (never color alone).
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
    loading: { dot: 'bg-gold-300 animate-pulse', text: 'Checking backend…' },
    ok: { dot: 'bg-emerald-400', text: `Online · v${state.version}` },
    error: { dot: 'bg-red-400', text: 'Backend unreachable' },
  };
  const { dot, text } = map[state.status];

  return (
    <span
      className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-3 py-1 text-xs font-medium text-treasury-100"
      aria-live="polite"
    >
      <span className={`h-2 w-2 rounded-full ${dot}`} aria-hidden="true" />
      {text}
    </span>
  );
}
