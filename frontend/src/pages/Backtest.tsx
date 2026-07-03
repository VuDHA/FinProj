import { useMutation, useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Loader2, Play, Sparkles } from "lucide-react";
import { usePersistentState } from "../hooks/usePersistentState";
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
import { getBacktestStress } from "../api/ai";
import { ErrorMessage } from "../components/ErrorMessage";
import { InfoTooltip } from "../components/InfoTooltip";
import { AnimatedNumber } from "../components/ui/AnimatedNumber";
import { FintechCard } from "../components/ui/FintechCard";
import { SectionHeader } from "../components/ui/SectionHeader";
import { TrendBadge } from "../components/ui/TrendBadge";
import { useAiQueue } from "../contexts/AiQueueContext";
import { labels } from "../i18n/vi";
import { chartTooltipStyle, formatCurrency, formatPercent } from "../lib/utils";

const COLORS = ["#22D3EE", "#34D399", "#FBBF24", "#FB7185", "#8B5CF6", "#3B82F6"];

export function Backtest() {
  const today = new Date().toISOString().split("T")[0];
  const oneYearAgo = new Date(Date.now() - 365 * 24 * 60 * 60 * 1000).toISOString().split("T")[0];
  const { isBusy, runAi } = useAiQueue();

  type Position = { symbol: string; price: string; quantity: string; ratio: string };
  const [form, setForm] = usePersistentState<{
    strategy: string;
    start_date: string;
    end_date: string;
    initial_cash: string;
    rebalance_frequency: string;
    positions: Position[];
  }>("backtest.form", {
    strategy: "buy_and_hold",
    start_date: oneYearAgo,
    end_date: today,
    initial_cash: "100000000",
    rebalance_frequency: "monthly",
    positions: [],
  });
  const [prompt, setPrompt] = usePersistentState("backtest.prompt", "");
  const [stressPrompt, setStressPrompt] = usePersistentState("backtest.stressPrompt", "");
  const [promptMode, setPromptMode] = usePersistentState("backtest.promptMode", false);
  const [stressMode, setStressMode] = useState(false);
  const [result, setResult] = useState<any>(null);

  const assets = useQuery({
    queryKey: ["assets"],
    queryFn: async () => (await API.get("/assets/")).data,
  });

  const positionSymbols = useMemo(
    () =>
      form.positions
        .map((p) => p.symbol.trim().toUpperCase())
        .filter(Boolean),
    [form.positions]
  );

  const totalRatio = useMemo(
    () => form.positions.reduce((sum, p) => sum + (Number(p.ratio) || 0), 0),
    [form.positions]
  );

  const totalValue = useMemo(
    () =>
      form.positions.reduce(
        (sum, p) => sum + (Number(p.price) || 0) * (Number(p.quantity) || 0),
        0
      ),
    [form.positions]
  );

  const hasRatios = useMemo(
    () => form.positions.some((p) => Number(p.ratio) > 0),
    [form.positions]
  );

  const allocationPieData = useMemo(
    () =>
      form.positions.map((p) => {
        const name = p.symbol.trim().toUpperCase() || labels.backtest.asset;
        const value = hasRatios
          ? Number(p.ratio) || 0
          : (Number(p.price) || 0) * (Number(p.quantity) || 0);
        return { name, value };
      }),
    [form.positions, hasRatios]
  );

  const run = useMutation({
    mutationFn: () =>
      API.post("/backtest/", {
        strategy: form.strategy,
        start_date: form.start_date,
        end_date: form.end_date,
        initial_cash: Number(form.initial_cash),
        rebalance_frequency: form.rebalance_frequency,
        symbols: positionSymbols.length > 0 ? positionSymbols : undefined,
        positions: form.positions
          .filter((p) => p.symbol.trim() && Number(p.price) > 0 && Number(p.quantity) > 0)
          .map((p) => ({
            symbol: p.symbol.trim().toUpperCase(),
            price: Number(p.price),
            quantity: Number(p.quantity),
            ratio: p.ratio ? Number(p.ratio) : undefined,
          })),
      }),
    onSuccess: (response) => {
      setResult(response.data);
      setPromptMode(false);
    },
  });

  const aiRun = useMutation({
    mutationFn: () =>
      runAi("backtest_prompt", () =>
        API.post("/backtest/ai", { prompt }).then((res) => res.data)
      ),
    onSuccess: (data) => {
      setResult(data.result);
      setPromptMode(false);
      // Optionally populate the form so the user can see the extracted parameters
      setForm({
        strategy: data.request.strategy,
        start_date: data.request.start_date,
        end_date: data.request.end_date,
        initial_cash: String(data.request.initial_cash),
        rebalance_frequency: data.request.rebalance_frequency,
        positions: (data.request.positions || []).map((p: any) => ({
          symbol: p.symbol || "",
          price: String(p.price ?? ""),
          quantity: String(p.quantity ?? ""),
          ratio: p.ratio != null ? String(p.ratio) : "",
        })),
      });
    },
  });

  const aiStressRun = useMutation({
    mutationFn: () =>
      runAi("backtest_stress", () =>
        getBacktestStress({
          prompt: stressPrompt,
          base_request: {
            strategy: form.strategy,
            start_date: form.start_date,
            end_date: form.end_date,
            initial_cash: Number(form.initial_cash),
            rebalance_frequency: form.rebalance_frequency,
            symbols: positionSymbols.length > 0 ? positionSymbols : undefined,
            positions: form.positions
              .filter((p) => p.symbol.trim() && Number(p.price) > 0 && Number(p.quantity) > 0)
              .map((p) => ({
                symbol: p.symbol.trim().toUpperCase(),
                price: Number(p.price),
                quantity: Number(p.quantity),
                ratio: p.ratio ? Number(p.ratio) : undefined,
              })),
          },
        })
      ),
    onSuccess: (data) => {
      setResult(data.result);
      setForm({
        strategy: data.request.strategy,
        start_date: data.request.start_date,
        end_date: data.request.end_date,
        initial_cash: String(data.request.initial_cash),
        rebalance_frequency: data.request.rebalance_frequency,
        positions: (data.request.positions || []).map((p: any) => ({
          symbol: p.symbol || "",
          price: String(p.price ?? ""),
          quantity: String(p.quantity ?? ""),
          ratio: p.ratio != null ? String(p.ratio) : "",
        })),
      });
    },
  });

  const benchmark = useQuery({
    queryKey: ["backtest-benchmark", form.start_date, form.end_date],
    queryFn: async () => {
      const { data } = await API.get("/prices/benchmark-raw/VNINDEX", {
        params: { start: form.start_date, end: form.end_date },
      });
      return data as Array<{ date: string; price: number }>;
    },
    enabled: !!result,
  });

  const curveMap = new Map<string, { portfolio?: number; benchmark?: number }>();
  for (const point of result?.equity_curve || []) {
    curveMap.set(point.date, { ...(curveMap.get(point.date) || {}), portfolio: point.value });
  }
  const rawBenchmark = benchmark.data || [];
  const initialCash = Number(form.initial_cash) || 0;
  if (rawBenchmark.length > 0 && initialCash > 0) {
    const firstPrice = rawBenchmark[0].price;
    for (const point of rawBenchmark) {
      const normalized = firstPrice > 0 ? (point.price / firstPrice) * initialCash : 0;
      curveMap.set(point.date, { ...(curveMap.get(point.date) || {}), benchmark: normalized });
    }
  }
  const chartData = Array.from(curveMap.entries())
    .map(([date, values]) => ({ date, ...values }))
    .sort((a, b) => a.date.localeCompare(b.date));

  return (
    <div className="space-y-6">
      {assets.isError && <ErrorMessage error={assets.error} retry={() => assets.refetch()} />}
      {run.isError && <ErrorMessage error={run.error} retry={() => run.mutate()} />}
      {aiRun.isError && <ErrorMessage error={aiRun.error} retry={() => aiRun.mutate()} />}
      {aiStressRun.isError && <ErrorMessage error={aiStressRun.error} retry={() => aiStressRun.mutate()} />}
      {benchmark.isError && <ErrorMessage error={benchmark.error} retry={() => benchmark.refetch()} />}
      <SectionHeader title={labels.backtest.title} />

      <FintechCard delay={0.1}>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1.5 uppercase tracking-wider">
              {labels.backtest.strategy}
              <InfoTooltip content={labels.tooltips.backtestStrategy} />
            </label>
            <select
              className="input-fintech"
              value={form.strategy}
              onChange={(e) => setForm({ ...form, strategy: e.target.value })}
            >
              <option value="buy_and_hold">{labels.backtest.buyAndHold}</option>
              <option value="rebalancing">{labels.backtest.rebalancing}</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1.5 uppercase tracking-wider">
              {labels.backtest.startDate}
              <InfoTooltip content={labels.tooltips.backtestStartDate} />
            </label>
            <input
              type="date"
              className="input-fintech"
              value={form.start_date}
              onChange={(e) => setForm({ ...form, start_date: e.target.value })}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1.5 uppercase tracking-wider">
              {labels.backtest.endDate}
              <InfoTooltip content={labels.tooltips.backtestEndDate} />
            </label>
            <input
              type="date"
              className="input-fintech"
              value={form.end_date}
              onChange={(e) => setForm({ ...form, end_date: e.target.value })}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1.5 uppercase tracking-wider">
              {labels.backtest.initialCash}
              <InfoTooltip content={labels.tooltips.backtestInitialCash} />
            </label>
            <input
              type="number"
              className="input-fintech"
              value={form.initial_cash}
              onChange={(e) => setForm({ ...form, initial_cash: e.target.value })}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1.5 uppercase tracking-wider">
              {labels.backtest.frequency}
              <InfoTooltip content={labels.tooltips.backtestFrequency} />
            </label>
            <select
              className="input-fintech"
              value={form.rebalance_frequency}
              onChange={(e) => setForm({ ...form, rebalance_frequency: e.target.value })}
            >
              <option value="monthly">{labels.backtest.monthly}</option>
              <option value="quarterly">{labels.backtest.quarterly}</option>
            </select>
          </div>
          <div className="md:col-span-3">
            <div className="flex items-center justify-between mb-2">
              <label className="block text-xs font-medium text-slate-500 uppercase tracking-wider">
                {labels.backtest.manualPositions}
                <InfoTooltip content={labels.tooltips.backtestAllocation} />
              </label>
              <div className="flex items-center gap-3">
                <span className="text-xs text-slate-500">
                  {labels.backtest.totalValue}: {formatCurrency(totalValue)}
                </span>
                {hasRatios && (
                  <span
                    className={`text-xs ${totalRatio > 100 ? "text-accent-rose" : "text-slate-500"}`}
                  >
                    {labels.backtest.totalRatio}: {totalRatio}%
                  </span>
                )}
                <button
                  type="button"
                  onClick={() => {
                    const base = Math.floor(100 / form.positions.length);
                    const remainder = 100 - base * form.positions.length;
                    setForm((prev) => ({
                      ...prev,
                      positions: prev.positions.map((p, i) => ({
                        ...p,
                        ratio: String(base + (i === 0 ? remainder : 0)),
                      })),
                    }));
                  }}
                  disabled={form.positions.length === 0}
                  className="text-xs text-indigo-600 hover:text-indigo-700 disabled:text-slate-400"
                >
                  {labels.backtest.equalize}
                </button>
              </div>
            </div>
            <div className="space-y-2">
              {form.positions.map((position, idx) => (
                <div key={idx} className="grid grid-cols-12 gap-2 items-end">
                  <div className="col-span-3">
                    <label className="block text-xs text-slate-400 mb-1">{labels.backtest.symbol}</label>
                    <input
                      type="text"
                      className="input-fintech"
                      value={position.symbol}
                      placeholder="VCB"
                      onChange={(e) =>
                        setForm((prev) => ({
                          ...prev,
                          positions: prev.positions.map((p, i) =>
                            i === idx ? { ...p, symbol: e.target.value } : p
                          ),
                        }))
                      }
                    />
                  </div>
                  <div className="col-span-3">
                    <label className="block text-xs text-slate-400 mb-1">{labels.backtest.price}</label>
                    <input
                      type="number"
                      className="input-fintech"
                      value={position.price}
                      onChange={(e) =>
                        setForm((prev) => ({
                          ...prev,
                          positions: prev.positions.map((p, i) =>
                            i === idx ? { ...p, price: e.target.value } : p
                          ),
                        }))
                      }
                    />
                  </div>
                  <div className="col-span-3">
                    <label className="block text-xs text-slate-400 mb-1">{labels.backtest.quantity}</label>
                    <input
                      type="number"
                      className="input-fintech"
                      value={position.quantity}
                      onChange={(e) =>
                        setForm((prev) => ({
                          ...prev,
                          positions: prev.positions.map((p, i) =>
                            i === idx ? { ...p, quantity: e.target.value } : p
                          ),
                        }))
                      }
                    />
                  </div>
                  <div className="col-span-2">
                    <label className="block text-xs text-slate-400 mb-1">{labels.backtest.ratio}</label>
                    <input
                      type="number"
                      min="0"
                      max="100"
                      className="input-fintech"
                      value={position.ratio}
                      onChange={(e) =>
                        setForm((prev) => ({
                          ...prev,
                          positions: prev.positions.map((p, i) =>
                            i === idx ? { ...p, ratio: e.target.value } : p
                          ),
                        }))
                      }
                    />
                  </div>
                  <div className="col-span-1">
                    <button
                      type="button"
                      onClick={() =>
                        setForm((prev) => ({
                          ...prev,
                          positions: prev.positions.filter((_, i) => i !== idx),
                        }))
                      }
                      className="text-xs text-accent-rose hover:text-rose-600"
                    >
                      {labels.backtest.remove}
                    </button>
                  </div>
                </div>
              ))}
            </div>
            <button
              type="button"
              onClick={() =>
                setForm((prev) => ({
                  ...prev,
                  positions: [...prev.positions, { symbol: "", price: "", quantity: "", ratio: "" }],
                }))
              }
              className="mt-3 text-sm text-indigo-600 hover:text-indigo-700"
            >
              + {labels.backtest.addAsset}
            </button>

            <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4 items-center">
              <div className="h-48">
                {allocationPieData.length > 0 && (hasRatios || totalValue > 0) ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={allocationPieData}
                        dataKey="value"
                        nameKey="name"
                        cx="50%"
                        cy="50%"
                        innerRadius={40}
                        outerRadius={70}
                        paddingAngle={2}
                        stroke="none"
                      >
                        {allocationPieData.map((_, i) => (
                          <Cell key={`cell-${i}`} fill={COLORS[i % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={chartTooltipStyle}
                        formatter={(v: number, n: string) =>
                          hasRatios ? [`${v}%`, n] : [formatCurrency(v), n]
                        }
                      />
                    </PieChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-xs text-slate-500">
                    {labels.backtest.noAllocation}
                  </div>
                )}
              </div>
              <div className="flex flex-wrap content-start gap-2">
                {allocationPieData.map((entry, i) => (
                  <div key={entry.name} className="flex items-center gap-1.5 text-xs text-slate-500">
                    <span
                      className="w-2 h-2 rounded-full"
                      style={{ backgroundColor: COLORS[i % COLORS.length] }}
                    />
                    {entry.name} {hasRatios ? `${entry.value}%` : formatCurrency(entry.value)}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
        <div className="mt-4 flex flex-col gap-3">
          <button
            onClick={() => run.mutate()}
            disabled={
              run.isPending ||
              !form.start_date ||
              !form.end_date ||
              isBusy ||
              (hasRatios && totalRatio > 100)
            }
            className="btn-primary"
          >
            <Play className="w-4 h-4" />
            {run.isPending ? labels.backtest.running : labels.backtest.run}
          </button>

          <button
            type="button"
            onClick={() => setPromptMode((m) => !m)}
            className="text-sm text-slate-500 hover:text-indigo-600 inline-flex items-center gap-1.5"
          >
            <Sparkles className="w-4 h-4" />
            {promptMode ? labels.backtest.hidePrompt : labels.backtest.usePrompt}
          </button>

          {promptMode && (
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setStressMode(false)}
                  className={`text-xs px-2.5 py-1 rounded-md ${!stressMode ? "bg-indigo-100 text-indigo-700" : "text-slate-500 hover:text-slate-700"}`}
                >
                  Tạo kịch bản
                </button>
                <button
                  type="button"
                  onClick={() => setStressMode(true)}
                  className={`text-xs px-2.5 py-1 rounded-md ${stressMode ? "bg-indigo-100 text-indigo-700" : "text-slate-500 hover:text-slate-700"}`}
                >
                  Stress / What-if
                </button>
              </div>

              {!stressMode ? (
                <>
                  <textarea
                    className="input-fintech w-full min-h-[80px]"
                    placeholder={labels.backtest.promptPlaceholder}
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                  />
                  <button
                    onClick={() => aiRun.mutate()}
                    disabled={aiRun.isPending || !prompt.trim() || isBusy}
                    className="btn-secondary w-full"
                  >
                    {aiRun.isPending ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Sparkles className="w-4 h-4" />
                    )}
                    {labels.backtest.runPrompt}
                  </button>
                </>
              ) : (
                <>
                  <textarea
                    className="input-fintech w-full min-h-[80px]"
                    placeholder="Ví dụ: thử nghiệm khủng hoảng 2022, giảm 40% giá trị, hoặc đầu tư 100% vào VCB trong giai đoạn 2020-2021"
                    value={stressPrompt}
                    onChange={(e) => setStressPrompt(e.target.value)}
                  />
                  <button
                    onClick={() => aiStressRun.mutate()}
                    disabled={aiStressRun.isPending || !stressPrompt.trim() || isBusy}
                    className="btn-secondary w-full"
                  >
                    {aiStressRun.isPending ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Sparkles className="w-4 h-4" />
                    )}
                    Chạy stress/what-if
                  </button>
                </>
              )}
            </div>
          )}
        </div>
      </FintechCard>

      {result && (
        <div className="relative">
          {(run.isPending || aiRun.isPending || aiStressRun.isPending) && (
            <div className="absolute inset-0 z-10 flex items-center justify-center bg-white/60 backdrop-blur-sm rounded-xl">
              <div className="flex items-center gap-2 text-slate-600">
                <Loader2 className="w-5 h-5 animate-spin" />
                <span>{labels.backtest.running}</span>
              </div>
            </div>
          )}
          <>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <FintechCard delay={0.15}>
                <div className="card-title mb-1 inline-flex items-center">
                  {labels.backtest.finalValue}
                  <InfoTooltip content={labels.tooltips.totalValue} />
                </div>
                <div className="metric-value">
                  <AnimatedNumber value={result.final_value} formatter={formatCurrency} />
                </div>
              </FintechCard>
              <FintechCard delay={0.2}>
                <div className="card-title mb-1 inline-flex items-center">
                  {labels.backtest.totalReturn}
                  <InfoTooltip content={labels.tooltips.pnl} />
                </div>
                <div className={`metric-value ${result.total_return >= 0 ? "text-accent-emerald" : "text-accent-rose"}`}>
                  {formatPercent(result.total_return_percent)}
                </div>
              </FintechCard>
              <FintechCard delay={0.25}>
                <div className="card-title mb-1 inline-flex items-center">
                  {labels.backtest.maxDrawdown}
                  <InfoTooltip content={labels.tooltips.analyticsRiskMetrics} />
                </div>
                <div className="metric-value text-accent-rose">
                  -{formatPercent(result.max_drawdown_percent)}
                </div>
              </FintechCard>
            </div>

            {result.warnings && result.warnings.length > 0 && (
              <FintechCard delay={0.12}>
                <h3 className="card-title mb-2 text-amber-300">{labels.backtest.warnings}</h3>
                <ul className="list-disc list-inside text-sm text-slate-300 space-y-1">
                  {result.warnings.map((warning: string, idx: number) => (
                    <li key={idx}>{warning}</li>
                  ))}
                </ul>
              </FintechCard>
            )}

            <FintechCard delay={0.3}>
              <div className="flex items-center justify-between mb-4">
                <h3 className="card-title inline-flex items-center">
                  {labels.backtest.equityCurve}
                  <InfoTooltip content={labels.tooltips.portfolioTrend} />
                </h3>
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-1.5 text-xs text-slate-500">
                    <span className="w-2 h-2 rounded-full" style={{ backgroundColor: result.total_return >= 0 ? "#34D399" : "#FB7185" }} />
                    {labels.backtest.equityCurve}
                  </div>
                  <div className="flex items-center gap-1.5 text-xs text-slate-500">
                    <span className="w-2 h-2 rounded-full bg-amber-400" />
                    {labels.dashboard.benchmark}
                  </div>
                  <TrendBadge value={result.total_return_percent} />
                </div>
              </div>
              {chartData.length > 1 ? (
                <div className="h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={chartData}>
                      <defs>
                        <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor={result.total_return >= 0 ? "#34D399" : "#FB7185"} stopOpacity={0.3} />
                          <stop offset="100%" stopColor={result.total_return >= 0 ? "#34D399" : "#FB7185"} stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.1)" vertical={false} />
                      <XAxis dataKey="date" tick={{ fill: "#64748b", fontSize: 11 }} axisLine={false} tickLine={false} />
                      <YAxis tickFormatter={(v: number) => formatCurrency(v)} tick={{ fill: "#64748b", fontSize: 11 }} axisLine={false} tickLine={false} />
                      <Tooltip
                        contentStyle={chartTooltipStyle}
                        formatter={(v: number, name: string) => [
                          formatCurrency(v),
                          name === "portfolio" ? labels.backtest.equityCurve : labels.dashboard.benchmark,
                        ]}
                      />
                      <Area
                        type="monotone"
                        dataKey="portfolio"
                        stroke={result.total_return >= 0 ? "#34D399" : "#FB7185"}
                        strokeWidth={2.5}
                        fill="url(#equityGradient)"
                        dot={false}
                        activeDot={{ r: 5, stroke: "#ffffff", strokeWidth: 2 }}
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
                </div>
              ) : (
                <div className="text-slate-500">{labels.backtest.noData}</div>
              )}
            </FintechCard>

            <FintechCard delay={0.35}>
              <h3 className="card-title mb-4 inline-flex items-center">
                {labels.backtest.trades}
                <InfoTooltip content={labels.tooltips.rebalanceSuggestion} />
              </h3>
              {result.trades.length > 0 ? (
                <div className="overflow-x-auto max-h-80 overflow-y-auto scrollbar-thin">
                  <table className="table-fintech">
                    <thead className="sticky top-0 bg-white/80 backdrop-blur-md">
                      <tr>
                        <th className="text-left">{labels.backtest.date}</th>
                        <th className="text-left">{labels.backtest.symbol}</th>
                        <th className="text-left">{labels.backtest.action}</th>
                        <th className="text-right">{labels.backtest.quantity}</th>
                        <th className="text-right">{labels.backtest.price}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.trades.map((trade: any, idx: number) => (
                        <tr key={idx}>
                          <td className="font-mono text-slate-500">{trade.date}</td>
                          <td className="font-display font-semibold text-slate-900">{trade.symbol}</td>
                          <td>
                            <span className={trade.action === "BUY" ? "badge-gain" : "badge-loss"}>
                              {trade.action === "BUY" ? labels.transactions.buy : labels.transactions.sell}
                            </span>
                          </td>
                          <td className="text-right font-mono">{trade.quantity}</td>
                          <td className="text-right font-mono">{formatCurrency(trade.price)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="text-slate-500">{labels.backtest.noTrades}</div>
              )}
            </FintechCard>
          </>
        </div>
      )}
    </div>
  );
}
