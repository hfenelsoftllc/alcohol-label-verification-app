import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';

import ErrorBoundary from '../components/ErrorBoundary.jsx';

afterEach(cleanup);

function Thrower() {
  throw new Error('boom');
}

// ISSUE 4.4 AC5 — a render error in any page is caught by the global
// boundary, which shows a plain-language message (not the raw error) and a
// way to recover without losing the session.
describe('ErrorBoundary', () => {
  it('shows a plain-language fallback with a retry control instead of crashing', () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});

    render(
      <ErrorBoundary>
        <Thrower />
      </ErrorBoundary>,
    );

    expect(screen.getByRole('alert')).toBeTruthy();
    screen.getByRole('heading', { name: 'Something went wrong' });
    screen.getByText(/your session is still active/i);
    expect(screen.queryByText(/boom/i)).toBeNull();

    console.error.mockRestore();
  });

  it('returns to the start page when the retry button is clicked', () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});

    // jsdom's window.location.assign is a non-configurable Location.prototype
    // method, so it can't be spied on directly — replace the whole object.
    const originalLocation = window.location;
    const assign = vi.fn();
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: { ...originalLocation, assign },
    });

    render(
      <ErrorBoundary>
        <Thrower />
      </ErrorBoundary>,
    );

    fireEvent.click(screen.getByRole('button', { name: 'Return to start' }));

    expect(assign).toHaveBeenCalledWith('/');

    Object.defineProperty(window, 'location', { configurable: true, value: originalLocation });
    console.error.mockRestore();
  });

  it('renders children normally when nothing has thrown', () => {
    render(
      <ErrorBoundary>
        <p>All good</p>
      </ErrorBoundary>,
    );

    screen.getByText('All good');
  });
});
