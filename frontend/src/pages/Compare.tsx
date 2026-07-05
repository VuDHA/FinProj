import { CSSProperties, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useQueries, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Bot, Database, Plus, Search, X } from "lucide-react";
import { motion } from "framer-motion";
import {
  CompareSymbol,
  fillMissingHistory,
  getCorrelation,
  getHistory,
  getMetrics,
  getQuotes,
  getSymbols,
} from "../api/compare";
import { getCompareInsight } from "../api/ai";
import { AiGenerateButton } from "../components/AiGenerateButton";
import { AiInsightCard } from "../components/AiInsightCard";
import { ErrorMessage } from "../components/ErrorMessage";
import { EmptyState } from "../components/EmptyState";
import { FintechCard } from "../components/ui/FintechCard";
import { SectionHeader } from "../components/ui/SectionHeader";
import { Skeleton } from "../components/ui/Skeleton";
import { TrendBadge } from "../components/ui/TrendBadge";
import { InfoTooltip } from "../components/InfoTooltip";
import { useAiInsight } from "../hooks/useAiInsight";
import { labels } from "../i18n/vi";
import { chartTooltipStyle, formatCurrency, formatPercent } from "../lib/utils";

const MAX_SYMBOLS = 8;
const TABS = ["quotes", "chart", "metrics", "correlation"] as const;
type Tab = (typeof TABS)[number];

type RangePreset = "1M" | "1Q" | "1Y" | "YTD" | "CUSTOM";

interface SelectedSymbol {
  symbol: string;
  name: string;
  type: string;
  fund_type?: string | null;
}

function today() {
  return new Date().toISOString().split("T")[0];
}

interface DateRange {
  start: string;
  end: string;
}

function getRangeDates(range: RangePreset, customStart: string, customEnd: string): DateRange {
  if (range === "CUSTOM" && (!customStart || !customEnd)) {
    const fallback: DateRange = getRangeDates("1Y", "", "");
    return { start: fallback.start, end: fallback.end };
  }

  const end = today();
  const endDate = new Date(end);
  let start = end;
  if (range === "1M") {
    start = new Date(endDate.getTime() - 30 * 24 * 60 * 60 * 1000).toISOString().split("T")[0];
  } else if (range === "1Q") {
    start = new Date(endDate.getTime() - 90 * 24 * 60 * 60 * 1000).toISOString().split("T")[0];
  } else if (range === "1Y") {
    start = new Date(endDate.getTime() - 365 * 24 * 60 * 60 * 1000).toISOString().split("T")[0];
  } else if (range === "YTD") {
    start = `${endDate.getFullYear()}-01-01`;
  } else {
    return { start: customStart, end: customEnd };
  }
  return { start, end };
}

function parseUrlSymbols(raw: string | null): string[] {
  if (!raw) return [];
  return raw
    .split(",")
    .map((s) => s.trim().toUpperCase())
    .filter(Boolean)
    .filter((s, i, arr) => arr.indexOf(s) === i);
}

function buildSymbolMap(symbols: CompareSymbol[]) {
  const map = new Map<string, CompareSymbol>();
  symbols.forEach((s) => map.set(s.symbol.toUpperCase(), s));
  return map;
}

const COLORS = [
  "#6366f1",
  "#ec4899",
  "#06b6d4",
  "#f59e0b",
  "#10b981",
  "#8b5cf6",
  "#ef4444",
  "#14b8a6",
];

