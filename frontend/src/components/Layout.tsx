import { Link, useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import {
  BarChart3,
  BookOpen,
  Cog,
  Coins,
  // FlaskConical,
  GitCompare,
  HelpCircle,
  LineChart,
  Menu,
  Newspaper,
  Receipt,
  Scale,
  Settings,
  TrendingUp,
  Wallet,
  X,
} from "lucide-react";
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { labels } from "../i18n/vi";
import { getAiStatus } from "../api/news";
import { ApiKeyBanner } from "./ApiKeyBanner";
import { GeminiApiKeyModal } from "./GeminiApiKeyModal";
import { HelpModal } from "./HelpModal";
import { InfoTooltip } from "./InfoTooltip";
import { OfflineBanner } from "./OfflineBanner";
import { OnboardingTour, TourStep } from "./OnboardingTour";
import { PriceAlertsBell } from "./PriceAlertsBell";
import { PwaInstallPrompt } from "./PwaInstallPrompt";
import { ThemeSelector } from "./ThemeSelector";
import { usePersistentState } from "../hooks/usePersistentState";

const nav = [
  { path: "/", label: labels.nav.dashboard, icon: BarChart3, tour: "dashboard", color: "accent-blue" },
  { path: "/assets", label: labels.nav.assets, icon: Coins, tour: "assets", color: "accent-violet" },
  { path: "/transactions", label: labels.nav.transactions, icon: Receipt, tour: "transactions", color: "accent-rose" },
  { path: "/analytics", label: labels.nav.analytics, icon: TrendingUp, color: "accent-emerald" },
  // { path: "/backtest", label: labels.nav.backtest, icon: FlaskConical, color: "accent-amber" },
  { path: "/rebalance", label: labels.nav.rebalance, icon: Scale, color: "accent-amber" },
  { path: "/market", label: labels.nav.market, icon: LineChart, color: "accent-cyan" },
  { path: "/compare", label: labels.nav.compare, icon: GitCompare, color: "accent-blue" },
  { path: "/news", label: labels.nav.news, icon: Newspaper, color: "accent-violet" },
  { path: "/settings", label: labels.nav.settings, icon: Settings, tour: "settings", color: "accent-emerald" },
  { path: "/env-config", label: labels.nav.envConfig, icon: Cog, color: "accent-rose" },
];

const tourSteps: TourStep[] = [
  { target: "dashboard", title: labels.onboarding.step1Title, description: labels.onboarding.step1Description },
  { target: "assets", title: labels.onboarding.step2Title, description: labels.onboarding.step2Description },
  { target: "transactions", title: labels.onboarding.step3Title, description: labels.onboarding.step3Description },
  { target: "settings", title: labels.onboarding.step4Title, description: labels.onboarding.step4Description },
];

const TOUR_FLAG = "wealth_onboarding_completed";

function SidebarHeader({ closeButton }: { closeButton?: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between mb-8 px-2">
      <div className="flex items-center gap-3">
        <div className="relative flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-br from-accent-blue to-accent-violet shadow-lg shadow-accent-blue/30">
          <Wallet className="w-5 h-5 text-theme-inverse" />
          <div className="absolute inset-0 rounded-xl bg-accent-cyan/20 blur-md" />
        </div>
        <div>
          <h1 className="font-display font-bold text-lg text-theme tracking-tight">
            {labels.app.shortTitle}
          </h1>
          <p className="text-[10px] font-medium uppercase tracking-widest text-theme-muted">
            {labels.app.subtitle}
          </p>
        </div>
      </div>
      {closeButton}
    </div>
  );
}

function NavLinks({ onClick }: { onClick?: () => void }) {
  const location = useLocation();
  return (
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
              data-tour={item.tour}
              onClick={onClick}
              className={`group nav-item ${active ? "nav-item-active" : ""}`}
            >
              <Icon
                className={`w-5 h-5 transition-opacity ${active ? "opacity-100" : "opacity-55 group-hover:opacity-100"}`}
                style={{ color: `var(--${item.color})` }}
              />
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
  );
}

function SidebarFooter({ onStartTour, onShowHelp }: { onStartTour: () => void; onShowHelp: () => void }) {
  return (
    <div className="mt-auto pt-8">
      <div className="mb-2">
        <ThemeSelector />
      </div>
      <button
        onClick={onStartTour}
        className="w-full flex items-center gap-2 rounded-xl px-3 py-2.5 text-sm font-medium text-theme-muted transition-all hover:bg-accent-blue/[0.06] hover:text-accent-blue"
      >
        <HelpCircle className="w-4 h-4" />
        {labels.onboarding.startTour}
        <span className="ml-auto">
          <InfoTooltip content={labels.tooltips.startTour} />
        </span>
      </button>
      <button
        onClick={onShowHelp}
        className="w-full flex items-center gap-2 rounded-xl px-3 py-2.5 text-sm font-medium text-theme-muted transition-all hover:bg-accent-blue/[0.06] hover:text-accent-blue mt-1"
      >
        <BookOpen className="w-4 h-4" />
        {labels.guide.title}
        <span className="ml-auto">
          <InfoTooltip content={labels.tooltips.helpButton} />
        </span>
      </button>
      <div className="rounded-xl border border-fintech-border bg-surface-card/80 p-3 mt-2">
        <p className="text-xs text-theme-muted mb-1">Phiên bản</p>
        <p className="text-sm font-mono font-medium text-theme-muted">v2.0 Fintech</p>
      </div>
    </div>
  );
}

export function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const [showTour, setShowTour] = useState(() => {
    try {
      return !localStorage.getItem(TOUR_FLAG);
    } catch {
      return false;
    }
  });
  const [showHelp, setShowHelp] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const [geminiOnboardingDone, setGeminiOnboardingDone] = usePersistentState(
    "gemini-api-key-onboarding-completed",
    false
  );

  const { data: aiStatusData } = useQuery({
    queryKey: ["ai-status-modal"],
    queryFn: getAiStatus,
    refetchInterval: false,
    staleTime: 60_000,
  });

  const showGeminiModal =
    !geminiOnboardingDone &&
    aiStatusData?.ai_provider === "gemini" &&
    aiStatusData?.gemini_configured === false;

  useEffect(() => {
    setMobileMenuOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    if (mobileMenuOpen) {
      document.body.classList.add("overflow-hidden");
    } else {
      document.body.classList.remove("overflow-hidden");
    }
    return () => document.body.classList.remove("overflow-hidden");
  }, [mobileMenuOpen]);

  const finishTour = () => {
    try {
      localStorage.setItem(TOUR_FLAG, "true");
    } catch {
      // ignore
    }
    setShowTour(false);
  };

  return (
    <div className="min-h-screen flex flex-col md:flex-row font-body">
      <aside className="hidden md:flex md:sticky md:top-0 md:self-start md:h-screen md:overflow-y-auto md:w-64 md:shrink-0 md:flex-col border-b md:border-b-0 md:border-r border-fintech-border bg-surface-elevated/80 backdrop-blur-xl p-4 scrollbar-thumb-hidden">
        <SidebarHeader />
        <NavLinks />
        <SidebarFooter onStartTour={() => setShowTour(true)} onShowHelp={() => setShowHelp(true)} />
      </aside>

      {mobileMenuOpen && (
        <div className="fixed inset-0 z-[60] flex flex-col bg-surface-elevated/95 backdrop-blur-xl p-4 md:hidden overflow-y-auto scrollbar-thumb-hidden">
          <SidebarHeader
            closeButton={
              <button
                onClick={() => setMobileMenuOpen(false)}
                className="p-2 rounded-lg text-theme-muted hover:bg-accent-blue/[0.06] hover:text-accent-blue transition-colors"
                aria-label={labels.common.close}
              >
                <X className="w-6 h-6" />
              </button>
            }
          />
          <NavLinks onClick={() => setMobileMenuOpen(false)} />
          <SidebarFooter onStartTour={() => setShowTour(true)} onShowHelp={() => setShowHelp(true)} />
        </div>
      )}

      <PriceAlertsBell />

      {showTour && (
        <OnboardingTour
          steps={tourSteps}
          onComplete={finishTour}
          onSkip={finishTour}
        />
      )}
      {showGeminiModal && (
        <GeminiApiKeyModal
          onSave={() => setGeminiOnboardingDone(true)}
          onSkip={() => setGeminiOnboardingDone(true)}
        />
      )}
      <HelpModal open={showHelp} onClose={() => setShowHelp(false)} />

      <main className="flex-1 p-4 md:p-8 overflow-auto">
        <ApiKeyBanner />
        <OfflineBanner />
        <PwaInstallPrompt />
        <div className="flex items-center justify-between mb-4 md:hidden">
          <button
            onClick={() => setMobileMenuOpen(true)}
            className="inline-flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium text-theme bg-surface-card/80 border border-fintech-border hover:bg-surface-elevated transition-colors"
          >
            <Menu className="w-5 h-5" />
            <span className="font-display font-semibold">{labels.app.shortTitle}</span>
          </button>
          <button
            onClick={() => setShowHelp(true)}
            className="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium text-accent-blue bg-accent-blue/[0.08] hover:bg-accent-blue/15 transition-colors"
          >
            <HelpCircle className="w-4 h-4" />
            {labels.guide.title}
          </button>
        </div>
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
