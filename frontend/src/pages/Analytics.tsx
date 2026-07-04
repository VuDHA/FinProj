import { useEffect, useMemo } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bot, Landmark, Plus, RefreshCw, Search, ChevronLeft, ChevronRight } from "lucide-react";
import { usePersistentState } from "../hooks/usePersistentState";
import { Link } from "react-router-dom";
import {
  Area,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import API from "../api/client";
import { getAnalyticsInsight } from "../api/ai";
import { AiGenerateButton } from "../components/AiGenerateButton";
import { AiInsightCard } from "../components/AiInsightCard";
import { ErrorMessage } from "../components/ErrorMessage";
import { EmptyState } from "../components/EmptyState";
import { InfoTooltip } from "../components/InfoTooltip";
import { AnimatedNumber } from "../components/ui/AnimatedNumber";
import { FintechCard } from "../components/ui/FintechCard";
import { MiniSparkline } from "../components/ui/MiniSparkline";
import { SectionHeader } from "../components/ui/SectionHeader";
import { Skeleton } from "../components/ui/Skeleton";
import { TrendBadge } from "../components/ui/TrendBadge";
import { useToast } from "../contexts/ToastContext";
import { useAiInsight } from "../hooks/useAiInsight";
import { labels } from "../i18n/vi";
import { chartTooltipStyle, formatCurrency, formatNumber } from "../lib/utils";

const PIE_COLORS = ["#34D399", "#60A5FA", "#FBBF24", "#A78BFA", "#FB7185", "#22D3EE", "#F472B6"];

const typeColor: Record<string, string> = {
  STOCK: "bg-accent-blue/10 text-accent-blue ring-accent-blue/20",
  FUND: "bg-accent-violet/10 text-accent-violet ring-accent-violet/20",
  ETF: "bg-accent-cyan/10 text-accent-cyan ring-accent-cyan/20",
  GOLD: "bg-accent-amber/10 text-accent-amber ring-accent-amber/20",
  CRYPTO: "bg-accent-emerald/10 text-accent-emerald ring-accent-emerald/20",
  REAL_ESTATE: "bg-accent-rose/10 text-accent-rose ring-accent-rose/20",
  LIFE_INSURANCE: "bg-accent-indigo/10 text-accent-indigo ring-accent-indigo/20",
};

function typeBadgeClass(type: string): string {
  if (typeColor[type]) return typeColor[type];
  const palette = [
    "bg-accent-blue/10 text-accent-blue ring-accent-blue/20",
    "bg-accent-violet/10 text-accent-violet ring-accent-violet/20",
    "bg-accent-cyan/10 text-accent-cyan ring-accent-cyan/20",
    "bg-accent-amber/10 text-accent-amber ring-accent-amber/20",
    "bg-accent-emerald/10 text-accent-emerald ring-accent-emerald/20",
    "bg-accent-rose/10 text-accent-rose ring-accent-rose/20",
    "bg-accent-indigo/10 text-accent-indigo ring-accent-indigo/20",
  ];
  let hash = 0;
  for (let i = 0; i < type.length; i++) hash = type.charCodeAt(i) + ((hash << 5) - hash);
  return palette[Math.abs(hash) % palette.length];
}

export function Analytics() {
  const [filterType, setFilterType] = usePersistentState<"month" | "quarter" | "year" | "custom">("analytics.filterType", "month");
  const [customStart, setCustomStart] = usePersistentState<string>("analytics.customStart", "");
  const [customEnd, setCustomEnd] = usePersistentState<string>("analytics.customEnd", "");
  const [chartMode, setChartMode] = usePersistentState<"total" | "type">("analytics.chartMode", "total");
  const [assetSearch, setAssetSearch] = usePersistentState("analytics.assetSearch", "");
  const [assetTypeFilter, setAssetTypeFilter] = usePersistentState<string>("analytics.assetTypeFilter", "ALL");
  const [assetPage, setAssetPage] = usePersistentState("analytics.assetPage", 1);
  const ASSETS_PER_PAGE = 10;
  const qc = useQueryClient();
  const { showToast } = useToast();

  const analytics = useQuery({
    queryKey: ["analytics", filterType, customStart, customEnd],
    queryFn: async () => {
      const params: Record<string, string> = { filter_type: filterType };
      if (filterType === "custom" && customStart && customEnd) {
        params.start_date = customStart;
        params.end_date = customEnd;
      }
      return (await API.get("/analytics/", { params })).data;
    },
  });

  const risk = useQuery({
    queryKey: ["analytics-risk"],
    queryFn: async () => (await API.get("/analytics/risk")).data,
  });

  const portfolio = useQuery({
    queryKey: ["portfolio"],
    queryFn: async () =>
      (await API.get("/portfolio/")).data as {
        total_value: number;
        total_cost: number;
        total_pnl: number;
        total_pnl_percent: number;
        items: Array<{
          asset_id: number;
          symbol: string;
          name: string;
          type: string;
          quantity: number;
          avg_cost: number;
          latest_price: number;
          current_value: number;
          cost: number;
          pnl: number;
          pnl_percent: number;
        }>;
      },
  });

  const assetTypes = useQuery<{ [key: string]: { marketPrice: boolean } }>({
    queryKey: ["asset-types"],
    queryFn: async () => (await API.get("/settings/asset-types")).data.types,
  });

  const isMarketType = (type: string) =>
    assetTypes.data?.[type]?.marketPrice !== false;

  const data = analytics.data;

  const history = useQuery({
    queryKey: ["portfolio-history", data?.period_start, data?.period_end],
    queryFn: async () => {
      const { data: hist } = await API.get("/portfolio/history", {
        params: { start: data?.period_start, end: data?.period_end },
      });
      return hist as Array<{ date: string; value: number; cost: number; by_type: Record<string, number> }>;
    },
    enabled: !!data?.period_start && !!data?.period_end,
  });

  const refresh = useMutation({
    mutationFn: async () => {
      await API.post("/prices/refresh-all");
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["analytics", filterType, customStart, customEnd] });
      qc.invalidateQueries({ queryKey: ["analytics-risk"] });
      qc.invalidateQueries({
        queryKey: ["portfolio-history", data?.period_start, data?.period_end],
      });
      qc.invalidateQueries({ queryKey: ["portfolio"] });
      showToast("Đã cập nhật dữ liệu phân tích", "success");
    },
    onError: (error: any) => {
      showToast(error?.response?.data?.detail || "Không thể cập nhật dữ liệu", "error");
    },
  });

  const analyticsInsight = useAiInsight({
    taskName: "analytics_insight",
    fetcher: () =>
      getAnalyticsInsight(
        filterType,
        filterType === "custom" ? customStart : undefined,
        filterType === "custom" ? customEnd : undefined
      ),
  });

  const totalPnl = data?.type_returns?.reduce((sum: number, t: any) => sum + (t.pnl || 0), 0) || 0;
  const totalCost = data?.type_returns?.reduce((sum: number, t: any) => sum + (t.cost || 0), 0) || 0;
  const totalPnlPercent = totalCost ? (totalPnl / totalCost) * 100 : 0;

  const typeKeys =
    chartMode === "type" && history.data
      ? Array.from(new Set(history.data.flatMap((d) => Object.keys(d.by_type || {}))))
      : [];

  const chartData = history.data?.map((d) => ({ ...d, ...(d.by_type || {}) })) || [];

  const assetTypeOptions = useMemo(() => {
    const types = new Set(portfolio.data?.items.map((i) => i.type) || []);
    return Array.from(types).sort();
  }, [portfolio.data]);

  const filteredAssets = useMemo(() => {
    const q = assetSearch.trim().toLowerCase();
    return (portfolio.data?.items || []).filter((item) => {
      const matchesSearch =
        !q ||
        item.symbol.toLowerCase().includes(q) ||
        item.name.toLowerCase().includes(q);
      const matchesType = assetTypeFilter === "ALL" || item.type === assetTypeFilter;
      return matchesSearch && matchesType;
    });
  }, [portfolio.data, assetSearch, assetTypeFilter]);

  useEffect(() => {
    setAssetPage(1);
  }, [assetSearch, assetTypeFilter]);

  const assetPageCount = Math.max(1, Math.ceil(filteredAssets.length / ASSETS_PER_PAGE));
  const safeAssetPage = Math.min(assetPage, assetPageCount);
  const pagedAssets = filteredAssets.slice(
    (safeAssetPage - 1) * ASSETS_PER_PAGE,
    safeAssetPage * ASSETS_PER_PAGE
  );

  return (
    <div className="space-y-6">
      {analytics.isError && <ErrorMessage error={analytics.error} retry={() => analytics.refetch()} />}
      {risk.isError && <ErrorMessage error={risk.error} retry={() => risk.refetch()} />}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <SectionHeader title={labels.analytics.title} />
          <InfoTooltip content={labels.tooltips.analyticsFilter} />
          {data && (
            <span className="text-xs text-slate-500 bg-slate-100 px-2 py-1 rounded-md">
              {data.period_start} → {data.period_end}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-2 flex-wrap">
            <div className="flex bg-slate-100 rounded-lg p-0.5">
              {(["month", "quarter", "year", "custom"] as const).map((f) => (
                <button
                  key={f}
                  onClick={() => setFilterType(f)}
                  className={`text-xs px-3 py-1.5 rounded-md transition-colors ${filterType === f
                    ? "bg-white text-slate-800 shadow-sm"
                    : "text-slate-500 hover:text-slate-700"
                    }`}
                >
                  {(labels.analytics as any)[f]}
                </button>
              ))}
            </div>
            {filterType === "custom" && (
              <div className="flex items-center gap-2">
                <input
                  type="date"
                  className="input-fintech text-sm py-1.5"
                  value={customStart}
                  onChange={(e) => setCustomStart(e.target.value)}
                />
                <span className="text-slate-500">→</span>
                <input
                  type="date"
                  className="input-fintech text-sm py-1.5"
                  value={customEnd}
                  onChange={(e) => setCustomEnd(e.target.value)}
                />
              </div>
            )}
          </div>
          <button
            onClick={() => refresh.mutate()}
            disabled={refresh.isPending || analytics.isFetching}
            className="btn-secondary inline-flex items-center gap-1.5 text-sm px-3 py-1.5 disabled:opacity-60"
          >
            <RefreshCw className={`w-4 h-4 ${refresh.isPending || analytics.isFetching ? "animate-spin" : ""}`} />
            {labels.analytics.refresh}
          </button>
        </div>
      </div>

      {!data && <div className="text-slate-500">{labels.common.loading}</div>}

      {data && data.type_returns.length === 0 && (
        <EmptyState
          title={labels.analytics.empty}
          description={labels.dashboard.addAssetsHint}
          action={
            <Link to="/assets" className="btn-primary">
              <Plus className="w-4 h-4" />
              {labels.assets.addAsset}
            </Link>
          }
        />
      )}

      {data && data.type_returns.length > 0 && (
        <>
          <FintechCard delay={0.04}>
            <div className="flex items-center justify-between mb-3">
              <h3 className="card-title inline-flex items-center gap-2">
                <Bot className="w-4 h-4 text-indigo-500" />
                Phân tích AI
              </h3>
              <AiGenerateButton
                label="Phân tích"
                onClick={() => analyticsInsight.generate()}
                loading={analyticsInsight.loading}
              />
            </div>
            <AiInsightCard
              data={analyticsInsight.data}
              loading={analyticsInsight.loading}
              error={analyticsInsight.error}
              onClose={analyticsInsight.clear}
            />
          </FintechCard>

          <FintechCard delay={0.05}>
            <div className="flex items-center justify-between mb-3">
              <h3 className="card-title inline-flex items-center">
                {labels.analytics.totalPortfolioValue}
                <InfoTooltip content={labels.tooltips.analyticsTotalValue} />
              </h3>
              <div className="flex items-center gap-3">
                <div className="flex bg-slate-100 rounded-lg p-0.5">
                  <button
                    onClick={() => setChartMode("total")}
                    className={`text-xs px-2 py-1 rounded-md transition-colors ${chartMode === "total"
                      ? "bg-white text-slate-800 shadow-sm"
                      : "text-slate-500 hover:text-slate-700"
                      }`}
                  >
                    {labels.analytics.asTotal}
                  </button>
                  <button
                    onClick={() => setChartMode("type")}
                    className={`text-xs px-2 py-1 rounded-md transition-colors ${chartMode === "type"
                      ? "bg-white text-slate-800 shadow-sm"
                      : "text-slate-500 hover:text-slate-700"
                      }`}
                  >
                    {labels.analytics.byAssetType}
                  </button>
                </div>
                <span className="text-xs text-slate-500">
                  {data.period_start} → {data.period_end}
                </span>
              </div>
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 h-72">
              <div className="lg:col-span-3 h-72">
                {history.isLoading ? (
                  <Skeleton className="h-full" />
                ) : history.data && history.data.length > 1 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={chartData}>
                      <defs>
                        <linearGradient id="portfolioValueGradient" x1="0" y1="0" x2="0" y2="1">
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
                          chartMode === "total" ? labels.analytics.totalPortfolioValue : name,
                        ]}
                      />
                      {chartMode === "total" ? (
                        <Area
                          type="monotone"
                          dataKey="value"
                          stroke="#3B82F6"
                          strokeWidth={2.5}
                          fill="url(#portfolioValueGradient)"
                          dot={false}
                          activeDot={{ r: 5, fill: "#22D3EE", stroke: "#ffffff", strokeWidth: 2 }}
                          animationDuration={1200}
                        />
                      ) : (
                        typeKeys.map((type, i) => (
                          <Line
                            key={type}
                            type="monotone"
                            dataKey={type}
                            stroke={PIE_COLORS[i % PIE_COLORS.length]}
                            strokeWidth={2}
                            dot={false}
                            activeDot={{ r: 4 }}
                            animationDuration={1200}
                          />
                        ))
                      )}
                      <Legend
                        formatter={(value: string) =>
                          value === "value" ? labels.analytics.totalPortfolioValue : value
                        }
                      />
                    </ComposedChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-slate-500">
                    {labels.analytics.empty}
                  </div>
                )}
              </div>
              <div className="lg:col-span-1 h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={data.portfolio_value_by_type || []}
                      dataKey="value"
                      nameKey="type"
                      cx="50%"
                      cy="50%"
                      innerRadius={40}
                      outerRadius={70}
                      paddingAngle={2}
                    >
                      {(data.portfolio_value_by_type || []).map((_entry: any, i: number) => (
                        <Cell key={`cell-${i}`} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip contentStyle={chartTooltipStyle} formatter={(v: number) => formatCurrency(v)} />
                    <Legend layout="vertical" verticalAlign="middle" align="right" />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>
          </FintechCard>

          <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
            <FintechCard delay={0.1}>
              <div className="card-title mb-1 inline-flex items-center">
                {labels.analytics.totalPnl}
                <InfoTooltip content={labels.tooltips.pnl} />
              </div>
              <div className={`metric-value ${totalPnl >= 0 ? "text-accent-emerald" : "text-accent-rose"}`}>
                <AnimatedNumber value={totalPnl} formatter={formatCurrency} />
              </div>
              <div className="mt-2">
                <TrendBadge value={totalPnlPercent} />
              </div>
            </FintechCard>
            {data.stable_value > 0 && (
              <FintechCard delay={0.12}>
                <div className="card-title mb-1 inline-flex items-center">
                  <Landmark className="w-4 h-4 mr-1.5 text-accent-violet" />
                  {labels.summary.stableValue}
                  <InfoTooltip content={labels.tooltips.stableValue} />
                </div>
                <div className="metric-value text-accent-violet">
                  <AnimatedNumber value={data.stable_value} formatter={formatCurrency} />
                </div>
                {/* <div className="mt-2 text-xs text-slate-500">
                  {labels.summary.totalValue}: {formatCurrency(data.total_value)}
                </div> */}
              </FintechCard>
            )}
            <FintechCard delay={0.15}>
              <div className="card-title mb-1 inline-flex items-center">
                {labels.analytics.topGainer}
                <InfoTooltip content={labels.tooltips.analyticsTopGainer} />
              </div>
              <div className="metric-value text-accent-cyan">
                {data.top_performers[0]?.symbol ?? "-"}
              </div>
              <div className="mt-2">
                {data.top_performers[0] ? (
                  <TrendBadge value={data.top_performers[0].pnl_percent} />
                ) : (
                  <span className="text-xs text-slate-500">-</span>
                )}
              </div>
            </FintechCard>
            <FintechCard delay={0.2}>
              <div className="card-title mb-1 inline-flex items-center">
                {labels.analytics.topLoser}
                <InfoTooltip content={labels.tooltips.analyticsTopLoser} />
              </div>
              <div className="metric-value text-accent-rose">
                {data.bottom_performers[0]?.symbol ?? "-"}
              </div>
              <div className="mt-2">
                {data.bottom_performers[0] ? (
                  <TrendBadge value={data.bottom_performers[0].pnl_percent} />
                ) : (
                  <span className="text-xs text-slate-500">-</span>
                )}
              </div>
            </FintechCard>
            <FintechCard delay={0.22}>
              <div className="card-title mb-1 inline-flex items-center">
                {labels.analytics.totalIncome}
                <InfoTooltip content={labels.tooltips.analyticsTotalIncome} />
              </div>
              <div className="metric-value text-accent-emerald">
                <AnimatedNumber value={data.total_income || 0} formatter={formatCurrency} />
              </div>
              <div className="mt-2 text-xs text-slate-500">
                {(data.income || []).map((inc: any) => `${inc.type}: ${formatCurrency(inc.total)}`).join(" | ")}
              </div>
            </FintechCard>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <FintechCard delay={0.25}>
              <h3 className="card-title mb-4 inline-flex items-center">
                {labels.analytics.topPerformers}
                <InfoTooltip content={labels.tooltips.analyticsTopGainer} />
              </h3>
              {data.top_performers.length > 0 ? (
                <div className="overflow-x-auto scrollbar-thin">
                  <table className="table-fintech">
                    <thead>
                      <tr>
                        <th className="text-left">{labels.dashboard.symbol}</th>
                        <th className="text-right">{labels.analytics.pnl}</th>
                        <th className="text-right">{labels.analytics.return}</th>
                        <th className="text-right">{labels.analytics.trend}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.top_performers.map((item: any) => (
                        <tr key={item.asset_id}>
                          <td>
                            <div className="font-display font-semibold text-slate-900">{item.symbol}</div>
                            <span className="text-xs text-slate-500">{item.name}</span>
                          </td>
                          <td className="text-right font-mono text-slate-700">{formatCurrency(item.pnl)}</td>
                          <td className="text-right">
                            <TrendBadge value={item.pnl_percent} />
                          </td>
                          <td className="text-right">
                            <div className="flex justify-end">
                              <MiniSparkline
                                data={Array.from({ length: 16 }, (_, i) => item.pnl * (0.6 + i * 0.04 + Math.random() * 0.1))}
                                color="emerald"
                                width={80}
                                height={24}
                              />
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="text-slate-500">{labels.analytics.empty}</div>
              )}
            </FintechCard>

            <FintechCard delay={0.3}>
              <h3 className="card-title mb-4 inline-flex items-center">
                {labels.analytics.bottomPerformers}
                <InfoTooltip content={labels.tooltips.analyticsTopLoser} />
              </h3>
              {data.bottom_performers.length > 0 ? (
                <div className="overflow-x-auto scrollbar-thin">
                  <table className="table-fintech">
                    <thead>
                      <tr>
                        <th className="text-left">{labels.dashboard.symbol}</th>
                        <th className="text-right">{labels.analytics.pnl}</th>
                        <th className="text-right">{labels.analytics.return}</th>
                        <th className="text-right">{labels.analytics.trend}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.bottom_performers.map((item: any) => (
                        <tr key={item.asset_id}>
                          <td>
                            <div className="font-display font-semibold text-slate-900">{item.symbol}</div>
                            <span className="text-xs text-slate-500">{item.name}</span>
                          </td>
                          <td className="text-right font-mono text-slate-700">{formatCurrency(item.pnl)}</td>
                          <td className="text-right">
                            <TrendBadge value={item.pnl_percent} />
                          </td>
                          <td className="text-right">
                            <div className="flex justify-end">
                              <MiniSparkline
                                data={Array.from({ length: 16 }, (_, i) => Math.abs(item.pnl) * (0.8 - i * 0.03 + Math.random() * 0.1))}
                                color="rose"
                                width={80}
                                height={24}
                              />
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="text-slate-500">{labels.analytics.empty}</div>
              )}
            </FintechCard>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <FintechCard delay={0.35}>
              <h3 className="card-title mb-4 inline-flex items-center">
                {labels.analytics.returnByType}
                <InfoTooltip content={labels.tooltips.allocationByType} />
              </h3>
              {data.type_returns.length > 0 ? (
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={data.type_returns}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.1)" vertical={false} />
                      <XAxis dataKey="type" tick={{ fill: "#64748b", fontSize: 12 }} axisLine={false} tickLine={false} />
                      <YAxis tickFormatter={(v: number) => formatCurrency(v)} tick={{ fill: "#64748b", fontSize: 11 }} axisLine={false} tickLine={false} />
                      <Tooltip contentStyle={chartTooltipStyle} formatter={(v: number) => formatCurrency(v)} />
                      <Bar dataKey="pnl" radius={[6, 6, 0, 0]}>
                        {data.type_returns.map((entry: any, i: number) => (
                          <Cell key={i} fill={entry.pnl >= 0 ? "#34D399" : "#FB7185"} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="text-slate-500">{labels.analytics.empty}</div>
              )}
            </FintechCard>

            <FintechCard delay={0.4}>
              <h3 className="card-title mb-4 inline-flex items-center">
                {labels.analytics.monthlyPnl}
                <InfoTooltip content={labels.tooltips.monthlyPnl} />
              </h3>
              {data.monthly_pnl.length > 0 ? (
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={data.monthly_pnl}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.1)" vertical={false} />
                      <XAxis dataKey="month" tick={{ fill: "#64748b", fontSize: 12 }} axisLine={false} tickLine={false} />
                      <YAxis tickFormatter={(v: number) => formatCurrency(v)} tick={{ fill: "#64748b", fontSize: 11 }} axisLine={false} tickLine={false} width={80} />
                      <Tooltip contentStyle={chartTooltipStyle} formatter={(v: number) => formatCurrency(v)} />
                      <Line
                        type="monotone"
                        dataKey="pnl"
                        stroke="#22D3EE"
                        strokeWidth={2.5}
                        dot={{ r: 3, fill: "#22D3EE", stroke: "#ffffff", strokeWidth: 2 }}
                        activeDot={{ r: 5, fill: "#FBBF24" }}
                        animationDuration={1200}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="text-slate-500">{labels.analytics.empty}</div>
              )}
            </FintechCard>
          </div>

          <FintechCard delay={0.32}>
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
              <h3 className="card-title inline-flex items-center">
                {labels.analytics.assetValueTable}
                <InfoTooltip content={labels.tooltips.allocationByType} />
              </h3>
              <div className="flex items-center gap-2 flex-wrap">
                <div className="relative w-full max-w-xs">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                  <input
                    type="text"
                    value={assetSearch}
                    onChange={(e) => setAssetSearch(e.target.value)}
                    placeholder={labels.analytics.searchPlaceholder}
                    className="input-fintech pl-9 w-full"
                  />
                </div>
                <select
                  value={assetTypeFilter}
                  onChange={(e) => setAssetTypeFilter(e.target.value)}
                  className="input-fintech text-sm"
                >
                  <option value="ALL">{labels.analytics.allTypes}</option>
                  {assetTypeOptions.map((t) => (
                    <option key={t} value={t}>
                      {labels.assetTypes[t as keyof typeof labels.assetTypes] || t}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            {portfolio.isLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-8" count={6} />
              </div>
            ) : (
              <>
                <div className="overflow-x-auto scrollbar-thin">
                  <table className="table-fintech">
                    <thead>
                      <tr>
                        <th className="text-left">{labels.dashboard.symbol}</th>
                        <th className="text-left">{labels.assets.name}</th>
                        <th className="text-left">{labels.assets.type}</th>
                        <th className="text-right">{labels.dashboard.quantity}</th>
                        <th className="text-right">{labels.dashboard.price}</th>
                        <th className="text-right">{labels.dashboard.value}</th>
                        <th className="text-right">{labels.analytics.cost}</th>
                        <th className="text-right">{labels.analytics.pnl}</th>
                        <th className="text-right">{labels.analytics.return}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {pagedAssets.map((item) => (
                        <tr key={item.asset_id}>
                          <td className="font-display font-semibold text-slate-900">{item.symbol}</td>
                          <td className="text-slate-700">{item.name}</td>
                          <td>
                            <span
                              className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${typeBadgeClass(
                                item.type
                              )}`}
                            >
                              {labels.assetTypes[item.type as keyof typeof labels.assetTypes] || item.type}
                            </span>
                          </td>
                          <td className="text-right font-mono">{formatNumber(item.quantity)}</td>
                          <td className="text-right font-mono">{formatCurrency(item.latest_price)}</td>
                          <td className="text-right font-mono">{formatCurrency(item.current_value)}</td>
                          <td className="text-right font-mono">{formatCurrency(item.cost)}</td>
                          <td
                            className={`text-right font-mono ${!isMarketType(item.type)
                              ? "text-slate-400"
                              : item.pnl >= 0
                                ? "text-accent-emerald"
                                : "text-accent-rose"
                              }`}
                          >
                            {isMarketType(item.type) ? formatCurrency(item.pnl) : "-"}
                          </td>
                          <td className="text-right">
                            {isMarketType(item.type) ? <TrendBadge value={item.pnl_percent} /> : <span className="text-slate-400">-</span>}
                          </td>
                        </tr>
                      ))}
                      {pagedAssets.length === 0 && (
                        <tr>
                          <td colSpan={9} className="px-4 py-8 text-center text-slate-500">
                            {labels.analytics.noAssets}
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
                <div className="flex items-center justify-between mt-4">
                  <span className="text-xs text-slate-500">
                    {filteredAssets.length} tài sản
                  </span>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setAssetPage((p) => Math.max(1, p - 1))}
                      disabled={safeAssetPage <= 1}
                      className="btn-secondary inline-flex items-center gap-1 text-xs px-2 py-1 disabled:opacity-50"
                    >
                      <ChevronLeft className="w-4 h-4" />
                      {labels.analytics.previous}
                    </button>
                    <span className="text-sm text-slate-700">
                      {labels.analytics.page} {safeAssetPage} / {assetPageCount}
                    </span>
                    <button
                      onClick={() => setAssetPage((p) => Math.min(assetPageCount, p + 1))}
                      disabled={safeAssetPage >= assetPageCount}
                      className="btn-secondary inline-flex items-center gap-1 text-xs px-2 py-1 disabled:opacity-50"
                    >
                      {labels.analytics.next}
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </>
            )}
          </FintechCard>

          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <FintechCard delay={0.42}>
              <div className="card-title mb-1 inline-flex items-center">
                {labels.analytics.volatility}
                <InfoTooltip content={labels.tooltips.analyticsVolatility} />
              </div>
              <div className="metric-value text-accent-blue">
                {risk.data?.volatility != null ? `${(risk.data.volatility * 100).toFixed(2)}%` : "—"}
              </div>
            </FintechCard>
            <FintechCard delay={0.44}>
              <div className="card-title mb-1 inline-flex items-center">
                {labels.analytics.sharpeRatio}
                <InfoTooltip content={labels.tooltips.analyticsSharpeRatio} />
              </div>
              <div className="metric-value text-accent-violet">
                {risk.data?.sharpe_ratio != null ? risk.data.sharpe_ratio.toFixed(2) : "—"}
              </div>
            </FintechCard>
            <FintechCard delay={0.46}>
              <div className="card-title mb-1 inline-flex items-center">
                {labels.analytics.maxDrawdown}
                <InfoTooltip content={labels.tooltips.analyticsMaxDrawdown} />
              </div>
              <div className="metric-value text-accent-rose">
                {risk.data?.max_drawdown_percent != null ? `${risk.data.max_drawdown_percent.toFixed(2)}%` : "—"}
              </div>
            </FintechCard>
            <FintechCard delay={0.48}>
              <div className="card-title mb-1 inline-flex items-center">
                {labels.analytics.beta}
                <InfoTooltip content={labels.tooltips.analyticsBeta} />
              </div>
              <div className="metric-value text-accent-cyan">
                {risk.data?.beta != null ? risk.data.beta.toFixed(2) : "—"}
              </div>
            </FintechCard>
          </div>

          <FintechCard delay={0.45}>
            <h3 className="card-title mb-4 inline-flex items-center">
              {labels.analytics.monthlyPnl} — {labels.analytics.detail}
              <InfoTooltip content={labels.tooltips.monthlyPnl} />
            </h3>
            {data.monthly_pnl.length > 0 ? (
              <>
                <div className="overflow-x-auto scrollbar-thin">
                  <table className="table-fintech">
                    <thead>
                      <tr>
                        <th className="text-left">{labels.analytics.month}</th>
                        <th className="text-right">{labels.analytics.startValue}</th>
                        <th className="text-right">{labels.analytics.endValue}</th>
                        <th className="text-right">{labels.analytics.pnl}</th>
                        <th className="text-right">{labels.analytics.return}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.monthly_pnl.map((item: any) => (
                        <tr key={item.month}>
                          <td className="font-display font-medium text-slate-900">{item.month}</td>
                          <td className="text-right font-mono">{formatCurrency(item.start_value)}</td>
                          <td className="text-right font-mono">{formatCurrency(item.end_value)}</td>
                          <td className={`text-right font-mono ${item.pnl >= 0 ? "text-accent-emerald" : "text-accent-rose"}`}>
                            {formatCurrency(item.pnl)}
                          </td>
                          <td className="text-right">
                            <TrendBadge value={item.pnl_percent} />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <p className="mt-3 text-xs text-slate-500">
                  Biến động giá thị trường có thể làm thay đổi giá trị danh mục ngay cả khi không có giao dịch.
                </p>
              </>
            ) : (
              <div className="text-slate-500">{labels.analytics.empty}</div>
            )}
          </FintechCard>
        </>
      )}
    </div>
  );
}