export function Compare() {
  const [searchParams, setSearchParams] = useSearchParams();
  const queryClient = useQueryClient();

  const [activeTab, setActiveTab] = useState<Tab>("quotes");
  const [search, setSearch] = useState("");
  const [range, setRange] = useState<RangePreset>(
    (searchParams.get("range") as RangePreset) || "1Y"
  );
  const [customStart, setCustomStart] = useState(searchParams.get("start") || "");
  const [customEnd, setCustomEnd] = useState(searchParams.get("end") || "");
  const [chartFillSymbol, setChartFillSymbol] = useState<string>("");
  const [fillLoading, setFillLoading] = useState(false);
  const [fillResult, setFillResult] = useState<string | null>(null);

  const { start, end } = useMemo(
    () => getRangeDates(range, customStart, customEnd),
    [range, customStart, customEnd]
  );

  const [selected, setSelected] = useState<SelectedSymbol[]>(() => {
    const symbols = parseUrlSymbols(searchParams.get("symbols"));
    return symbols.map((symbol) => ({
      symbol,
      name: symbol,
      type: "STOCK",
    }));
  });

  const allSymbols = useQuery({
    queryKey: ["compare-symbols"],
    queryFn: getSymbols,
    staleTime: 1000 * 60 * 30,
  });

  const symbolMap = useMemo(
    () => (allSymbols.data ? buildSymbolMap(allSymbols.data) : new Map()),
    [allSymbols.data]
  );

  // Hydrate selected symbols from listing when it loads.
  const hydratedSelected = useMemo(() => {
    return selected.map((item) => {
      const meta = symbolMap.get(item.symbol);
      if (!meta) return item;
      return {
        symbol: item.symbol,
        name: meta.name || item.name,
        type: meta.type,
        fund_type: meta.fund_type,
      };
    });
  }, [selected, symbolMap]);

  const symbolsList = useMemo(
    () => hydratedSelected.map((s) => s.symbol),
    [hydratedSelected]
  );
  const typesList = useMemo(
    () => hydratedSelected.map((s) => s.type),
    [hydratedSelected]
  );

  useEffect(() => {
    if (!chartFillSymbol && hydratedSelected.length > 0) {
      setChartFillSymbol(hydratedSelected[0].symbol);
    } else if (chartFillSymbol && !hydratedSelected.some((s) => s.symbol === chartFillSymbol)) {
      setChartFillSymbol(hydratedSelected.length > 0 ? hydratedSelected[0].symbol : "");
    }
  }, [hydratedSelected, chartFillSymbol]);

  const updateUrl = (next: SelectedSymbol[], nextRange: RangePreset, startValue: string, endValue: string) => {
    const params = new URLSearchParams();
    if (next.length > 0) {
      params.set("symbols", next.map((s) => s.symbol).join(","));
    }
    params.set("range", nextRange);
    if (nextRange === "CUSTOM") {
      params.set("start", startValue);
      params.set("end", endValue);
    }
    setSearchParams(params, { replace: true });
  };

  const addSymbol = (symbol: CompareSymbol) => {
    if (hydratedSelected.length >= MAX_SYMBOLS) return;
    if (hydratedSelected.some((s) => s.symbol === symbol.symbol.toUpperCase())) return;
    const next = [
      ...hydratedSelected,
      {
        symbol: symbol.symbol.toUpperCase(),
        name: symbol.name,
        type: symbol.type,
        fund_type: symbol.fund_type,
      },
    ];
    setSelected(next);
    updateUrl(next, range, customStart, customEnd);
    setSearch("");
  };

  const removeSymbol = (symbol: string) => {
    const next = hydratedSelected.filter((s) => s.symbol !== symbol);
    setSelected(next);
    updateUrl(next, range, customStart, customEnd);
  };

  const changeRange = (nextRange: RangePreset) => {
    setRange(nextRange);
    let nextStart = customStart;
    let nextEnd = customEnd;
    if (nextRange === "CUSTOM" && (!customStart || !customEnd)) {
      const fallback = getRangeDates("1Y", "", "");
      nextStart = fallback.start;
      nextEnd = fallback.end;
      setCustomStart(nextStart);
      setCustomEnd(nextEnd);
    }
    updateUrl(hydratedSelected, nextRange, nextStart, nextEnd);
  };

  const applyCustomDates = (startValue: string, endValue: string) => {
    setRange("CUSTOM");
    setCustomStart(startValue);
    setCustomEnd(endValue);
    updateUrl(hydratedSelected, "CUSTOM", startValue, endValue);
  };

  const handleFillMissing = async () => {
    if (!chartFillSymbol) return;
    const asset = hydratedSelected.find((s) => s.symbol === chartFillSymbol);
    if (!asset) return;

    setFillLoading(true);
    setFillResult(null);
    try {
      const result = await fillMissingHistory(chartFillSymbol, asset.type, start, end);
      await queryClient.invalidateQueries({
        queryKey: ["compare-history", chartFillSymbol, asset.type, start, end],
      });
      setFillResult(labels.compare.filled.replace("{count}", String(result.filled)));
    } catch (e) {
      setFillResult(labels.compare.fillError);
    } finally {
      setFillLoading(false);
    }
  };

  const filteredSymbols = useMemo(() => {
    if (!allSymbols.data || !search.trim()) return [];
    const term = search.toLowerCase();
    const already = new Set(hydratedSelected.map((s) => s.symbol));
    return allSymbols.data
      .filter(
        (s) =>
          !already.has(s.symbol.toUpperCase()) &&
          (s.symbol.toLowerCase().includes(term) || s.name.toLowerCase().includes(term))
      )
      .slice(0, 50);
  }, [allSymbols.data, search, hydratedSelected]);

  const searchRef = useRef<HTMLDivElement>(null);
  const [dropdownStyle, setDropdownStyle] = useState<CSSProperties>({});

  useLayoutEffect(() => {
    if (!filteredSymbols.length) return;
    const update = () => {
      const rect = searchRef.current?.getBoundingClientRect();
      if (!rect) return;
      setDropdownStyle({
        position: "fixed",
        top: rect.bottom + 4,
        left: rect.left,
        width: rect.width,
        zIndex: 50,
      });
    };
    update();
    const main = document.querySelector("main");
    window.addEventListener("resize", update);
    main?.addEventListener("scroll", update, { passive: true });
    return () => {
      window.removeEventListener("resize", update);
      main?.removeEventListener("scroll", update);
    };
  }, [filteredSymbols.length]);

  const quotes = useQuery({
    queryKey: ["compare-quotes", symbolsList.join(","), typesList.join(",")],
    queryFn: () => getQuotes(symbolsList, typesList),
    enabled: symbolsList.length > 0,
  });

  const metrics = useQuery({
    queryKey: ["compare-metrics", symbolsList.join(","), typesList.join(","), start, end],
    queryFn: () => getMetrics(symbolsList, typesList, start, end),
    enabled: symbolsList.length > 0,
  });

  const correlation = useQuery({
    queryKey: ["compare-correlation", symbolsList.join(","), typesList.join(","), start, end],
    queryFn: () => getCorrelation(symbolsList, typesList, start, end),
    enabled: symbolsList.length > 1,
  });

  const histories = useQueries({
    queries: hydratedSelected.map((s) => ({
      queryKey: ["compare-history", s.symbol, s.type, start, end],
      queryFn: () => getHistory(s.symbol, s.type, start, end),
      enabled: symbolsList.length > 0,
    })),
  });

  const chartData = useMemo(() => {
    if (hydratedSelected.length === 0) return [];
    const rawSeries: Record<string, Record<string, number>> = {};
    const allDates = new Set<string>();
    hydratedSelected.forEach((s, idx) => {
      const result = histories[idx];
      if (!result.data || result.data.length === 0) return;
      const data = result.data;
      const firstPrice = data[0].price;
      if (firstPrice <= 0) return;
      const series: Record<string, number> = {};
      data.forEach((point) => {
        series[point.date] = (point.price / firstPrice) * 100;
        allDates.add(point.date);
      });
      rawSeries[s.symbol] = series;
    });
    if (allDates.size === 0) return [];
    const sortedDates = Array.from(allDates).sort();

    // Fill forward so each symbol's line spans the full date range even when
    // the source skips non-trading days.
    const filledSeries: Record<string, Record<string, number>> = {};
    hydratedSelected.forEach((s) => {
      const series = rawSeries[s.symbol];
      if (!series) return;
      let lastValue: number | null = null;
      const filled: Record<string, number> = {};
      sortedDates.forEach((date) => {
        if (series[date] !== undefined) {
          lastValue = series[date];
        }
        if (lastValue !== null) {
          filled[date] = lastValue;
        }
      });
      filledSeries[s.symbol] = filled;
    });

    return sortedDates.map((date) => {
      const row: Record<string, number | string> = { date };
      hydratedSelected.forEach((s) => {
        const value = filledSeries[s.symbol]?.[date];
        if (value !== undefined) row[s.symbol] = value;
      });
      return row;
    });
  }, [hydratedSelected, histories]);

  const hasAnyHistory = useMemo(
    () => histories.some((h) => h.data && h.data.length > 0),
    [histories]
  );

  const isLoading =
    quotes.isLoading || metrics.isLoading || histories.some((h) => h.isLoading);
  const anyError =
    quotes.error || metrics.error || histories.some((h) => h.error);

  const compareInsight = useAiInsight({
    taskName: "compare_insight",
    fetcher: () => {
      if (hydratedSelected.length < 2) {
        throw new Error(labels.compare.correlationNeedTwo);
      }
      const corrLabels = correlation.data?.labels || hydratedSelected.map((s) => s.symbol);
      return getCompareInsight({
        symbols: hydratedSelected.map((s) => s.symbol),
        metrics: metrics.data || [],
        correlation: {
          labels: corrLabels,
          matrix: correlation.data?.matrix || [],
        },
      });
    },
  });

  return (
    <div className="space-y-6">
      <SectionHeader
        title={labels.compare.title}
        subtitle={labels.compare.normalizedChartHint}
      />

      <FintechCard>
        <div className="space-y-4">
          <div className="flex flex-col md:flex-row gap-4">
            <div ref={searchRef} className="relative z-50 flex-1">
              <div className="flex items-center gap-2 rounded-xl border border-fintech-border bg-white px-3 py-2">
                <Search className="w-4 h-4 text-slate-400" />
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder={labels.compare.searchPlaceholder}
                  className="flex-1 bg-transparent outline-none text-sm"
                  disabled={hydratedSelected.length >= MAX_SYMBOLS}
                />
              </div>
            </div>
            {filteredSymbols.length > 0 &&
              createPortal(
                <div
                  className="fixed z-50 rounded-xl border border-fintech-border bg-white shadow-lg max-h-60 overflow-auto"
                  style={dropdownStyle}
                >
                  {filteredSymbols.map((s) => (
                    <button
                      key={s.symbol}
                      onClick={() => addSymbol(s)}
                      className="w-full text-left px-3 py-2 text-sm hover:bg-slate-50 flex items-center justify-between"
                    >
                      <span>
                        <span className="font-semibold">{s.symbol}</span>{" "}
                        <span className="text-slate-500">{s.name}</span>
                      </span>
                      <Plus className="w-4 h-4 text-accent-blue" />
                    </button>
                  ))}
                </div>,
                document.body
              )}

            <div className="flex items-center gap-2 flex-wrap">
              {(["1M", "1Q", "1Y", "YTD", "CUSTOM"] as RangePreset[]).map((r) => (
                <button
                  key={r}
                  onClick={() => changeRange(r)}
                  className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${range === r
                    ? "bg-accent-blue text-white"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                    }`}
                >
                  {r === "1M" && labels.compare.range1M}
                  {r === "1Q" && labels.compare.range1Q}
                  {r === "1Y" && labels.compare.range1Y}
                  {r === "YTD" && labels.compare.rangeYTD}
                  {r === "CUSTOM" && labels.compare.rangeCustom}
                </button>
              ))}
            </div>
          </div>

          {range === "CUSTOM" && (
            <div className="flex items-center gap-3">
              <label className="text-sm text-slate-600">{labels.compare.startDate}</label>
              <input
                type="date"
                value={customStart}
                max={customEnd || today()}
                onChange={(e) => applyCustomDates(e.target.value, customEnd)}
                className="rounded-lg border border-fintech-border px-3 py-2 text-sm"
              />
              <label className="text-sm text-slate-600">{labels.compare.endDate}</label>
              <input
                type="date"
                value={customEnd}
                min={customStart}
                max={today()}
                onChange={(e) => applyCustomDates(customStart, e.target.value)}
                className="rounded-lg border border-fintech-border px-3 py-2 text-sm"
              />
            </div>
          )}

          <div className="flex items-center gap-2 flex-wrap">
            {hydratedSelected.map((s) => (
              <motion.div
                key={s.symbol}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                className="flex items-center gap-2 rounded-lg bg-slate-100 px-3 py-1.5 text-sm"
              >
                <span className="font-semibold">{s.symbol}</span>
                <span className="text-slate-500 truncate max-w-[160px]">{s.name}</span>
                <button
                  onClick={() => removeSymbol(s.symbol)}
                  className="text-slate-400 hover:text-accent-rose"
                >
                  <X className="w-4 h-4" />
                </button>
              </motion.div>
            ))}
            {hydratedSelected.length === 0 && (
              <span className="text-sm text-slate-400">{labels.compare.noSymbols}</span>
            )}
            {hydratedSelected.length >= MAX_SYMBOLS && (
              <span className="text-sm text-accent-rose">
                {labels.compare.maxSymbols.replace("{max}", String(MAX_SYMBOLS))}
              </span>
            )}
          </div>
        </div>
      </FintechCard>

      {hydratedSelected.length === 0 ? (
        <EmptyState
          title={labels.compare.noSymbols}
          description={labels.compare.addSymbolsHint}
        />
      ) : (
        <>
          {anyError && <ErrorMessage error={anyError as Error} retry={() => quotes.refetch()} />}

          <FintechCard delay={0.05}>
            <div className="flex items-center justify-between mb-3">
              <h3 className="card-title inline-flex items-center gap-2">
                <Bot className="w-4 h-4 text-indigo-500" />
                Phân tích AI so sánh
              </h3>
              <AiGenerateButton
                label="Phân tích"
                onClick={() => compareInsight.generate()}
                loading={compareInsight.loading}
                disabled={hydratedSelected.length < 2}
              />
            </div>
            <AiInsightCard
              data={compareInsight.data}
              loading={compareInsight.loading}
              error={compareInsight.error}
              onClose={compareInsight.clear}
            />
          </FintechCard>

          <div className="flex gap-2 border-b border-fintech-border">
            {TABS.map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 ${activeTab === tab
                  ? "border-accent-blue text-accent-blue"
                  : "border-transparent text-slate-500 hover:text-slate-700"
                  }`}
                disabled={tab === "correlation" && hydratedSelected.length < 2}
              >
                {tab === "quotes" && labels.compare.tabQuotes}
                {tab === "chart" && labels.compare.tabChart}
                {tab === "metrics" && labels.compare.tabMetrics}
                {tab === "correlation" && labels.compare.tabCorrelation}
              </button>
            ))}
          </div>

          {isLoading && (
            <div className="space-y-4">
              <Skeleton className="h-8 w-full" />
              <Skeleton className="h-64 w-full" />
            </div>
          )}

          {!isLoading && activeTab === "quotes" && (
            <FintechCard>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="text-slate-500 border-b border-fintech-border">
                    <tr>
                      <th className="text-left py-2 px-3">{labels.compare.type}</th>
                      <th className="text-left py-2 px-3">{labels.market.symbol}</th>
                      <th className="text-left py-2 px-3">{labels.assets.name}</th>
                      <th className="text-right py-2 px-3">{labels.compare.price}</th>
                      <th className="text-right py-2 px-3">{labels.compare.change}</th>
                      <th className="text-right py-2 px-3">{labels.compare.changePercent}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(quotes.data || []).map((q) => {
                      const meta = symbolMap.get(q.symbol);
                      return (
                        <tr key={q.symbol} className="border-b border-slate-100">
                          <td className="py-2 px-3 text-slate-500 whitespace-nowrap">
                            {meta?.type === "FUND"
                              ? labels.assetTypes.FUND
                              : labels.assetTypes.STOCK}
                          </td>
                          <td className="py-2 px-3 font-semibold whitespace-nowrap">{q.symbol}</td>
                          <td className="py-2 px-3 max-w-[140px] truncate">{meta?.name || q.symbol}</td>
                          <td className="py-2 px-3 value-cell" title={formatCurrency(q.price || 0)}>
                            {formatCurrency(q.price || 0)}
                          </td>
                          <td className="py-2 px-3 text-right">
                            {q.change != null ? (
                              <TrendBadge value={q.change} />
                            ) : (
                              <span className="text-slate-400">-</span>
                            )}
                          </td>
                          <td className="py-2 px-3 text-right">
                            {q.change_percent != null ? (
                              <TrendBadge value={q.change_percent} />
                            ) : (
                              <span className="text-slate-400">-</span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </FintechCard>
          )}

          {!isLoading && activeTab === "chart" && (
            <FintechCard>
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4">
                <div className="flex items-center gap-2">
                  <h3 className="font-semibold text-slate-800">{labels.compare.normalizedChart}</h3>
                  <InfoTooltip content={labels.compare.normalizedChartHint} />
                </div>
                <div className="flex items-center gap-2 flex-wrap">
                  <select
                    value={chartFillSymbol}
                    onChange={(e) => setChartFillSymbol(e.target.value)}
                    className="rounded-lg border border-fintech-border px-3 py-2 text-sm bg-white"
                  >
                    {hydratedSelected.map((s) => (
                      <option key={s.symbol} value={s.symbol}>
                        {s.symbol} - {s.name}
                      </option>
                    ))}
                  </select>
                  <button
                    onClick={handleFillMissing}
                    disabled={fillLoading || !chartFillSymbol}
                    className="inline-flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium bg-slate-100 text-slate-700 hover:bg-slate-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    <Database className="w-4 h-4" />
                    {fillLoading ? labels.compare.filling : labels.compare.fillMissing}
                  </button>
                </div>
              </div>
              {fillResult && (
                <p className={`text-sm mb-3 ${fillResult === labels.compare.fillError ? "text-accent-rose" : "text-emerald-600"}`}>
                  {fillResult}
                </p>
              )}
              {!hasAnyHistory ? (
                <p className="text-sm text-slate-500">{labels.compare.noHistory}</p>
              ) : (
                <div className="h-[400px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                      <XAxis
                        dataKey="date"
                        tick={{ fontSize: 12 }}
                        tickFormatter={(value) => {
                          const d = new Date(value);
                          return `${d.getMonth() + 1}/${d.getFullYear()}`;
                        }}
                        minTickGap={30}
                      />
                      <YAxis tick={{ fontSize: 12 }} domain={["auto", "auto"]} />
                      <Tooltip contentStyle={chartTooltipStyle} />
                      <Legend />
                      {hydratedSelected.map((s, idx) => (
                        <Line
                          key={s.symbol}
                          type="monotone"
                          dataKey={s.symbol}
                          name={s.symbol}
                          stroke={COLORS[idx % COLORS.length]}
                          strokeWidth={2}
                          dot={false}
                          connectNulls={false}
                          isAnimationActive={false}
                        />
                      ))}
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}
            </FintechCard>
          )}

          {!isLoading && activeTab === "metrics" && (
            <FintechCard>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="text-slate-500 border-b border-fintech-border">
                    <tr>
                      <th className="text-left py-2 px-3">{labels.market.symbol}</th>
                      <th className="text-right py-2 px-3">{labels.compare.totalReturn}</th>
                      <th className="text-right py-2 px-3">{labels.compare.annualizedReturn}</th>
                      <th className="text-right py-2 px-3">{labels.compare.volatility}</th>
                      <th className="text-right py-2 px-3">{labels.compare.maxDrawdown}</th>
                      <th className="text-right py-2 px-3">{labels.compare.sharpeRatio}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(metrics.data || []).map((m) => (
                      <tr key={m.symbol} className="border-b border-slate-100">
                        <td className="py-2 px-3 font-semibold">{m.symbol}</td>
                        <td className="py-2 px-3 text-right">
                          {m.total_return !== null && m.total_return !== undefined ? (
                            <TrendBadge value={m.total_return} />
                          ) : (
                            <span className="text-slate-400">-</span>
                          )}
                        </td>
                        <td className="py-2 px-3 text-right">
                          {m.annualized_return !== null && m.annualized_return !== undefined ? (
                            <span className={m.annualized_return >= 0 ? "text-emerald-600" : "text-accent-rose"}>
                              {formatPercent(m.annualized_return)}
                            </span>
                          ) : (
                            <span className="text-slate-400">-</span>
                          )}
                        </td>
                        <td className="py-2 px-3 text-right">
                          {m.volatility !== null && m.volatility !== undefined ? (
                            <span className="text-slate-700">{formatPercent(m.volatility)}</span>
                          ) : (
                            <span className="text-slate-400">-</span>
                          )}
                        </td>
                        <td className="py-2 px-3 text-right">
                          {m.max_drawdown_percent !== null && m.max_drawdown_percent !== undefined ? (
                            <span className="text-accent-rose">{formatPercent(m.max_drawdown_percent)}</span>
                          ) : (
                            <span className="text-slate-400">-</span>
                          )}
                        </td>
                        <td className="py-2 px-3 text-right">
                          {m.sharpe_ratio !== null && m.sharpe_ratio !== undefined ? (
                            <span className="text-slate-700">{m.sharpe_ratio.toFixed(2)}</span>
                          ) : (
                            <span className="text-slate-400">-</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </FintechCard>
          )}

          {!isLoading && activeTab === "correlation" && (
            <FintechCard>
              <div className="flex items-center gap-2 mb-4">
                <h3 className="font-semibold text-slate-800">{labels.compare.correlation}</h3>
                <InfoTooltip content={labels.compare.correlationHint} />
              </div>
              {hydratedSelected.length < 2 ? (
                <p className="text-sm text-slate-500">{labels.compare.correlationNeedTwo}</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="text-slate-500 border-b border-fintech-border">
                      <tr>
                        <th className="text-left py-2 px-3"></th>
                        {(correlation.data?.labels || hydratedSelected.map((s) => s.symbol)).map((label) => (
                          <th key={label} className="text-right py-2 px-3 font-semibold">
                            {label}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {(correlation.data?.labels || []).map((rowLabel, i) => (
                        <tr key={rowLabel} className="border-b border-slate-100">
                          <td className="py-2 px-3 font-semibold">{rowLabel}</td>
                          {(correlation.data?.matrix[i] || []).map((value, j) => {
                            const isDiag = i === j;
                            const intensity = isDiag ? 0 : Math.abs(value);
                            const bg = isDiag
                              ? "bg-slate-100"
                              : value > 0
                                ? `rgba(99, 102, 241, ${0.1 + intensity * 0.4})`
                                : `rgba(236, 72, 153, ${0.1 + intensity * 0.4})`;
                            return (
                              <td
                                key={`${i}-${j}`}
                                className="py-2 px-3 text-right font-medium"
                                style={{ background: bg }}
                              >
                                {isDiag ? "1.00" : value.toFixed(2)}
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </FintechCard>
          )}
        </>
      )}
    </div>
  );
}
