import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCw, Plus } from "lucide-react";
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
import { ErrorMessage } from "../components/ErrorMessage";
import { EmptyState } from "../components/EmptyState";
import { InfoTooltip } from "../components/InfoTooltip";
import { SummaryCards } from "../components/SummaryCards";
import { FintechCard } from "../components/ui/FintechCard";
import { SectionHeader } from "../components/ui/SectionHeader";
import { Skeleton } from "../components/ui/Skeleton";
import { TrendBadge } from "../components/ui/TrendBadge";
import { useToast } from "../contexts/ToastContext";
import { labels } from "../i18n/vi";
import { chartTooltipStyle, formatCurrency, formatNumber, formatPercent } from "../lib/utils";

const COLORS = ["#22D3EE", "#34D399", "#FBBF24", "#FB7185", "#8B5CF6", "#3B82F6"];

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

  const refresh = useMutation({
    mutationFn: () => API.post("/prices/refresh-all"),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["portfolio"] });
      qc.invalidateQueries({ queryKey: ["portfolio-history"] });
      qc.invalidateQueries({ queryKey: ["portfolio-benchmark"] });
      qc.invalidateQueries({ queryKey: ["prices"] });
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

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <FintechCard className="lg:col-span-2" delay={0.2}>
          <div className="flex items-center justify-between mb-4">
            <h3 className="card-title inline-flex items-center">
              {labels.dashboard.holdings}
              <InfoTooltip content={labels.dashboard.addAssetsHint} />
            </h3>
            <span className="text-xs text-slate-500">{data.items.length} {labels.assets.symbol}</span>
          </div>
          {portfolio.isLoading ? (
            <div className="space-y-3">
              <Skeleton className="h-8" count={6} />
            </div>
          ) : data.items.length > 0 ? (
            <div className="overflow-x-auto scrollbar-thin">
              <table className="table-fintech">
                <thead>
                  <tr>
                    <th className="text-left">{labels.dashboard.symbol}</th>
                    <th className="text-right">{labels.dashboard.quantity}</th>
                    <th className="text-right">{labels.dashboard.price}</th>
                    <th className="text-right">{labels.dashboard.value}</th>
                    <th className="text-right">Giá vốn</th>
                    <th className="text-right">{labels.dashboard.pnl}</th>
                    <th className="text-right">Tỷ trọng</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((item: any) => {
                    const allocationPercent = data.total_value > 0 ? (item.current_value / data.total_value) * 100 : 0;
                    return (
                      <tr key={item.asset_id}>
                        <td>
                          <div className="font-display font-semibold text-slate-900">{item.symbol}</div>
                          <span className="text-xs text-slate-500">
                            {labels.assetTypes[item.type as keyof typeof labels.assetTypes] ?? item.type}
                          </span>
                        </td>
                        <td className="text-right font-mono">{formatNumber(item.quantity, 4)}</td>
                        <td className="text-right font-mono">{formatCurrency(item.latest_price)}</td>
                        <td className="text-right font-mono text-slate-900">{formatCurrency(item.current_value)}</td>
                        <td className="text-right font-mono text-slate-500">{formatCurrency(item.avg_cost)}</td>
                        <td className="text-right">
                          <div className="flex flex-col items-end gap-1">
                            <span className="font-mono text-xs text-slate-600">{formatCurrency(item.pnl)}</span>
                            <TrendBadge value={item.pnl_percent} />
                          </div>
                        </td>
                        <td className="text-right">
                          <div className="flex flex-col items-end gap-1">
                            <span className="font-mono text-xs text-slate-600">{formatPercent(allocationPercent)}</span>
                            <div className="h-1.5 w-16 rounded-full bg-slate-100 overflow-hidden">
                              <div
                                className="h-full rounded-full bg-accent-blue"
                                style={{ width: `${Math.min(allocationPercent, 100)}%` }}
                              />
                            </div>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
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
          )}
        </FintechCard>

        <FintechCard delay={0.3}>
          <h3 className="card-title mb-4 inline-flex items-center">
            {labels.dashboard.allocationByType}
            <InfoTooltip content={labels.tooltips.allocationByType} />
          </h3>
          <div className="h-64">
            {pieData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={pieData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={85}
                    paddingAngle={3}
                    stroke="none"
                  >
                    {pieData.map((_, i) => (
                      <Cell key={`cell-${i}`} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={chartTooltipStyle}
                    formatter={(v: number) => formatCurrency(v)}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-slate-500">
                {labels.dashboard.empty}
              </div>
            )}
          </div>
          <div className="flex flex-wrap gap-2 mt-2">
            {pieData.map((entry, i) => (
              <div key={entry.name} className="flex items-center gap-1.5 text-xs text-slate-500">
                <span
                  className="w-2 h-2 rounded-full"
                  style={{ backgroundColor: COLORS[i % COLORS.length] }}
                />
                {entry.name}
              </div>
            ))}
          </div>
        </FintechCard>
      </div>

      <FintechCard delay={0.4}>
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
        <div className="h-72">
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
