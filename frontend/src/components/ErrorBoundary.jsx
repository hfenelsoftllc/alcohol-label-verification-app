import { Component } from 'react';

// Class component — React error boundaries must be class-based.
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, info) {
    // Surfaced to the console for now; ISSUE 4.4 wires structured reporting.
    console.error('Unhandled UI error:', error, info);
  }

  handleReload = () => {
    this.setState({ hasError: false });
    window.location.assign('/');
  };

  render() {
    if (this.state.hasError) {
      return (
        <main
          className="mx-auto mt-16 max-w-lg rounded-2xl border border-slate-200/70 bg-white p-10 text-center shadow-card"
          role="alert"
        >
          <h1 className="font-display text-2xl font-semibold text-ink">Something went wrong</h1>
          <p className="mt-3 text-muted">
            Your session is still active. You can return to the start and try again.
          </p>
          <button
            type="button"
            onClick={this.handleReload}
            className="mt-6 inline-flex items-center rounded-lg bg-treasury-700 px-5 py-2.5 font-semibold text-white shadow-sm transition-colors hover:bg-treasury-800"
          >
            Return to start
          </button>
        </main>
      );
    }
    return this.props.children;
  }
}
