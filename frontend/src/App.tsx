import { Routes, Route } from "react-router-dom";
import { Layout } from "./components/Layout";
import { Analytics } from "./pages/Analytics";
import { Assets } from "./pages/Assets";
import { Backtest } from "./pages/Backtest";
import { Dashboard } from "./pages/Dashboard";
import { EnvConfig } from "./pages/EnvConfig";
import { Market } from "./pages/Market";
import { News } from "./pages/News";
import { Rebalance } from "./pages/Rebalance";
import { Settings } from "./pages/Settings";
import { Transactions } from "./pages/Transactions";

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/assets" element={<Assets />} />
        <Route path="/transactions" element={<Transactions />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/backtest" element={<Backtest />} />
        <Route path="/rebalance" element={<Rebalance />} />
        <Route path="/market" element={<Market />} />
        <Route path="/news" element={<News />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/env-config" element={<EnvConfig />} />
      </Routes>
    </Layout>
  );
}

export default App;
