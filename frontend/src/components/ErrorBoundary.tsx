import { Component, type ErrorInfo, type ReactNode } from "react";

/** Catches rendering errors in a page so one bad response cannot blank the whole app (and E2E tests see role="alert"). */
export class ErrorBoundary extends Component<{ children: ReactNode; resetKey?: string }, { error: Error | null }> {
  state: { error: Error | null } = { error: null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  componentDidUpdate(prev: { resetKey?: string }) {
    if (prev.resetKey !== this.props.resetKey && this.state.error) this.setState({ error: null });
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("page render error", error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <div role="alert" className="rounded-xl border border-alert/30 bg-alert/10 p-4 text-sm">
          <h1 className="font-display text-xl">This page failed to render</h1>
          <p className="mt-1 font-mono text-xs">{this.state.error.message}</p>
        </div>
      );
    }
    return this.props.children;
  }
}
