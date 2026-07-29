import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  ArrowDownRight,
  ArrowRight,
  ArrowUpRight,
  BarChart3,
  Bell,
  Bot,
  Check,
  Copy,
  GitCompare,
  History,
  LineChart as LineChartIcon,
  Newspaper,
  Plus,
  QrCode,
  Receipt,
  RefreshCw,
  Scale,
  Settings,
  Sparkles,
  TrendingUp,
  Wallet,
} from "lucide-react";
import { QRCodeSVG } from "qrcode.react";
import { Link } from "react-router-dom";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import API from "../api/client";
import { getPortfolioInsight } from "../api/ai";
import { getSymbols, getHistory } from "../api/compare";
import { getAlerts, getDailyBrief, type Article } from "../api/news";
import { AiGenerateButton } from "../components/AiGenerateButton";
import { AiInsightCard } from "../components/AiInsightCard";
import { ErrorMessage } from "../components/ErrorMessage";
import { EmptyState } from "../components/EmptyState";
import { InfoTooltip } from "../components/InfoTooltip";
import { PriceAlertsSection } from "../components/PriceAlertsSection";
import { SummaryCards } from "../components/SummaryCards";
import { AnimatedNumber } from "../components/ui/AnimatedNumber";
import { Value } from "../components/Value";
import { FintechCard } from "../components/ui/FintechCard";
import { MiniSparkline } from "../components/ui/MiniSparkline";
import { SectionHeader } from "../components/ui/SectionHeader";
import { Skeleton } from "../components/ui/Skeleton";
import { usePersistentState } from "../hooks/usePersistentState";
import { TrendBadge } from "../components/ui/TrendBadge";
import { QuickAddCard } from "../components/QuickAddCard";
import { useTheme } from "../contexts/ThemeContext";
import { useToast } from "../contexts/ToastContext";
import { useAiInsight } from "../hooks/useAiInsight";
import { labels } from "../i18n/vi";
import { chartTooltipStyle, formatCurrency, formatNumber, formatPercent } from "../lib/utils";

const TYPE_COLORS: Record<string, string> = {
  STOCK: "var(--accent-blue)",
  FUND: "var(--accent-violet)",
  ETF: "var(--accent-cyan)",
  GOLD: "var(--accent-amber)",
  CRYPTO: "var(--accent-rose)",
  REAL_ESTATE: "var(--accent-emerald)",
  LIFE_INSURANCE: "var(--accent-violet)",
};
const WATCHLIST_SYMBOLS =
  "VCB,VHM,VIC,FPT,GAS,HPG,MBB,MSN,MWG,PLX,SSI,TCB,VIB,VPB,E1VFVN30,FUEVFVND,FUESSVFL";
const WATCHLIST_STOCKS = [
  "VCB", "VHM", "VIC", "FPT", "GAS", "HPG", "MBB", "MSN", "MWG", "PLX", "SSI", "TCB", "VIB", "VPB",
];
const WATCHLIST_FUNDS = ["E1VFVN30", "FUEVFVND", "FUESSVFL"];

function generatePriceSparkline(price: number, changePercent: number, points = 14): number[] {
  const prev = price / (1 + changePercent / 100);
  const data: number[] = [];
  for (let i = 0; i < points; i++) {
    const ratio = i / (points - 1);
    const base = prev + (price - prev) * ratio;
    const noise = (Math.random() - 0.5) * Math.abs(price - prev) * 0.4;
    data.push(Math.max(base + noise, price * 0.5));
  }
  data[data.length - 1] = price;
  return data;
}

function formatRelativeTime(date: string | null): string {
  if (!date) return "";
  const d = new Date(date);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  const diffHour = Math.floor(diffMs / 3600000);
  const diffDay = Math.floor(diffMs / 86400000);
  if (diffMin < 1) return "Vừa xong";
  if (diffMin < 60) return `${diffMin} phút`;
  if (diffHour < 24) return `${diffHour} giờ`;
  if (diffDay < 7) return `${diffDay} ngày`;
  return d.toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit" });
}

function SectionLink({ to, children }: { to: string; children: React.ReactNode }) {
  return (
    <Link
      to={to}
      className="inline-flex items-center gap-1 text-xs font-medium text-accent-blue hover:text-accent-violet transition-colors"
    >
      {children}
      <ArrowRight className="w-3.5 h-3.5" />
    </Link>
  );
}

function MobileQrCard() {
  const [url, setUrl] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const envUrl = import.meta.env.VITE_LAN_URL;
    if (envUrl) {
      setUrl(`${envUrl}${window.location.pathname}`);
      return;
    }
    const port = window.location.port;
    API.get("/lan-ip")
      .then((res) => {
        const ip = res.data?.ip;
        if (ip) {
          setUrl(`http://${ip}:${port}${window.location.pathname}`);
        } else {
          setUrl(window.location.href);
        }
      })
      .catch(() => setUrl(window.location.href));
  }, []);

  const handleCopy = async () => {
    if (!url) return;
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // ignore
    }
  };

  if (!url) return null;

  return (
    <FintechCard delay={0.4}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-accent-emerald/10 text-accent-emerald">
            <QrCode className="w-4 h-4" />
          </div>
          <h3 className="card-title">{labels.dashboard.mobileAccess}</h3>
        </div>
        <InfoTooltip content={labels.tooltips.dashboardQrMobile} />
      </div>
      <div className="flex flex-col items-center gap-3">
        <div className="p-2 bg-white rounded-lg border border-slate-100 shadow-sm">
          <QRCodeSVG value={url} size={128} level="M" includeMargin={false} />
        </div>
        <div className="w-full">
          <div className="text-xs text-slate-500 mb-1">{labels.dashboard.scanQrToOpen}</div>
          <div className="flex items-center gap-2">
            <div className="flex-1 text-xs font-mono text-slate-700 truncate bg-slate-50 px-2 py-1.5 rounded">
              {url}
            </div>
            <button
              onClick={handleCopy}
              className="p-1.5 rounded-md bg-slate-100 text-slate-600 hover:bg-slate-200 transition-colors"
              title={labels.common.copyLink}
            >
              {copied ? <Check className="w-4 h-4 text-accent-emerald" /> : <Copy className="w-4 h-4" />}
            </button>
          </div>
        </div>
      </div>
    </FintechCard>
  );
}

