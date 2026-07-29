import { Component, ErrorInfo, ReactNode } from "react";
import { Routes, Route } from "react-router-dom";
import { Layout } from "./components/Layout";
import { Analytics } from "./pages/Analytics";
import { Assets } from "./pages/Assets";
// import { Backtest } from "./pages/Backtest";
import { Compare } from "./pages/Compare";
import { Dashboard } from "./pages/Dashboard";
import { EnvConfig } from "./pages/EnvConfig";
import { Market } from "./pages/Market";
import { News } from "./pages/News";
import { Rebalance } from "./pages/Rebalance";
import { Settings } from "./pages/Settings";
import { Transactions } from "./pages/Transactions";

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error("ErrorBoundary caught an error:", error, errorInfo);
  }

  handleReload = (): void => {
    window.location.reload();
  };

  render(): ReactNode {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-gray-50 p-6 text-center dark:bg-gray-900">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            Đã xảy ra lỗi
          </h1>
          <p className="max-w-md text-gray-600 dark:text-gray-400">
            Ứng dụng gặp sự cố không mong muốn. Vui lòng tải lại trang để thử
            lại.
          </p>
          {this.state.error && (
            <pre className="max-w-lg overflow-auto rounded bg-gray-100 p-3 text-xs text-gray-700 dark:bg-gray-800 dark:text-gray-300">
              {this.state.error.message}
            </pre>
          )}
          <button
            onClick={this.handleReload}
            className="rounded-lg bg-blue-600 px-5 py-2.5 font-medium text-white transition-colors hover:bg-blue-700"
          >
            Tải lại trang
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

function App() {
  return (
    <ErrorBoundary>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/assets" element={<Assets />} />
          <Route path="/transactions" element={<Transactions />} />
          <Route path="/analytics" element={<Analytics />} />
          {/* <Route path="/backtest" element={<Backtest />} /> */}
          <Route path="/rebalance" element={<Rebalance />} />
          <Route path="/market" element={<Market />} />
          <Route path="/compare" element={<Compare />} />
          <Route path="/news" element={<News />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/env-config" element={<EnvConfig />} />
        </Routes>
      </Layout>
    </ErrorBoundary>
  );
}

export default App;
