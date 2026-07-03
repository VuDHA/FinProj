import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowRight,
  Bell,
  Flame,
  Landmark,
  LineChart,
  Newspaper,
  PiggyBank,
  Plus,
  Receipt,
  RefreshCw,
  Scale,
  TrendingUp,
} from "lucide-react";
import { Link } from "react-router-dom";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Cell,
  Line,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import API from "../api/client";
import { getAlerts, getDailyBrief, getTrending } from "../api/news";
import { ErrorMessage } from "../components/ErrorMessage";
import { EmptyState } from "../components/EmptyState";
import { InfoTooltip } from "../components/InfoTooltip";
import { PriceAlertsSection } from "../components/PriceAlertsSection";
import { SummaryCards } from "../components/SummaryCards";
import { AnimatedNumber } from "../components/ui/AnimatedNumber";
import { FintechCard } from "../components/ui/FintechCard";
import { SectionHeader } from "../components/ui/SectionHeader";
import { Skeleton } from "../components/ui/Skeleton";
import { TrendBadge } from "../components/ui/TrendBadge";
import { useToast } from "../contexts/ToastContext";
import { labels } from "../i18n/vi";
import { chartTooltipStyle, formatCurrency } from "../lib/utils";

const COLORS = ["#22D3EE", "#34D399", "#FBBF24", "#FB7185", "#8B5CF6", "#3B82F6"];
const WATCHLIST_SYMBOLS =
  "VCB,VHM,VIC,FPT,GAS,HPG,MBB,MSN,MWG,PLX,SSI,TCB,VIB,VPB,E1VFVN30,FUEVFVND,FUESSVFL";