export function Dashboard() {
  const qc = useQueryClient();
  const { showToast } = useToast();
  const { theme } = useTheme();

  const portfolio = useQuery({
    queryKey: ["portfolio"],
    queryFn: async () => (await API.get("/portfolio/")).data,
  });

  const history = useQuery({
    queryKey: ["portfolio-history"],
    queryFn: async () => {
      const end = new Date().toISOString().split("T")[0];
      const start = new Date(Date.now() - 180 * 24 * 60 * 60 * 1000).toISOString().split("T")[0];
      const { data } = await API.get("/portfolio/history", { params: { start, end } });
      return data as Array<{ date: string; value: number; cost: number }>;
    },
  });

  const [trendPeriod, setTrendPeriod] = usePersistentState<
    "1W" | "1M" | "3M" | "6M" | "1Y" | "ALL" | "CUSTOM"
  >("dashboard.trendPeriod", "6M");
  const [trendCustomStart, setTrendCustomStart] = usePersistentState(
    "dashboard.trendCustomStart",
    ""
  );
  const [trendCustomEnd, setTrendCustomEnd] = usePersistentState(
    "dashboard.trendCustomEnd",
    ""
  );

  const trendDateRange = useMemo(() => {
    const end = new Date().toISOString().split("T")[0];
    if (trendPeriod === "CUSTOM") {
      return {
        start: trendCustomStart || end,
        end: trendCustomEnd || end,
      };
    }
    if (trendPeriod === "ALL") {
      return { start: undefined as string | undefined, end };
    }
    const days =
      {
        "1W": 7,
        "1M": 30,
        "3M": 90,
        "6M": 180,
        "1Y": 365,
      }[trendPeriod] || 180;
    const start = new Date(Date.now() - days * 24 * 60 * 60 * 1000)
      .toISOString()
      .split("T")[0];
    return { start, end };
  }, [trendPeriod, trendCustomStart, trendCustomEnd]);

  const trendHistory = useQuery({
    queryKey: ["portfolio-history-trend", trendDateRange.start, trendDateRange.end],
    queryFn: async () => {
      const params: Record<string, string> = { end: trendDateRange.end };
      if (trendDateRange.start) params.start = trendDateRange.start;
      const { data } = await API.get("/portfolio/history", { params });
      return data as Array<{ date: string; value: number; cost: number }>;
    },
    placeholderData: keepPreviousData,
    enabled: trendPeriod !== "CUSTOM" || Boolean(trendCustomStart && trendCustomEnd),
  });

  const trendBenchmarkStart = trendDateRange.start || trendHistory.data?.[0]?.date;
  const trendBenchmark = useQuery({
    queryKey: ["portfolio-benchmark-trend", trendBenchmarkStart, trendDateRange.end],
    queryFn: async () => {
      const params: Record<string, string> = { end: trendDateRange.end };
      if (trendBenchmarkStart) params.start = trendBenchmarkStart;
      const { data } = await API.get("/prices/benchmark/VNINDEX", { params });
      return data as Array<{ date: string; portfolio_value: number; benchmark_value: number }>;
    },
    enabled: trendHistory.data && trendHistory.data.length > 1,
    placeholderData: keepPreviousData,
  });

  const analytics = useQuery({
    queryKey: ["analytics"],
    queryFn: async () => (await API.get("/analytics/")).data,
  });

  const risk = useQuery({
    queryKey: ["analytics-risk"],
    queryFn: async () => (await API.get("/analytics/risk")).data,
  });

  const rebalance = useQuery({
    queryKey: ["rebalance"],
    queryFn: async () => (await API.get("/rebalance/")).data,
  });

  const recentTransactions = useQuery({
    queryKey: ["transactions"],
    queryFn: async () => (await API.get("/transactions/")).data as Array<{
      id: number;
      asset_id: number;
      symbol?: string;
      type: string;
      quantity: number;
      price: number;
      fee: number;
      date: string;
      notes?: string;
    }>,
  });

  const assets = useQuery({
    queryKey: ["assets"],
    queryFn: async () => (await API.get("/assets/")).data as Array<{
      id: number;
      symbol: string;
      name?: string;
      type: string;
    }>,
  });

  const [marketTab, setMarketTab] = usePersistentState<"STOCK" | "FUND" | "GOLD">(
    "dashboard.marketTab",
    "STOCK"
  );
  const [compareA, setCompareA] = usePersistentState("dashboard.compareA", "");
  const [compareB, setCompareB] = usePersistentState("dashboard.compareB", "");

  const [newsRegion, setNewsRegion] = usePersistentState<"vn" | "global">(
    "dashboard.newsRegion",
    "vn"
  );

  const portfolioSymbols = (portfolio.data?.items || [])
    .filter((item: any) => ["STOCK", "FUND"].includes(item.type))
    .map((item: any) => item.symbol);
  const marketSymbols = Array.from(new Set([...portfolioSymbols, ...WATCHLIST_SYMBOLS.split(",")]));

  const marketQuotes = useQuery({
    queryKey: ["market-quotes", marketSymbols],
    queryFn: async () => {
      const { data } = await API.get("/prices/quote", { params: { symbols: marketSymbols.join(",") } });
      return data as Array<{ symbol: string; price: number; change: number; change_percent: number; date: string }>;
    },
    enabled: marketSymbols.length > 0,
  });

  const goldFx = useQuery({
    queryKey: ["gold-fx"],
    queryFn: async () => (await API.get("/gold-fx/")).data,
  });

  const compareSymbolsList = useQuery({
    queryKey: ["compare-symbols"],
    queryFn: getSymbols,
  });

  const compareToday = new Date().toISOString().split("T")[0];
  const compareStart = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split("T")[0];

  const compareHistoryA = useQuery({
    queryKey: ["compare-history", compareA, compareStart, compareToday],
    queryFn: async () => {
      const symbol = compareSymbolsList.data?.find((s) => s.symbol === compareA);
      if (!symbol) return [];
      return getHistory(compareA, symbol.type, compareStart, compareToday);
    },
    enabled: !!compareA && compareSymbolsList.data != null,
  });

  const compareHistoryB = useQuery({
    queryKey: ["compare-history", compareB, compareStart, compareToday],
    queryFn: async () => {
      const symbol = compareSymbolsList.data?.find((s) => s.symbol === compareB);
      if (!symbol) return [];
      return getHistory(compareB, symbol.type, compareStart, compareToday);
    },
    enabled: !!compareB && compareSymbolsList.data != null,
  });

  const alerts = useQuery({
    queryKey: ["news-alerts-unread"],
    queryFn: async () => getAlerts(true),
  });

  const dailyBrief = useQuery({
    queryKey: ["news-daily-brief", newsRegion],
    queryFn: async () => getDailyBrief(24, newsRegion),
  });

  const refresh = useMutation({
    mutationFn: () => API.post("/prices/refresh-all"),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["portfolio"] });
      qc.invalidateQueries({ queryKey: ["portfolio-history"] });
      qc.invalidateQueries({ queryKey: ["portfolio-history-trend"] });
      qc.invalidateQueries({ queryKey: ["portfolio-benchmark-trend"] });
      qc.invalidateQueries({ queryKey: ["prices"] });
      qc.invalidateQueries({ queryKey: ["market-watchlist"] });
      qc.invalidateQueries({ queryKey: ["price-alerts"] });
      qc.invalidateQueries({ queryKey: ["price-alerts-notifications"] });
      showToast("Đã cập nhật giá thành công", "success");
    },
    onError: (error: any) => {
      showToast(error?.response?.data?.detail || "Không thể cập nhật giá", "error");
    },
  });

  const portfolioInsight = useAiInsight({
    taskName: "portfolio_insight",
    fetcher: getPortfolioInsight,
  });

  const data = portfolio.data || {
    total_value: 0,
    total_cost: 0,
    total_pnl: 0,
    total_pnl_percent: 0,
    market_value: 0,
    market_cost: 0,
    stable_value: 0,
    items: [],
  };

  // Contextual insight: month-over-month change in net worth
  const monthlyChange = useMemo(() => {
    const hist = history.data || [];
    if (hist.length < 2) return null;
    const sorted = [...hist].sort((a, b) => a.date.localeCompare(b.date));
    const latest = sorted[sorted.length - 1];
    const now = new Date();
    const target = new Date(now);
    target.setDate(now.getDate() - 30);
    const targetIso = target.toISOString().split("T")[0];
    const past =
      sorted.find((h) => h.date >= targetIso) || sorted[0];
    if (!past || past.value <= 0) return null;
    const pct = ((latest.value - past.value) / past.value) * 100;
    return { pct, delta: latest.value - past.value };
  }, [history.data]);

  const trendPercentData = useMemo(() => {
    const trendMap = new Map<string, { label: string; portfolio?: number; benchmark?: number }>();
    for (const point of trendHistory.data || []) {
      const date = new Date(point.date);
      const label = date.toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit" });
      const iso = point.date;
      trendMap.set(iso, { ...(trendMap.get(iso) || { label }), label, portfolio: point.value });
    }
    for (const point of trendBenchmark.data || []) {
      const date = new Date(point.date);
      const label = date.toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit" });
      const iso = point.date;
      trendMap.set(iso, { ...(trendMap.get(iso) || { label }), label, benchmark: point.benchmark_value });
    }
    const trendData = Array.from(trendMap.entries())
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([_, { label, portfolio, benchmark }]) => ({ date: label, portfolio, benchmark }));

    let basePortfolio: number | null = null;
    let baseBenchmark: number | null = null;
    for (const d of trendData) {
      if (d.portfolio != null && d.portfolio > 0 && d.benchmark != null && d.benchmark > 0) {
        basePortfolio = d.portfolio;
        baseBenchmark = d.benchmark;
        break;
      }
    }
    return trendData.map((d) => ({
      date: d.date,
      portfolio: basePortfolio ? ((d.portfolio ?? basePortfolio) / basePortfolio - 1) * 100 : null,
      benchmark: baseBenchmark ? ((d.benchmark ?? baseBenchmark) / baseBenchmark - 1) * 100 : null,
    }));
  }, [trendHistory.data, trendBenchmark.data]);

  const [displayTrendData, setDisplayTrendData] = useState<typeof trendPercentData>([]);
  const [hasTrendData, setHasTrendData] = useState(false);
  useEffect(() => {
    if (trendHistory.isLoading || trendHistory.isFetching) return;
    if (trendPercentData.length > 1) {
      setDisplayTrendData(trendPercentData);
      setHasTrendData(true);
    } else if (trendPeriod !== "CUSTOM" || (trendCustomStart && trendCustomEnd)) {
      setHasTrendData(false);
    }
  }, [
    trendPercentData,
    trendHistory.isLoading,
    trendHistory.isFetching,
    trendPeriod,
    trendCustomStart,
    trendCustomEnd,
  ]);

  const portfolioMarketItems = (portfolio.data?.items || [])
    .filter((item: any) => item.type === marketTab)
    .map((item: any) => {
      const quote = marketQuotes.data?.find((q: any) => q.symbol === item.symbol);
      return quote
        ? { ...quote, isPortfolio: true }
        : { symbol: item.symbol, price: 0, change: 0, change_percent: 0, isPortfolio: true };
    })
    .filter((item: any) => item.price > 0);

  const watchlistMarketItems = (marketQuotes.data || [])
    .filter((q: any) => {
      if (marketTab === "STOCK") return WATCHLIST_STOCKS.includes(q.symbol);
      if (marketTab === "FUND") return WATCHLIST_FUNDS.includes(q.symbol);
      return false;
    })
    .map((q: any) => ({ ...q, isPortfolio: false }))
    .filter((q: any) => !portfolioMarketItems.find((p: any) => p.symbol === q.symbol));

  const marketListItems = [...portfolioMarketItems, ...watchlistMarketItems].slice(0, 5);

  const goldListItems = (goldFx.data?.gold || []) as Array<{
    source: string;
    buy: number;
    sell: number;
    change?: number;
    change_percent?: number;
  }>;

  const compareChartData = useMemo(() => {
    const rawSeries: Record<string, Record<string, number>> = {};
    const allDates = new Set<string>();
    [
      { symbol: compareA, data: compareHistoryA.data || [] },
      { symbol: compareB, data: compareHistoryB.data || [] },
    ].forEach(({ symbol, data }) => {
      if (!symbol || data.length === 0) return;
      const firstPrice = data[0].price;
      if (firstPrice <= 0) return;
      const series: Record<string, number> = {};
      data.forEach((point) => {
        series[point.date] = (point.price / firstPrice) * 100;
        allDates.add(point.date);
      });
      rawSeries[symbol] = series;
    });
    if (allDates.size === 0) return [];
    const sortedDates = Array.from(allDates).sort();
    const filledSeries: Record<string, Record<string, number>> = {};
    [compareA, compareB].forEach((symbol) => {
      const series = rawSeries[symbol];
      if (!series) return;
      let lastValue: number | null = null;
      const filled: Record<string, number> = {};
      sortedDates.forEach((date) => {
        if (series[date] !== undefined) lastValue = series[date];
        if (lastValue !== null) filled[date] = lastValue;
      });
      filledSeries[symbol] = filled;
    });
    return sortedDates
      .map((date) => ({
        date: new Date(date).toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit" }),
        a: filledSeries[compareA]?.[date] ?? null,
        b: filledSeries[compareB]?.[date] ?? null,
      }))
      .filter((d) => d.a != null || d.b != null);
  }, [compareHistoryA.data, compareHistoryB.data, compareA, compareB]);

  const topGainer = analytics.data?.top_performers?.[0];
  const topLoser = analytics.data?.bottom_performers?.[0];

  // Recent activity: last 5 transactions enriched with asset symbol/name
  const recentActivity = useMemo(() => {
    const txns = (recentTransactions.data || []).slice();
    txns.sort((a, b) => (b.date || "").localeCompare(a.date || ""));
    return txns.slice(0, 5).map((t) => {
      const asset = (assets.data || []).find((a) => a.id === t.asset_id);
      return {
        ...t,
        symbol: t.symbol || asset?.symbol || `#${t.asset_id}`,
        assetName: asset?.name || asset?.symbol || "",
      };
    });
  }, [recentTransactions.data, assets.data]);

  const transactionTypeLabel = (type: string) => {
    switch (type) {
      case "BUY": return labels.transactions.buy;
      case "SELL": return labels.transactions.sell;
      case "DEPOSIT": return labels.transactions.deposit;
      case "WITHDRAWAL": return labels.transactions.withdrawal;
      default: return type;
    }
  };

  const transactionTypeBadgeClass = (type: string) => {
    if (type === "BUY" || type === "DEPOSIT") return "badge-gain";
    if (type === "SELL" || type === "WITHDRAWAL") return "badge-loss";
    return "badge-loss";
  };

  const biggestDrift = (rebalance.data?.suggestions || [])
    .map((s: any) => ({ ...s, drift: Math.abs(s.current_percent - s.target_percent) }))
    .sort((a: any, b: any) => b.drift - a.drift)[0];

  const unreadAlerts = (alerts.data || []).filter((a) => !a.is_read).length;

  const isLoading =
    portfolio.isLoading ||
    history.isLoading ||
    analytics.isLoading ||
    risk.isLoading ||
    rebalance.isLoading ||
    marketQuotes.isLoading ||
    compareSymbolsList.isLoading;

  return (
    <div className="space-y-6">
      {portfolio.isError && <ErrorMessage error={portfolio.error} retry={() => portfolio.refetch()} />}
      {history.isError && <ErrorMessage error={history.error} retry={() => history.refetch()} />}
      {trendHistory.isError && <ErrorMessage error={trendHistory.error} retry={() => trendHistory.refetch()} />}
      {trendBenchmark.isError && <ErrorMessage error={trendBenchmark.error} retry={() => trendBenchmark.refetch()} />}
      {refresh.isError && <ErrorMessage error={refresh.error} retry={() => refresh.mutate()} />}

      <SectionHeader title={labels.dashboard.title}>
        <div className="flex items-center gap-3">
          {portfolio.dataUpdatedAt > 0 && (
            <span className="text-xs text-slate-500 hidden sm:inline">
              Cập nhật: {new Date(portfolio.dataUpdatedAt).toLocaleString("vi-VN")}
            </span>
          )}
          <InfoTooltip content={labels.tooltips.refreshPrices} />
          <button
            onClick={() => refresh.mutate()}
            disabled={refresh.isPending}
            className="btn-primary"
          >
            <RefreshCw className={`w-4 h-4 ${refresh.isPending ? "animate-spin" : ""}`} />
            {refresh.isPending ? labels.dashboard.refreshing : labels.dashboard.refreshPrices}
          </button>
        </div>
      </SectionHeader>

      {portfolio.isLoading ? (
        <Skeleton className="h-40" />
      ) : (
        <FintechCard delay={0.02} hover={false} className="relative overflow-hidden">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="min-w-0">
              <div className="flex items-center gap-2 mb-2">
                <div className="p-1.5 rounded-lg bg-accent-cyan/10 text-accent-cyan ring-1 ring-inset ring-accent-cyan/20">
                  <Wallet className="w-4 h-4" />
                </div>
                <span className="text-sm font-medium text-slate-500">
                  {labels.summary.totalValue}
                </span>
                <InfoTooltip content={labels.tooltips.totalValue} />
              </div>
              <div className="font-mono font-bold tracking-tight text-slate-900 text-3xl sm:text-4xl lg:text-5xl">
                <AnimatedNumber
                  value={data.total_value}
                  formatter={formatCurrency}
                  duration={1400}
                  className="block"
                  title={formatCurrency(data.total_value)}
                />
              </div>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <TrendBadge value={data.total_pnl_percent} />
                <span className={`text-sm font-medium ${data.total_pnl >= 0 ? "text-accent-emerald" : "text-accent-rose"}`}>
                  {data.total_pnl >= 0 ? "+" : ""}
                  <AnimatedNumber value={data.total_pnl} formatter={formatCurrency} duration={1400} />
                </span>
              </div>
            </div>
            {monthlyChange && (
              <div className="flex items-center gap-2 rounded-xl bg-slate-50/80 px-3 py-2 ring-1 ring-inset ring-slate-200/60">
                <Sparkles className={`w-4 h-4 ${monthlyChange.pct >= 0 ? "text-accent-emerald" : "text-accent-rose"}`} />
                <div className="text-xs leading-tight">
                  <div className="text-slate-500">30 ngày qua</div>
                  <div className={`font-semibold ${monthlyChange.pct >= 0 ? "text-accent-emerald" : "text-accent-rose"}`}>
                    {monthlyChange.pct >= 0 ? "Tăng" : "Giảm"} {formatPercent(Math.abs(monthlyChange.pct))}
                    {" "}
                    <span className="text-slate-400 font-normal">
                      ({monthlyChange.delta >= 0 ? "+" : ""}{formatCurrency(monthlyChange.delta)})
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </FintechCard>
      )}

      {portfolio.isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Skeleton className="h-28" count={3} />
        </div>
      ) : (
        <SummaryCards {...data} history={history.data} />
      )}

      <FintechCard delay={0.08}>
        <div className="flex items-center justify-between mb-3">
          <h3 className="card-title inline-flex items-center gap-2">
            <Bot className="w-4 h-4 text-accent-violet" />
            Phân tích AI danh mục
          </h3>
          <AiGenerateButton
            label="Phân tích"
            onClick={() => portfolioInsight.generate()}
            loading={portfolioInsight.loading}
          />
        </div>
        <AiInsightCard
          data={portfolioInsight.data}
          loading={portfolioInsight.loading}
          error={portfolioInsight.error}
          onClose={portfolioInsight.clear}
        />
      </FintechCard>

      <FintechCard delay={0.1} className="!p-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 px-2">
            {labels.dashboard.quickActions}
          </span>
          <InfoTooltip content={labels.tooltips.dashboardQuickActions} />
          <div className="w-px h-4 bg-slate-200 mx-1 hidden sm:block" />
          <Link to="/transactions" className="btn-secondary py-1.5 px-3 text-xs">
            <Receipt className="w-3.5 h-3.5" />
            {labels.dashboard.addTransaction}
          </Link>
          <Link to="/assets" className="btn-secondary py-1.5 px-3 text-xs">
            <Plus className="w-3.5 h-3.5" />
            {labels.dashboard.addAsset}
          </Link>
          <Link to="/assets" className="btn-secondary py-1.5 px-3 text-xs">
            <Wallet className="w-3.5 h-3.5" />
            Xem danh mục
          </Link>
          <Link to="/analytics" className="btn-secondary py-1.5 px-3 text-xs">
            <BarChart3 className="w-3.5 h-3.5" />
            Báo cáo
          </Link>
          <Link to="/rebalance" className="btn-secondary py-1.5 px-3 text-xs">
            <Scale className="w-3.5 h-3.5" />
            {labels.dashboard.runRebalance}
          </Link>
          <Link to="/news" className="btn-secondary py-1.5 px-3 text-xs">
            <Newspaper className="w-3.5 h-3.5" />
            {labels.dashboard.news}
          </Link>
          <Link to="/market" className="btn-secondary py-1.5 px-3 text-xs">
            <LineChartIcon className="w-3.5 h-3.5" />
            {labels.market.title}
          </Link>
          <Link to="/settings" className="btn-secondary py-1.5 px-3 text-xs">
            <Settings className="w-3.5 h-3.5" />
            Cài đặt
          </Link>
        </div>
      </FintechCard>

      <FintechCard delay={0.12}>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-accent-blue/10 text-accent-blue">
              <History className="w-4 h-4" />
            </div>
            <h3 className="card-title">Hoạt động gần đây</h3>
          </div>
          <SectionLink to="/transactions">{labels.dashboard.viewAll}</SectionLink>
        </div>
        {recentTransactions.isLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-12" count={3} />
          </div>
        ) : recentActivity.length > 0 ? (
          <div className="space-y-1">
            {recentActivity.map((t, idx) => {
              const isBuy = t.type === "BUY" || t.type === "DEPOSIT";
              const total = (t.quantity || 0) * (t.price || 0) + (t.fee || 0);
              return (
                <div
                  key={t.id}
                  className={`flex items-center justify-between py-2 ${idx > 0 ? "border-t border-slate-100" : ""}`}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div className={`p-1.5 rounded-lg ${isBuy ? "bg-accent-emerald/10 text-accent-emerald" : "bg-accent-rose/10 text-accent-rose"}`}>
                      {isBuy ? <ArrowDownRight className="w-4 h-4" /> : <ArrowUpRight className="w-4 h-4" />}
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-display font-semibold text-slate-900 text-sm">
                          {t.symbol}
                        </span>
                        <span className={`px-1.5 py-0.5 rounded-md text-[10px] font-medium ${transactionTypeBadgeClass(t.type)}`}>
                          {transactionTypeLabel(t.type)}
                        </span>
                      </div>
                      <div className="text-xs text-slate-500 mt-0.5">
                        {new Date(t.date).toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric" })}
                        {t.quantity > 0 && ` · ${formatNumber(t.quantity)} @ ${formatCurrency(t.price)}`}
                      </div>
                    </div>
                  </div>
                  <div className={`font-mono font-semibold text-sm whitespace-nowrap ${isBuy ? "text-accent-emerald" : "text-accent-rose"}`}>
                    {isBuy ? "-" : "+"}{formatCurrency(total)}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <EmptyState
            icon={<Receipt className="w-6 h-6" />}
            title="Ghi nhận giao dịch đầu tiên"
            description="Thêm giao dịch mua, bán hoặc nạp/rút để theo dõi lịch sử hoạt động và diễn biến danh mục."
            actionLabel={labels.dashboard.addTransaction}
            onAction={() => { window.location.hash = "/transactions"; }}
            delay={0}
          />
        )}
      </FintechCard>

      <PriceAlertsSection />

      <div className="space-y-2">
        <div className="flex items-center gap-2 px-1">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-500">
            {labels.dashboard.featureSpotlight}
          </h2>
          <InfoTooltip content={labels.tooltips.dashboardSpotlight} />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          <FintechCard delay={0.15}>
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-accent-emerald/10 text-accent-emerald">
                  <TrendingUp className="w-4 h-4" />
                </div>
                <h3 className="card-title">{labels.dashboard.analytics}</h3>
              </div>
              <SectionLink to="/analytics">{labels.dashboard.viewAll}</SectionLink>
            </div>
            {isLoading ? (
              <div className="space-y-2">
                <Skeleton className="h-12" />
                <Skeleton className="h-12" />
              </div>
            ) : (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="min-w-0 overflow-hidden">
                    <div className="text-xs text-slate-500 mb-0.5">{labels.summary.pnl}</div>
                    <div className={`font-mono font-semibold ${data.total_pnl >= 0 ? "text-accent-emerald" : "text-accent-rose"}`}>
                      <AnimatedNumber value={data.total_pnl} formatter={formatCurrency} className="block truncate" title={formatCurrency(data.total_pnl)} />
                    </div>
                  </div>
                  <TrendBadge value={data.total_pnl_percent} />
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-xs text-slate-500 mb-0.5">{labels.dashboard.topGainer}</div>
                    <div className="font-display font-semibold text-slate-900">
                      {topGainer ? topGainer.symbol : "-"}
                    </div>
                  </div>
                  {topGainer && <TrendBadge value={topGainer.pnl_percent} />}
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-xs text-slate-500 mb-0.5">{labels.dashboard.topLoser}</div>
                    <div className="font-display font-semibold text-slate-900">
                      {topLoser ? topLoser.symbol : "-"}
                    </div>
                  </div>
                  {topLoser && <TrendBadge value={topLoser.pnl_percent} />}
                </div>
                <div className="grid grid-cols-2 gap-3 pt-2 border-t border-slate-100">
                  <div className="min-w-0 overflow-hidden">
                    <div className="text-xs text-slate-500 mb-0.5">{labels.summary.totalValue}</div>
                    <div className="font-mono font-semibold text-accent-cyan">
                      <AnimatedNumber value={data.total_value} formatter={formatCurrency} className="block truncate" title={formatCurrency(data.total_value)} />
                    </div>
                  </div>
                  <div className="min-w-0 overflow-hidden">
                    <div className="text-xs text-slate-500 mb-0.5">{labels.summary.stableValue}</div>
                    <div className="font-mono font-semibold text-accent-violet">
                      <AnimatedNumber value={data.stable_value || 0} formatter={formatCurrency} className="block truncate" title={formatCurrency(data.stable_value || 0)} />
                    </div>
                  </div>
                </div>
              </div>
            )}
          </FintechCard>

          <FintechCard delay={0.2}>
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-accent-violet/10 text-accent-violet">
                  <Scale className="w-4 h-4" />
                </div>
                <h3 className="card-title">{labels.dashboard.rebalance}</h3>
              </div>
              <SectionLink to="/rebalance">{labels.dashboard.viewAll}</SectionLink>
            </div>
            {isLoading ? (
              <div className="space-y-2">
                <Skeleton className="h-12" />
                <Skeleton className="h-12" />
              </div>
            ) : (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-xs text-slate-500 mb-0.5">{labels.dashboard.biggestDrift}</div>
                    <div className="font-display font-semibold text-slate-900">
                      {biggestDrift
                        ? labels.assetTypes[biggestDrift.type as keyof typeof labels.assetTypes] ?? biggestDrift.type
                        : labels.dashboard.noSuggestions}
                    </div>
                  </div>
                  {biggestDrift && (
                    <TrendBadge value={biggestDrift.current_percent - biggestDrift.target_percent} />
                  )}
                </div>
                {(rebalance.data?.suggestions || []).length > 0 && (
                  <div className="space-y-2">
                    <div className="flex justify-between text-xs text-slate-500">
                      <span>{labels.dashboard.currentAllocation}</span>
                    </div>
                    <div className="relative h-3 bg-slate-100 rounded-full overflow-hidden">
                      <div className="absolute inset-0 flex rounded-full overflow-hidden">
                        {(rebalance.data?.suggestions || []).map((s: any) => (
                          <div
                            key={s.type}
                            className="h-full"
                            style={{
                              width: `${Math.max(0, Math.min(100, s.current_percent))}%`,
                              backgroundColor: TYPE_COLORS[s.type] || "var(--text-muted)",
                            }}
                            title={`${labels.assetTypes[s.type as keyof typeof labels.assetTypes] ?? s.type}\nHiện tại: ${formatCurrency(s.current_value)} (${formatPercent(s.current_percent)})\nMục tiêu: ${formatCurrency(s.target_value)} (${formatPercent(s.target_percent)})`}
                          />
                        ))}
                      </div>
                    </div>
                    <div className="flex justify-between text-xs text-slate-500">
                      <span>{labels.rebalance.targetAllocation}</span>
                    </div>
                    <div className="relative h-3 bg-slate-100 rounded-full overflow-hidden">
                      <div className="absolute inset-0 flex rounded-full overflow-hidden">
                        {(rebalance.data?.suggestions || []).map((s: any) => (
                          <div
                            key={s.type}
                            className="h-full opacity-70"
                            style={{
                              width: `${Math.max(0, Math.min(100, s.target_percent))}%`,
                              backgroundColor: TYPE_COLORS[s.type] || "var(--text-muted)",
                            }}
                            title={`${labels.assetTypes[s.type as keyof typeof labels.assetTypes] ?? s.type}\nMục tiêu: ${formatCurrency(s.target_value)} (${formatPercent(s.target_percent)})`}
                          />
                        ))}
                      </div>
                    </div>
                    <div className="flex flex-wrap gap-1.5 pt-1">
                      {(rebalance.data?.suggestions || []).map((s: any) => (
                        <div key={s.type} className="flex items-center gap-1 text-[10px] text-slate-500">
                          <span
                            className="inline-block w-2 h-2 rounded-full"
                            style={{ backgroundColor: TYPE_COLORS[s.type] || "#64748b" }}
                          />
                          <span>{labels.assetTypes[s.type as keyof typeof labels.assetTypes] ?? s.type} {formatPercent(s.current_percent)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                <div className="pt-2 border-t border-slate-100">
                  <div className="text-xs text-slate-500">
                    {labels.rebalance.estimatedValue}:{" "}
                    <span className="value-text font-semibold text-slate-900">
                      <AnimatedNumber value={rebalance.data?.total_value || 0} formatter={formatCurrency} className="block truncate" title={formatCurrency(rebalance.data?.total_value || 0)} />
                    </span>
                  </div>
                </div>
              </div>
            )}
          </FintechCard>

          <FintechCard delay={0.25}>
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-accent-blue/10 text-accent-blue">
                  <LineChartIcon className="w-4 h-4" />
                </div>
                <h3 className="card-title">{labels.dashboard.market}</h3>
              </div>
              <SectionLink to="/market">{labels.dashboard.viewAll}</SectionLink>
            </div>
            <div className="flex bg-slate-100 rounded-lg p-0.5 mb-3">
              {(["STOCK", "FUND", "GOLD"] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setMarketTab(tab)}
                  className={`text-xs px-2 py-1 rounded-md transition-colors ${marketTab === tab
                    ? "bg-white text-slate-800 shadow-sm"
                    : "text-slate-500 hover:text-slate-700"
                    }`}
                >
                  {labels.assetTypes[tab]}
                </button>
              ))}
            </div>
            {marketQuotes.isLoading || goldFx.isLoading ? (
              <div className="space-y-2">
                <Skeleton className="h-10" count={3} />
              </div>
            ) : marketTab === "GOLD" ? (
              goldListItems.length > 0 ? (
                <div className="space-y-2">
                  {goldListItems.slice(0, 5).map((g: any) => (
                    <div key={g.source} className="flex items-center justify-between">
                      <div className="flex items-center gap-2 min-w-0 overflow-hidden">
                        <div className="font-display font-semibold text-slate-900 text-sm whitespace-nowrap">{g.source}</div>
                        <Value value={g.buy} formatter={formatCurrency} className="value-text text-xs text-slate-500" />
                      </div>
                      <div className="flex items-center gap-2">
                        <MiniSparkline
                          data={
                            g.buy > 0 && g.change_percent != null
                              ? generatePriceSparkline(g.buy, g.change_percent)
                              : [g.buy, g.buy]
                          }
                          color="amber"
                          width={80}
                          height={24}
                          showArea={false}
                        />
                        <Value value={g.sell} formatter={formatCurrency} className="value-text text-xs font-semibold text-slate-700" />
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <EmptyState
                  icon={<LineChartIcon className="w-6 h-6" />}
                  title="Khám phá giá vàng"
                  description="Bảng giá vàng sẽ hiển thị tại đây khi có dữ liệu. Thử cập nhật giá để làm mới."
                  actionLabel={labels.dashboard.refreshPrices}
                  onAction={() => refresh.mutate()}
                  delay={0}
                />
              )
            ) : marketListItems.length > 0 ? (
              <div className="space-y-2">
                {marketListItems.map((q: any) => (
                  <div key={q.symbol} className="flex items-center justify-between">
                    <div className="flex items-center gap-2 min-w-0 overflow-hidden">
                      <div className="font-display font-semibold text-slate-900 text-sm whitespace-nowrap">
                        {q.symbol}
                        {q.isPortfolio && (
                          <span className="ml-1.5 inline-flex rounded-full px-1.5 py-0.5 text-[10px] font-semibold bg-accent-blue/10 text-accent-blue ring-1 ring-inset ring-accent-blue/20">
                            {labels.dashboard.portfolio}
                          </span>
                        )}
                      </div>
                      <Value value={q.price} formatter={formatCurrency} className="value-text text-xs text-slate-500" />
                    </div>
                    <div className="flex items-center gap-2">
                      <MiniSparkline
                        data={
                          q.price > 0 && q.change_percent != null
                            ? generatePriceSparkline(q.price, q.change_percent)
                            : [q.price, q.price]
                        }
                        color={q.change_percent >= 0 ? "emerald" : "rose"}
                        width={80}
                        height={24}
                        showArea={false}
                      />
                      <TrendBadge value={q.change_percent} />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                icon={<LineChartIcon className="w-6 h-6" />}
                title="Theo dõi thị trường"
                description="Thêm tài sản vào danh mục hoặc cập nhật giá để xem biến động cổ phiếu và quỹ tại đây."
                actionLabel={labels.dashboard.refreshPrices}
                onAction={() => refresh.mutate()}
                delay={0}
              />
            )}
          </FintechCard>

          <FintechCard delay={0.3}>
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-accent-amber/10 text-accent-amber">
                  <Newspaper className="w-4 h-4" />
                </div>
                <h3 className="card-title">{labels.dashboard.news}</h3>
                {unreadAlerts > 0 && (
                  <Link
                    to="/news"
                    className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full bg-accent-amber/10 text-accent-amber text-[10px] font-medium"
                  >
                    <Bell className="w-3 h-3" />
                    {unreadAlerts}
                  </Link>
                )}
              </div>
              <div className="flex items-center gap-2">
                <div className="flex bg-slate-100 rounded-lg p-0.5">
                  {(["vn", "global"] as const).map((r) => (
                    <button
                      key={r}
                      onClick={() => setNewsRegion(r)}
                      className={`text-[10px] px-2 py-1 rounded-md transition-colors ${newsRegion === r
                        ? "bg-white text-slate-800 shadow-sm"
                        : "text-slate-500 hover:text-slate-700"
                        }`}
                    >
                      {r === "vn" ? "VN" : "Global"}
                    </button>
                  ))}
                </div>
                <SectionLink to="/news">{labels.dashboard.viewAll}</SectionLink>
              </div>
            </div>
            {dailyBrief.isLoading ? (
              <div className="space-y-2">
                <Skeleton className="h-12" />
                <Skeleton className="h-12" />
                <Skeleton className="h-12" />
              </div>
            ) : (
              <div className="space-y-1">
                {(dailyBrief.data?.top_articles || []).slice(0, 4).map((article: Article, idx: number) => {
                  const tags = article.tags
                    ?.split(",")
                    .map((t) => t.trim())
                    .filter(Boolean) ?? [];
                  return (
                    <a
                      key={article.id}
                      href={article.url}
                      target="_blank"
                      rel="noreferrer"
                      className={`block py-2 group ${idx > 0 ? "border-t border-slate-100" : ""}`}
                    >
                      <div className="text-sm font-medium text-slate-900 truncate group-hover:text-accent-blue transition-colors">
                        {article.title}
                      </div>
                      <div className="flex flex-wrap items-center gap-2 mt-1 text-xs">
                        <span className="text-slate-400">{formatRelativeTime(article.published_at)}</span>
                        {article.source_name && (
                          <span className="px-1.5 py-0.5 rounded-md bg-slate-100 text-slate-600 font-medium">
                            {article.source_name}
                          </span>
                        )}
                        {tags[0] && (
                          <span className="px-1.5 py-0.5 rounded-md bg-accent-blue/10 text-accent-blue font-medium">
                            {tags[0]}
                          </span>
                        )}
                      </div>
                    </a>
                  );
                })}
                {(dailyBrief.data?.top_articles || []).length === 0 && (
                  <EmptyState
                    icon={<Newspaper className="w-6 h-6" />}
                    title="Tin tức sẽ sớm xuất hiện"
                    description="Chưa có tóm tắt tin tức hôm nay. Thêm tài sản hoặc mã vào danh mục để nhận tin cá nhân hóa."
                    actionLabel={labels.dashboard.news}
                    onAction={() => { window.location.hash = "/news"; }}
                    delay={0}
                  />
                )}
              </div>
            )}
          </FintechCard>

          <FintechCard delay={0.35}>
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-accent-rose/10 text-accent-rose">
                  <GitCompare className="w-4 h-4" />
                </div>
                <h3 className="card-title">{labels.dashboard.compare}</h3>
              </div>
              <SectionLink to="/compare">{labels.dashboard.viewAll}</SectionLink>
            </div>
            <div className="flex items-center gap-2 mb-3">
              <select
                value={compareA}
                onChange={(e) => setCompareA(e.target.value)}
                className="input-fintech text-xs flex-1"
              >
                <option value="">{labels.compare.searchPlaceholder}</option>
                {(compareSymbolsList.data || []).map((s) => (
                  <option key={s.symbol} value={s.symbol}>
                    {s.symbol} - {s.name}
                  </option>
                ))}
              </select>
              <span className="text-xs text-slate-400">vs</span>
              <select
                value={compareB}
                onChange={(e) => setCompareB(e.target.value)}
                className="input-fintech text-xs flex-1"
              >
                <option value="">{labels.compare.searchPlaceholder}</option>
                {(compareSymbolsList.data || []).map((s) => (
                  <option key={s.symbol} value={s.symbol}>
                    {s.symbol} - {s.name}
                  </option>
                ))}
              </select>
            </div>
            {compareA && compareB ? (
              compareHistoryA.isLoading || compareHistoryB.isLoading ? (
                <Skeleton className="h-48" />
              ) : compareChartData.length > 1 ? (
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-xs text-slate-500">
                    <span className="font-medium text-slate-700">{labels.compare.normalizedChart}</span>
                    <span className="text-[10px]">Chỉ số hóa 100 = ngày đầu</span>
                  </div>
                  <div className="h-48">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={compareChartData} margin={{ top: 28, right: 8, bottom: 8, left: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--fintech-border)" />
                        <XAxis
                          dataKey="date"
                          tick={{ fill: "var(--text-muted)", fontSize: 10 }}
                          axisLine={false}
                          tickLine={false}
                          interval="preserveStartEnd"
                          minTickGap={24}
                        />
                        <YAxis
                          tick={{ fill: "var(--text-muted)", fontSize: 10 }}
                          axisLine={false}
                          tickLine={false}
                          width={40}
                          tickFormatter={(v) => `${v.toFixed(0)}`}
                        />
                        <Tooltip
                          contentStyle={chartTooltipStyle}
                          formatter={(v: number, name: string) => [
                            v.toFixed(2),
                            name === "a" ? compareA : compareB,
                          ]}
                          labelFormatter={(label) => `Ngày ${label}`}
                        />
                        <Legend
                          verticalAlign="top"
                          align="right"
                          iconType="plainline"
                          wrapperStyle={{ top: 0, right: 0, fontSize: 11, color: "var(--text-muted)" }}
                        />
                        <Line
                          type="monotone"
                          dataKey="a"
                          stroke={theme.chartColors[0]}
                          strokeWidth={2.5}
                          dot={false}
                          activeDot={{ r: 4, strokeWidth: 2, stroke: "var(--text-inverse)" }}
                          connectNulls
                          name={compareA}
                        />
                        <Line
                          type="monotone"
                          dataKey="b"
                          stroke={theme.chartColors[1]}
                          strokeWidth={2.5}
                          dot={false}
                          activeDot={{ r: 4, strokeWidth: 2, stroke: "var(--text-inverse)" }}
                          connectNulls
                          name={compareB}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              ) : (
                <div className="h-48 flex items-center justify-center text-xs text-slate-500">
                  {labels.compare.noData}
                </div>
              )
            ) : (
              <div className="h-48 flex items-center justify-center text-xs text-slate-500">
                {labels.compare.searchPlaceholder}
              </div>
            )}
          </FintechCard>

          <FintechCard delay={0.4}>
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-accent-cyan/10 text-accent-cyan">
                  <Activity className="w-4 h-4" />
                </div>
                <h3 className="card-title">{labels.analytics.riskMetrics}</h3>
              </div>
              <SectionLink to="/analytics">{labels.dashboard.viewAll}</SectionLink>
            </div>
            {isLoading || risk.isLoading ? (
              <div className="space-y-2">
                <Skeleton className="h-10" />
                <Skeleton className="h-10" />
              </div>
            ) : (
              <div className="space-y-3">
                <div className="grid grid-cols-3 gap-2">
                  <div className="text-center p-2 rounded-lg bg-slate-50">
                    <div className="text-[10px] text-slate-500 mb-0.5">{labels.analytics.volatility}</div>
                    <div className="font-mono font-semibold text-sm text-slate-900">
                      {risk.data?.volatility != null ? formatPercent(risk.data.volatility) : "—"}
                    </div>
                  </div>
                  <div className="text-center p-2 rounded-lg bg-slate-50">
                    <div className="text-[10px] text-slate-500 mb-0.5">{labels.analytics.sharpeRatio}</div>
                    <div className="font-mono font-semibold text-sm text-slate-900">
                      {risk.data?.sharpe_ratio != null ? risk.data.sharpe_ratio.toFixed(2) : "—"}
                    </div>
                  </div>
                  <div className="text-center p-2 rounded-lg bg-slate-50">
                    <div className="text-[10px] text-slate-500 mb-0.5">{labels.analytics.maxDrawdown}</div>
                    <div className={`font-mono font-semibold text-sm ${(risk.data?.max_drawdown_percent || 0) < 0 ? "text-accent-rose" : "text-slate-900"}`}>
                      {risk.data?.max_drawdown_percent != null ? formatPercent(risk.data.max_drawdown_percent) : "—"}
                    </div>
                  </div>
                </div>
                <div className="space-y-2 pt-2 border-t border-slate-100">
                  <div className="text-xs text-slate-500">{labels.dashboard.topMovers}</div>
                  {(analytics.data?.top_performers || []).slice(0, 2).map((item: any) => (
                    <div key={item.symbol} className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className="font-display font-semibold text-slate-900 text-sm">{item.symbol}</div>
                        <span className="text-[10px] text-slate-500">{labels.dashboard.topGainer}</span>
                      </div>
                      <TrendBadge value={item.pnl_percent} />
                    </div>
                  ))}
                  {(analytics.data?.bottom_performers || []).slice(0, 2).map((item: any) => (
                    <div key={item.symbol} className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className="font-display font-semibold text-slate-900 text-sm">{item.symbol}</div>
                        <span className="text-[10px] text-slate-500">{labels.dashboard.topLoser}</span>
                      </div>
                      <TrendBadge value={item.pnl_percent} />
                    </div>
                  ))}
                  {(analytics.data?.top_performers || []).length === 0 && (analytics.data?.bottom_performers || []).length === 0 && (
                    <EmptyState
                      icon={<Activity className="w-6 h-6" />}
                      title="Biến động sẽ hiển thị tại đây"
                      description="Thêm giao dịch để xem top sinh lời và top thua lỗ của danh mục."
                      actionLabel={labels.dashboard.addTransaction}
                      onAction={() => { window.location.hash = "/transactions"; }}
                      delay={0}
                    />
                  )}
                </div>
              </div>
            )}
          </FintechCard>

          <QuickAddCard />

          <MobileQrCard />

        </div>
      </div>

      <FintechCard delay={0.45}>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
          <h3 className="card-title inline-flex items-center">
            {labels.dashboard.portfolioTrend}
            <span className="ml-1.5 text-xs text-slate-400">(%)</span>
            <InfoTooltip content={labels.tooltips.portfolioTrend} />
          </h3>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5 text-xs text-slate-500">
              <span className="w-2 h-2 rounded-full bg-accent-blue" />
              {labels.dashboard.portfolioTrend}
            </div>
            <div className="flex items-center gap-1.5 text-xs text-slate-500">
              <span className="w-2 h-2 rounded-full bg-accent-amber" />
              {labels.dashboard.benchmark}
            </div>
            <TrendBadge value={data.total_pnl_percent} />
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2 mb-3">
          {[
            { key: "1W", label: "1 tuần" },
            { key: "1M", label: "1 tháng" },
            { key: "3M", label: "3 tháng" },
            { key: "6M", label: "6 tháng" },
            { key: "1Y", label: "1 năm" },
            { key: "ALL", label: "Tất cả" },
            { key: "CUSTOM", label: "Tùy chỉnh" },
          ].map((p) => (
            <button
              key={p.key}
              onClick={() => setTrendPeriod(p.key as typeof trendPeriod)}
              className={`text-xs px-2 py-1 rounded-md transition-colors ${trendPeriod === p.key
                ? "bg-accent-blue text-white"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                }`}
            >
              {p.label}
            </button>
          ))}
          {trendPeriod === "CUSTOM" && (
            <div className="flex items-center gap-2 ml-1">
              <input
                type="date"
                className="input-fintech text-xs py-1"
                value={trendCustomStart}
                onChange={(e) => setTrendCustomStart(e.target.value)}
              />
              <span className="text-xs text-slate-400">→</span>
              <input
                type="date"
                className="input-fintech text-xs py-1"
                value={trendCustomEnd}
                onChange={(e) => setTrendCustomEnd(e.target.value)}
              />
            </div>
          )}
        </div>
        <div className="h-64">
          {trendHistory.isLoading ? (
            <Skeleton className="h-full" />
          ) : hasTrendData ? (
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={displayTrendData}>
                <defs>
                  <linearGradient id="trendGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="var(--accent-blue)" stopOpacity={0.35} />
                    <stop offset="100%" stopColor="var(--accent-blue)" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--fintech-border)" />
                <XAxis dataKey="date" tick={{ fill: "var(--text-muted)", fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis
                  tickFormatter={(v) => formatPercent(v)}
                  tick={{ fill: "var(--text-muted)", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                  width={80}
                />
                <Tooltip
                  contentStyle={chartTooltipStyle}
                  formatter={(v: number, name: string) => [
                    formatPercent(v),
                    name === "portfolio" ? labels.dashboard.portfolioTrend : labels.dashboard.benchmark,
                  ]}
                />
                <Area
                  type="monotone"
                  dataKey="portfolio"
                  stroke="var(--accent-blue)"
                  strokeWidth={2.5}
                  fill="url(#trendGradient)"
                  dot={false}
                  activeDot={{ r: 5, fill: "var(--accent-cyan)", stroke: "var(--text-inverse)", strokeWidth: 2 }}
                  animationDuration={1500}
                />
                <Line
                  type="monotone"
                  dataKey="benchmark"
                  stroke="var(--accent-amber)"
                  strokeWidth={2}
                  dot={false}
                  connectNulls
                  animationDuration={1500}
                />
              </ComposedChart>
            </ResponsiveContainer>
          ) : trendHistory.isFetching ? (
            <Skeleton className="h-full" />
          ) : (
            <div className="h-full flex items-center justify-center">
              <EmptyState
                icon={<TrendingUp className="w-6 h-6" />}
                title="Bắt đầu xây dựng danh mục"
                description={labels.dashboard.addAssetsHint}
                actionLabel={labels.assets.addAsset}
                onAction={() => { window.location.hash = "/assets"; }}
                delay={0}
              />
            </div>
          )}
        </div>
      </FintechCard>
    </div>
  );
}
