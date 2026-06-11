import { expect, vi } from 'vitest';
import { toHaveNoViolations } from 'jest-axe';

expect.extend(toHaveNoViolations);

// BackendStatus calls getHealth() on mount; stub fetch so component tests
// never make real network calls and settle into the "error" state.
vi.stubGlobal(
  'fetch',
  vi.fn(() => Promise.reject(new Error('network disabled in tests'))),
);