function Sparkline({ data, color }: { data: number[]; color: string }) {
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const width = 80;
  const height = 24;
  const points = data
    .map((v, i) => {
      const x = (i / (data.length - 1 || 1)) * width;
      const y = height - ((v - min) / range) * height;
      return `${x},${y}`;
    })
    .join(" ");
  return (
    <svg width={width} height={height} className="overflow-visible">
      <polyline
        fill="none"
        stroke={color}
        strokeWidth={2}
        points={points}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx={width} cy={height - ((data[data.length - 1] - min) / range) * height} r={2.5} fill={color} />
    </svg>
  );
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

export function Dashboard() {
  const qc = useQueryClient();
  const { showToast } = useToast();

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

  const benchmark = useQuery({
    queryKey: ["portfolio-benchmark"],
    queryFn: async () => {
      const end = new Date().toISOString().split("T")[0];
      const start = new Date(Date.now() - 180 * 24 * 60 * 60 * 1000).toISOString().split("T")[0];
      const { data } = await API.get("/prices/benchmark/VNINDEX", { params: { start, end } });
      return data as Array<{ date: string; portfolio_value: number; benchmark_value: number }>;
    },
    enabled: history.data && history.data.length > 1,
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

  const marketWatchlist = useQuery({
    queryKey: ["market-watchlist"],
    queryFn: async () => {
      const { data } = await API.get("/prices/quote", { params: { symbols: WATCHLIST_SYMBOLS } });
      return data as Array<{ symbol: string; price: number; change: number; change_percent: number; date: string }>;
    },
  });

  const goldFx = useQuery({
    queryKey: ["gold-fx"],
    queryFn: async () => (await API.get("/gold-fx/")).data,
  });

  const alerts = useQuery({
    queryKey: ["news-alerts-unread"],
    queryFn: async () => getAlerts(true),
  });

  const dailyBrief = useQuery({
    queryKey: ["news-daily-brief"],
    queryFn: async () => getDailyBrief(24, "vn"),
  });

  const trending = useQuery({
    queryKey: ["news-trending"],
    queryFn: async () => getTrending(24),
  });

  const refresh = useMutation({
    mutationFn: () => API.post("/prices/refresh-all"),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["portfolio"] });
      qc.invalidateQueries({ queryKey: ["portfolio-history"] });
      qc.invalidateQueries({ queryKey: ["portfolio-benchmark"] });
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

  const data = portfolio.data || {
    total_value: 0,
    total_cost: 0,
    total_pnl: 0,
    total_pnl_percent: 0,
    items: [],
  };

  const allocation = data.items.reduce((acc: Record<string, number>, item: any) => {
    acc[item.type] = (acc[item.type] || 0) + item.current_value;
    return acc;
  }, {});

  const pieData = Object.entries(allocation).map(([name, value]) => ({
    name: labels.assetTypes[name as keyof typeof labels.assetTypes] ?? name,
    value,
  }));

  const trendMap = new Map<string, { label: string; portfolio?: number; benchmark?: number }>();
  for (const point of history.data || []) {
    const date = new Date(point.date);
    const label = date.toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit" });
    const iso = point.date;
    trendMap.set(iso, { ...(trendMap.get(iso) || { label }), label, portfolio: point.value });
  }
  for (const point of benchmark.data || []) {
    const date = new Date(point.date);
    const label = date.toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit" });
    const iso = point.date;
    trendMap.set(iso, { ...(trendMap.get(iso) || { label }), label, benchmark: point.benchmark_value });
  }
  const trendData = Array.from(trendMap.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([_, { label, portfolio, benchmark }]) => ({ date: label, portfolio, benchmark }));

  const topMovers = (marketWatchlist.data || [])
    .filter((q) => q.change_percent != null)
    .sort((a, b) => Math.abs(b.change_percent) - Math.abs(a.change_percent))
    .slice(0, 3);

  const topGainer = analytics.data?.top_performers?.[0];
  const topLoser = analytics.data?.bottom_performers?.[0];
  const totalIncome = analytics.data?.total_income || 0;
  const maxDrawdown = risk.data?.max_drawdown_percent;

  const biggestDrift = (rebalance.data?.suggestions || [])
    .map((s: any) => ({ ...s, drift: Math.abs(s.current_percent - s.target_percent) }))
    .sort((a: any, b: any) => b.drift - a.drift)[0];

  const topTrade = rebalance.data?.trades?.[0];

  const unreadAlerts = (alerts.data || []).filter((a) => !a.is_read).length;
  const briefArticle = dailyBrief.data?.top_articles?.[0];
  const topTrending = trending.data?.symbols?.[0];

  const goldRates = (goldFx.data?.gold || []) as Array<{ source: string; buy: number; sell: number; updated_at?: string }>;
  const fxRates = (goldFx.data?.fx || []) as Array<{ currency: string; buy: number; sell: number }>;
  const goldRate = goldRates[0];
  const fxRate = fxRates[0];

  const isLoading =
    portfolio.isLoading ||
    history.isLoading ||
    analytics.isLoading ||
    risk.isLoading ||
    rebalance.isLoading ||
    marketWatchlist.isLoading;

  return (
    <div className="space-y-6">
      {portfolio.isError && <ErrorMessage error={portfolio.error} retry={() => portfolio.refetch()} />}
      {history.isError && <ErrorMessage error={history.error} retry={() => history.refetch()} />}
      {benchmark.isError && <ErrorMessage error={benchmark.error} retry={() => benchmark.refetch()} />}
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
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Skeleton className="h-28" count={3} />
        </div>
      ) : (
        <SummaryCards {...data} history={history.data} />
      )}

      <FintechCard delay={0.1} className="!p-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 px-2">
            {labels.dashboard.quickActions}
          </span>
          <InfoTooltip content={labels.tooltips.dashboardQuickActions} />
          <div className="w-px h-4 bg-slate-200 mx-1 hidden sm:block" />
          <Link to="/assets" className="btn-secondary py-1.5 px-3 text-xs">
            <Plus className="w-3.5 h-3.5" />
            {labels.dashboard.addAsset}
          </Link>
          <Link to="/transactions" className="btn-secondary py-1.5 px-3 text-xs">
            <Receipt className="w-3.5 h-3.5" />
            {labels.dashboard.addTransaction}
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
            <LineChart className="w-3.5 h-3.5" />
            {labels.market.title}
          </Link>
        </div>
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
                  <div>
                    <div className="text-xs text-slate-500 mb-0.5">{labels.dashboard.totalIncome}</div>
                    <div className="font-mono font-semibold text-accent-emerald">
                      <AnimatedNumber value={totalIncome} formatter={formatCurrency} />
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-500 mb-0.5">{labels.dashboard.maxDrawdown}</div>
                    <div className="font-mono font-semibold text-accent-rose">
                      {maxDrawdown != null ? `${maxDrawdown.toFixed(2)}%` : "—"}
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
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-xs text-slate-500 mb-0.5">{labels.dashboard.topSuggestion}</div>
                    <div className="font-display font-semibold text-slate-900">
                      {topTrade
                        ? `${topTrade.action === "BUY" ? labels.rebalance.buy : labels.rebalance.sell} ${topTrade.symbol}`
                        : labels.dashboard.noSuggestions}
                    </div>
                  </div>
                  {topTrade && (
                    <span className={topTrade.action === "BUY" ? "badge-gain" : "badge-loss"}>
                      {formatCurrency(topTrade.estimated_value)}
                    </span>
                  )}
                </div>
                <div className="pt-2 border-t border-slate-100">
                  <div className="text-xs text-slate-500">
                    {labels.rebalance.estimatedValue}:{" "}
                    <span className="font-mono font-semibold text-slate-900">
                      <AnimatedNumber value={rebalance.data?.total_value || 0} formatter={formatCurrency} />
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
                  <LineChart className="w-4 h-4" />
                </div>
                <h3 className="card-title">{labels.dashboard.market}</h3>
              </div>
              <SectionLink to="/market">{labels.dashboard.viewAll}</SectionLink>
            </div>
            {marketWatchlist.isLoading ? (
              <div className="space-y-2">
                <Skeleton className="h-10" count={3} />
              </div>
            ) : topMovers.length > 0 ? (
              <div className="space-y-2">
                {topMovers.map((q) => (
                  <div key={q.symbol} className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="font-display font-semibold text-slate-900 text-sm">{q.symbol}</div>
                      <div className="text-xs text-slate-500">{formatCurrency(q.price)}</div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Sparkline
                        data={[
                          q.price * (1 - q.change_percent / 100),
                          q.price,
                        ]}
                        color={q.change_percent >= 0 ? "#34D399" : "#FB7185"}
                      />
                      <TrendBadge value={q.change_percent} />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-xs text-slate-500 py-4">{labels.dashboard.noMovers}</div>
            )}
          </FintechCard>

          <FintechCard delay={0.3}>
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-accent-amber/10 text-accent-amber">
                  <Newspaper className="w-4 h-4" />
                </div>
                <h3 className="card-title">{labels.dashboard.news}</h3>
              </div>
              <SectionLink to="/news">{labels.dashboard.viewAll}</SectionLink>
            </div>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Bell className="w-4 h-4 text-slate-500" />
                  <span className="text-sm text-slate-700">{labels.dashboard.unreadAlerts}</span>
                  <InfoTooltip content={labels.tooltips.dashboardUnreadAlerts} />
                </div>
                <span
                  className={`text-sm font-mono font-semibold ${unreadAlerts > 0 ? "text-accent-amber" : "text-slate-500"}`}
                >
                  {unreadAlerts}
                </span>
              </div>
              <div className="pt-2 border-t border-slate-100">
                <div className="text-xs text-slate-500 mb-1">{labels.dashboard.dailyBrief}</div>
                <div className="text-sm font-medium text-slate-900 line-clamp-2">
                  {briefArticle ? briefArticle.title : labels.dashboard.noBrief}
                </div>
              </div>
              <div className="flex items-center gap-2 text-xs text-slate-500">
                <Flame className="w-3.5 h-3.5" />
                {labels.dashboard.trending}:{" "}
                <span className="font-medium text-slate-700">
                  {topTrending ? `${topTrending.symbol} (${topTrending.mentions})` : labels.dashboard.noTrending}
                </span>
              </div>
            </div>
          </FintechCard>

          <FintechCard delay={0.35}>
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-accent-cyan/10 text-accent-cyan">
                  <Landmark className="w-4 h-4" />
                </div>
                <h3 className="card-title">{labels.dashboard.goldFx}</h3>
              </div>
              <SectionLink to="/market">{labels.dashboard.viewAll}</SectionLink>
            </div>
            {goldFx.isLoading ? (
              <div className="space-y-2">
                <Skeleton className="h-12" />
                <Skeleton className="h-12" />
              </div>
            ) : (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-xs text-slate-500 mb-0.5">
                      {labels.dashboard.gold} {goldRate ? `(${goldRate.source})` : ""}
                    </div>
                    <div className="font-mono font-semibold text-slate-900">
                      {goldRate ? `${formatCurrency(goldRate.buy)} / ${formatCurrency(goldRate.sell)}` : "—"}
                    </div>
                  </div>
                  {goldRate && (
                    <span className="text-xs text-slate-400">
                      {goldRate.updated_at ? new Date(goldRate.updated_at).toLocaleDateString("vi-VN") : ""}
                    </span>
                  )}
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-xs text-slate-500 mb-0.5">
                      {labels.dashboard.fx} {fxRate ? `(${fxRate.currency})` : ""}
                    </div>
                    <div className="font-mono font-semibold text-slate-900">
                      {fxRate ? `${formatCurrency(fxRate.buy)} / ${formatCurrency(fxRate.sell)}` : "—"}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </FintechCard>

          <FintechCard delay={0.4}>
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-accent-rose/10 text-accent-rose">
                  <PiggyBank className="w-4 h-4" />
                </div>
                <h3 className="card-title">{labels.dashboard.allocation}</h3>
              </div>
              <SectionLink to="/assets">{labels.dashboard.viewAll}</SectionLink>
            </div>
            <div className="h-40">
              {pieData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={pieData}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      innerRadius={40}
                      outerRadius={60}
                      paddingAngle={3}
                      stroke="none"
                    >
                      {pieData.map((_, i) => (
                        <Cell key={`cell-${i}`} fill={COLORS[i % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip contentStyle={chartTooltipStyle} formatter={(v: number) => formatCurrency(v)} />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex items-center justify-center text-xs text-slate-500">
                  {labels.dashboard.empty}
                </div>
              )}
            </div>
            <div className="flex flex-wrap gap-2">
              {pieData.map((entry, i) => (
                <div key={entry.name} className="flex items-center gap-1.5 text-xs text-slate-500">
                  <span className="w-2 h-2 rounded-full" style={{ backgroundColor: COLORS[i % COLORS.length] }} />
                  {entry.name}
                </div>
              ))}
            </div>
          </FintechCard>
        </div>
      </div>

      <FintechCard delay={0.45}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="card-title inline-flex items-center">
            {labels.dashboard.portfolioTrend}
            <InfoTooltip content={labels.tooltips.portfolioTrend} />
          </h3>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5 text-xs text-slate-500">
              <span className="w-2 h-2 rounded-full bg-blue-500" />
              {labels.dashboard.portfolioTrend}
            </div>
            <div className="flex items-center gap-1.5 text-xs text-slate-500">
              <span className="w-2 h-2 rounded-full bg-amber-400" />
              {labels.dashboard.benchmark}
            </div>
            <TrendBadge value={data.total_pnl_percent} />
          </div>
        </div>
        <div className="h-64">
          {history.isLoading ? (
            <Skeleton className="h-full" />
          ) : trendData.length > 1 ? (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trendData}>
                <defs>
                  <linearGradient id="trendGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#3B82F6" stopOpacity={0.35} />
                    <stop offset="100%" stopColor="#3B82F6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.1)" />
                <XAxis dataKey="date" tick={{ fill: "#64748b", fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis
                  tickFormatter={(v) => formatCurrency(v)}
                  tick={{ fill: "#64748b", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                  width={80}
                />
                <Tooltip
                  contentStyle={chartTooltipStyle}
                  formatter={(v: number, name: string) => [
                    formatCurrency(v),
                    name === "portfolio" ? labels.dashboard.portfolioTrend : labels.dashboard.benchmark,
                  ]}
                />
                <Area
                  type="monotone"
                  dataKey="portfolio"
                  stroke="#3B82F6"
                  strokeWidth={2.5}
                  fill="url(#trendGradient)"
                  dot={false}
                  activeDot={{ r: 5, fill: "#22D3EE", stroke: "#ffffff", strokeWidth: 2 }}
                  animationDuration={1500}
                />
                <Line
                  type="monotone"
                  dataKey="benchmark"
                  stroke="#FBBF24"
                  strokeWidth={2}
                  dot={false}
                  animationDuration={1500}
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex items-center justify-center">
              <EmptyState
                title={labels.dashboard.empty}
                description={labels.dashboard.addAssetsHint}
                action={
                  <Link to="/assets" className="btn-primary">
                    <Plus className="w-4 h-4" />
                    {labels.assets.addAsset}
                  </Link>
                }
              />
            </div>
          )}
        </div>
      </FintechCard>
    </div>
  );
}
