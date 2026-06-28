import { Link, useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import {
  BarChart3,
  Coins,
  FlaskConical,
  LineChart,
  Receipt,
  Scale,
  Settings,
  TrendingUp,
  Wallet,
} from "lucide-react";
import { labels } from "../i18n/vi";

const nav = [
  { path: "/", label: labels.nav.dashboard, icon: BarChart3 },
  { path: "/assets", label: labels.nav.assets, icon: Coins },
  { path: "/transactions", label: labels.nav.transactions, icon: Receipt },
  { path: "/analytics", label: labels.nav.analytics, icon: TrendingUp },
  { path: "/backtest", label: labels.nav.backtest, icon: FlaskConical },
  { path: "/rebalance", label: labels.nav.rebalance, icon: Scale },
  { path: "/market", label: labels.nav.market, icon: LineChart },
  { path: "/settings", label: labels.nav.settings, icon: Settings },
];

export function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation();

  return (
    <div className="min-h-screen flex flex-col md:flex-row font-body">
      <aside className="w-full md:w-64 md:min-h-screen flex-shrink-0 border-b md:border-b-0 md:border-r border-fintech-border bg-surface-elevated/80 backdrop-blur-xl p-4">
        <div className="flex items-center gap-3 mb-8 px-2">
          <div className="relative flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-br from-accent-blue to-accent-violet shadow-lg shadow-accent-blue/30">
            <Wallet className="w-5 h-5 text-white" />
            <div className="absolute inset-0 rounded-xl bg-accent-cyan/20 blur-md" />
          </div>
          <div>
            <h1 className="font-display font-bold text-lg text-slate-900 tracking-tight">
              {labels.app.shortTitle}
            </h1>
            <p className="text-[10px] font-medium uppercase tracking-widest text-slate-500">
              Wealth Management
            </p>
          </div>
        </div>

        <nav className="space-y-1">
          {nav.map((item, i) => {
            const Icon = item.icon;
            const active = location.pathname === item.path;
            return (
              <motion.div
                key={item.path}
                initial={{ opacity: 0, x: -12 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.05 }}
              >
                <Link
                  to={item.path}
                  className={`nav-item ${active ? "nav-item-active" : ""}`}
                >
                  <Icon className={`w-5 h-5 ${active ? "text-accent-cyan" : "text-slate-500"}`} />
                  <span>{item.label}</span>
                  {active && (
                    <motion.div
                      layoutId="nav-glow"
                      className="absolute inset-0 rounded-xl bg-gradient-to-r from-accent-blue/10 to-transparent -z-10"
                      transition={{ type: "spring", bounce: 0.15, duration: 0.5 }}
                    />
                  )}
                </Link>
              </motion.div>
            );
          })}
        </nav>

        <div className="mt-auto pt-8 px-2 hidden md:block">
          <div className="rounded-xl border border-fintech-border bg-white/50 p-3">
            <p className="text-xs text-slate-500 mb-1">Phiên bản</p>
            <p className="text-sm font-mono font-medium text-slate-700">v2.0 Fintech</p>
          </div>
        </div>
      </aside>

      <main className="flex-1 p-4 md:p-8 overflow-auto">
        <motion.div
          key={location.pathname}
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
        >
          {children}
        </motion.div>
      </main>
    </div>
  );
}
