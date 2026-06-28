import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCw } from "lucide-react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import API from "../api/client";
import { ErrorMessage } from "../components/ErrorMessage";
import { SummaryCards } from "../components/SummaryCards";
import { FintechCard } from "../components/ui/FintechCard";
import { MiniSparkline } from "../components/ui/MiniSparkline";
import { SectionHeader } from "../components/ui/SectionHeader";
import { TrendBadge } from "../components/ui/TrendBadge";
import { labels } from "../i18n/vi";
import { chartTooltipStyle, formatCurrency, formatNumber } from "../lib/utils";

const COLORS = ["#22D3EE", "#34D399", "#FBBF24", "#FB7185", "#8B5CF6", "#3B82F6"];

function generateTrend(total: number) {
  const data: Array<{ date: string; value: number }> = [];
  const days = 30;
  const end = new Date();
  let value = total * 0.92;
  for (let i = days; i >= 0; i--) {
    const date = new Date(end);
    date.setDate(date.getDate() - i);
    value = value * (1 + (Math.random() - 0.45) * 0.015);
    data.push({
      date: date.toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit" }),
      value: Math.max(value, total * 0.5),
    });
  }
  data[data.length - 1].value = total;
  return data;
}

export function Dashboard() {
  const qc = useQueryClient();

  const portfolio = useQuery({
    queryKey: ["portfolio"],
    queryFn: async () => (await API.get("/portfolio/")).data,
  });

  const refresh = useMutation({
    mutationFn: () => API.post("/prices/refresh-all"),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["portfolio"] });
      qc.invalidateQueries({ queryKey: ["prices"] });
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

  const trendData = generateTrend(data.total_value || 1_000_000_000);

  const holdingSparkline = (item: any) => {
    const points = 18;
    const arr: number[] = [];
    let v = item.current_value * 0.88;
    for (let i = 0; i < points; i++) {
      v = v * (1 + (Math.random() - 0.48) * 0.04);
      arr.push(v);
    }
    arr[arr.length - 1] = item.current_value;
    return arr;
  };

  return (
    <div className="space-y-6">
      {portfolio.isError && <ErrorMessage error={portfolio.error} retry={() => portfolio.refetch()} />}
      {refresh.isError && <ErrorMessage error={refresh.error} retry={() => refresh.mutate()} />}

      <SectionHeader title={labels.dashboard.title}>
        <button
          onClick={() => refresh.mutate()}
          disabled={refresh.isPending}
          className="btn-primary"
        >
          <RefreshCw className={`w-4 h-4 ${refresh.isPending ? "animate-spin" : ""}`} />
          {refresh.isPending ? labels.dashboard.refreshing : labels.dashboard.refreshPrices}
        </button>
      </SectionHeader>

      <SummaryCards {...data} />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <FintechCard className="lg:col-span-2" delay={0.2}>
          <div className="flex items-center justify-between mb-4">
            <h3 className="card-title">{labels.dashboard.holdings}</h3>
            <span className="text-xs text-slate-500">{data.items.length} {labels.assets.symbol}</span>
          </div>
          {data.items.length > 0 ? (
            <div className="overflow-x-auto scrollbar-thin">
              <table className="table-fintech">
                <thead>
                  <tr>
                    <th className="text-left">{labels.dashboard.symbol}</th>
                    <th className="text-right">{labels.dashboard.quantity}</th>
                    <th className="text-right">{labels.dashboard.price}</th>
                    <th className="text-right">{labels.dashboard.value}</th>
                    <th className="text-right">{labels.dashboard.pnl}</th>
                    <th className="text-right">{labels.dashboard.trend}</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((item: any) => (
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
                      <td className="text-right">
                        <TrendBadge value={(item.pnl / (item.current_value - item.pnl || 1)) * 100} />
                      </td>
                      <td className="text-right">
                        <div className="flex justify-end">
                          <MiniSparkline
                            data={holdingSparkline(item)}
                            color={item.pnl >= 0 ? "emerald" : "rose"}
                            width={90}
                            height={28}
                          />
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-slate-500 py-8">{labels.dashboard.addAssetsHint}</div>
          )}
        </FintechCard>

        <FintechCard delay={0.3}>
          <h3 className="card-title mb-4">{labels.dashboard.allocationByType}</h3>
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
          <h3 className="card-title">{labels.dashboard.portfolioTrend}</h3>
          <TrendBadge value={data.total_pnl_percent} />
        </div>
        <div className="h-72">
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
                formatter={(v: number) => [formatCurrency(v), "Giá trị"]}
              />
              <Area
                type="monotone"
                dataKey="value"
                stroke="#3B82F6"
                strokeWidth={2.5}
                fill="url(#trendGradient)"
                dot={false}
                activeDot={{ r: 5, fill: "#22D3EE", stroke: "#ffffff", strokeWidth: 2 }}
                animationDuration={1500}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </FintechCard>
    </div>
  );
}
