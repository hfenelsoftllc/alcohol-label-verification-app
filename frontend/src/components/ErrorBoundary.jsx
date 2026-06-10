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
        <main className="mx-auto max-w-lg p-8 text-center" role="alert">
          <h1 className="text-2xl font-bold text-ink">Something went wrong</h1>
          <p className="mt-3 text-muted">
            Your session is still active. You can return to the start and try again.
          </p>
          <button
            type="button"
            onClick={this.handleReload}
            className="mt-6 rounded-md bg-brand-700 px-5 py-2.5 font-semibold text-white hover:bg-brand-800"
          >
            Return to start
          </button>
        </main>
      );
    }
    return this.props.children;
  }
}
