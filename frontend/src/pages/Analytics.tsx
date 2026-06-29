import { useQuery } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { Link } from "react-router-dom";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import API from "../api/client";
import { ErrorMessage } from "../components/ErrorMessage";
import { EmptyState } from "../components/EmptyState";
import { InfoTooltip } from "../components/InfoTooltip";
import { AnimatedNumber } from "../components/ui/AnimatedNumber";
import { FintechCard } from "../components/ui/FintechCard";
import { MiniSparkline } from "../components/ui/MiniSparkline";
import { SectionHeader } from "../components/ui/SectionHeader";
import { TrendBadge } from "../components/ui/TrendBadge";
import { labels } from "../i18n/vi";
import { chartTooltipStyle, formatCurrency } from "../lib/utils";


export function Analytics() {
  const analytics = useQuery({
    queryKey: ["analytics"],
    queryFn: async () => (await API.get("/analytics/")).data,
  });

  const risk = useQuery({
    queryKey: ["analytics-risk"],
    queryFn: async () => (await API.get("/analytics/risk")).data,
  });

  const data = analytics.data;

  const totalPnl = data?.type_returns?.reduce((sum: number, t: any) => sum + (t.pnl || 0), 0) || 0;
  const totalCost = data?.type_returns?.reduce((sum: number, t: any) => sum + (t.cost || 0), 0) || 0;
  const totalPnlPercent = totalCost ? (totalPnl / totalCost) * 100 : 0;

  return (
    <div className="space-y-6">
      {analytics.isError && <ErrorMessage error={analytics.error} retry={() => analytics.refetch()} />}
      {risk.isError && <ErrorMessage error={risk.error} retry={() => risk.refetch()} />}
      <SectionHeader title={labels.analytics.title} />

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
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
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
                <InfoTooltip content={labels.tooltips.pnl} />
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

          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <FintechCard delay={0.42}>
              <div className="card-title mb-1 inline-flex items-center">
                {labels.analytics.volatility}
                <InfoTooltip content={labels.tooltips.analyticsRiskMetrics} />
              </div>
              <div className="metric-value text-accent-blue">
                {risk.data?.volatility != null ? `${(risk.data.volatility * 100).toFixed(2)}%` : "—"}
              </div>
            </FintechCard>
            <FintechCard delay={0.44}>
              <div className="card-title mb-1 inline-flex items-center">
                {labels.analytics.sharpeRatio}
                <InfoTooltip content={labels.tooltips.analyticsRiskMetrics} />
              </div>
              <div className="metric-value text-accent-violet">
                {risk.data?.sharpe_ratio != null ? risk.data.sharpe_ratio.toFixed(2) : "—"}
              </div>
            </FintechCard>
            <FintechCard delay={0.46}>
              <div className="card-title mb-1 inline-flex items-center">
                {labels.analytics.maxDrawdown}
                <InfoTooltip content={labels.tooltips.analyticsRiskMetrics} />
              </div>
              <div className="metric-value text-accent-rose">
                {risk.data?.max_drawdown_percent != null ? `${risk.data.max_drawdown_percent.toFixed(2)}%` : "—"}
              </div>
            </FintechCard>
            <FintechCard delay={0.48}>
              <div className="card-title mb-1 inline-flex items-center">
                {labels.analytics.beta}
                <InfoTooltip content={labels.tooltips.analyticsRiskMetrics} />
              </div>
              <div className="metric-value text-accent-cyan">
                {risk.data?.beta != null ? risk.data.beta.toFixed(2) : "—"}
              </div>
            </FintechCard>
          </div>

          <FintechCard delay={0.45}>
            <h3 className="card-title mb-4 inline-flex items-center">
              {labels.analytics.monthlyPnl} — {labels.analytics.detail}
              <InfoTooltip content={labels.tooltips.pnl} />
            </h3>
            {data.monthly_pnl.length > 0 ? (
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
            ) : (
              <div className="text-slate-500">{labels.analytics.empty}</div>
            )}
          </FintechCard>
        </>
      )}
    </div>
  );
}
