import React, { useEffect, useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { RefreshCw, X, Calendar, TrendingUp, TrendingDown, BarChart3, Info, Sparkles } from "lucide-react";
import API from "../api/client";
import { getFundDetail, getStockDetail, getSymbolAIInsight } from "../api/symbol";
import { chartTooltipStyle, formatCurrency, formatPercent, formatNumber, formatDate, formatDateShort } from "../lib/utils";
import { labels } from "../i18n/vi";
import { useDateFormat } from "../hooks/useDateFormat";
import { AiInsightCard } from "./AiInsightCard";

interface SymbolDetailModalProps {
  symbol: string;
  name: string;
  type: string;
  exchange: string;
  onClose: () => void;
}

interface FundDetail {
  symbol: string;
  name: string;
  fund_type?: string;
  owner?: string;
  management_fee?: number;
  inception_date?: string;
  nav: number;
  nav_update_at?: string;
  vsd_fee_id?: string;
}

interface StockDetail {
  symbol: string;
  name: string;
  exchange: string;
  type: string;
  sector?: string;
  industry?: string;
  market_cap?: number;
  price: number;
  change: number;
  change_percent: number;
  date: string;
  pe?: number;
  pb?: number;
  dividend_yield?: number;
}

interface HistoryPoint {
  date: string;
  price: number;
}

type RangePreset = "1W" | "1M" | "3M" | "6M" | "1Y" | "3Y" | "5Y" | "YTD" | "ALL" | "CUSTOM";

const PRESETS: RangePreset[] = ["1W", "1M", "3M", "6M", "1Y", "3Y", "5Y", "YTD", "ALL", "CUSTOM"];

const PRESET_LABELS: Record<RangePreset, string> = {
  "1W": "1 tuần",
  "1M": "1 tháng",
  "3M": "3 tháng",
  "6M": "6 tháng",
  "1Y": "1 năm",
  "3Y": "3 năm",
  "5Y": "5 năm",
  YTD: "Từ đầu năm",
  ALL: "Toàn bộ",
  CUSTOM: "Tùy chỉnh",
};

function getPresetDates(preset: RangePreset) {
  const end = new Date();
  const start = new Date();
  switch (preset) {
    case "1W":
      start.setDate(start.getDate() - 7);
      break;
    case "1M":
      start.setMonth(start.getMonth() - 1);
      break;
    case "3M":
      start.setMonth(start.getMonth() - 3);
      break;
    case "6M":
      start.setMonth(start.getMonth() - 6);
      break;
    case "1Y":
      start.setFullYear(start.getFullYear() - 1);
      break;
    case "3Y":
      start.setFullYear(start.getFullYear() - 3);
      break;
    case "5Y":
      start.setFullYear(start.getFullYear() - 5);
      break;
    case "YTD":
      start.setMonth(0, 1);
      start.setHours(0, 0, 0, 0);
      break;
    case "ALL":
      start.setFullYear(start.getFullYear() - 10);
      break;
    case "CUSTOM":
      return null;
  }
  return {
    start: start.toISOString().split("T")[0],
    end: end.toISOString().split("T")[0],
  };
}

function computeStats(points: HistoryPoint[]) {
  if (!points.length) return null;
  const prices = points.map((p) => p.price);
  const first = prices[0];
  const last = prices[prices.length - 1];
  const max = Math.max(...prices);
  const min = Math.min(...prices);
  const avg = prices.reduce((a, b) => a + b, 0) / prices.length;

  const dailyReturns: number[] = [];
  for (let i = 1; i < prices.length; i++) {
    dailyReturns.push((prices[i] - prices[i - 1]) / prices[i - 1]);
  }
  const volatility = dailyReturns.length
    ? Math.sqrt(dailyReturns.reduce((a, b) => a + b * b, 0) / dailyReturns.length) * Math.sqrt(252) * 100
    : 0;

  const days = points.length;
  const totalReturn = first ? ((last - first) / first) * 100 : 0;
  const years = Math.max(days / 252, 1 / 252);
  const annualized = first ? (Math.pow(last / first, 1 / years) - 1) * 100 : 0;

  return { first, last, max, min, avg, totalReturn, annualized, volatility, days };
}

function formatAxisPrice(n: number) {
  return formatNumber(n, 0);
}

function CompactStat({
  label,
  value,
  positive,
}: {
  label: string;
  value: string;
  positive?: boolean;
}) {
  const colorClass =
    positive === undefined
      ? "text-slate-900"
      : positive
        ? "text-accent-emerald"
        : "text-accent-rose";
  return (
    <div className="p-3 rounded-xl bg-slate-50/80 border border-slate-100 min-w-0 overflow-hidden">
      <p className="text-xs text-slate-500 mb-1">{label}</p>
      <p className={`value-text text-sm md:text-base font-semibold ${colorClass}`} title={value}>{value}</p>
    </div>
  );
}

type Tab = "overview" | "info" | "ai";

const TABS: { key: Tab; label: string; icon: React.ReactNode }[] = [
  { key: "overview", label: labels.symbolDetail.overview, icon: <BarChart3 size={16} /> },
  { key: "info", label: labels.symbolDetail.info, icon: <Info size={16} /> },
  { key: "ai", label: labels.symbolDetail.aiAnalysis, icon: <Sparkles size={16} /> },
];

export default function SymbolDetailModal({
  symbol,
  name,
  type,
  exchange,
  onClose,
}: SymbolDetailModalProps) {
  const { format: dateFormat } = useDateFormat();
  const [fundDetail, setFundDetail] = useState<FundDetail | null>(null);
  const [stockDetail, setStockDetail] = useState<StockDetail | null>(null);
  const [history, setHistory] = useState<HistoryPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [range, setRange] = useState<RangePreset>("3M");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);
  const [activeTab, setActiveTab] = useState<Tab>("overview");
  const [aiInsight, setAiInsight] = useState<{ overall: string; details: string; suggestions: string[]; used_ollama?: boolean } | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);
  const [aiGenerated, setAiGenerated] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  useEffect(() => {
    const dates = getPresetDates(range);
    if (dates) {
      setStart(dates.start);
      setEnd(dates.end);
    }
  }, [range]);

  useEffect(() => {
    let cancelled = false;
    if (!start || !end) return;
    setLoading(true);
    setError(null);
    setAiGenerated(false);
    setAiInsight(null);
    setAiError(null);

    const detailPromise =
      type === "FUND"
        ? getFundDetail(symbol)
        : getStockDetail(symbol);

    const historyPromise = API.get(`/prices/market-history/${encodeURIComponent(symbol)}`, {
      params: { type, start, end },
    });

    Promise.all([detailPromise, historyPromise])
      .then(([detail, historyRes]) => {
        if (cancelled) return;
        if (type === "FUND") {
          setFundDetail(detail as FundDetail);
        } else {
          setStockDetail(detail as StockDetail);
        }
        setHistory(historyRes.data || []);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err?.response?.data?.detail || err.message || labels.common.error);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [symbol, type, start, end, refreshKey]);

  const generateAIInsight = async () => {
    if (aiLoading || !start || !end) return;
    setAiLoading(true);
    setAiError(null);
    try {
      const data = await getSymbolAIInsight(symbol, type, start, end);
      setAiInsight(data);
      setAiGenerated(true);
    } catch (err: any) {
      setAiError(err?.response?.data?.detail || err.message || labels.common.error);
    } finally {
      setAiLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === "ai" && !aiGenerated && !aiLoading && !error) {
      generateAIInsight();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab, aiGenerated, aiLoading, error]);

  const chartData = useMemo(
    () =>
      history.map((h) => ({
        date: h.date,
        price: h.price,
      })),
    [history]
  );

  const stats = useMemo(() => computeStats(history), [history]);
  const positive = useMemo(() => stats && stats.totalReturn >= 0, [stats]);

  const chartTickFormatter = (date: string) => {
    const d = new Date(date);
    if (["1Y", "3Y", "5Y", "ALL", "YTD"].includes(range)) {
      return d.toLocaleDateString("vi-VN", { month: "2-digit", year: "2-digit" });
    }
    return formatDateShort(date, dateFormat);
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl shadow-2xl w-full max-w-3xl max-h-[92vh] overflow-y-auto scrollbar-thin border border-slate-100"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between px-6 py-5 border-b border-slate-100">
          <div className="min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span
                className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-semibold uppercase tracking-wide ${type === "FUND"
                  ? "bg-accent-violet/10 text-accent-violet ring-1 ring-inset ring-accent-violet/20"
                  : "bg-accent-blue/10 text-accent-blue ring-1 ring-inset ring-accent-blue/20"
                  }`}
              >
                {type === "FUND" ? labels.assetTypes.FUND : labels.assetTypes.STOCK}
              </span>
              <h2 className="text-xl font-bold text-slate-900">{symbol}</h2>
            </div>
            <p className="text-sm text-slate-500 truncate max-w-md">{name}</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-full hover:bg-slate-100 text-slate-500 transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        <div className="p-6 space-y-6">
          <div className="space-y-3">
            <div className="flex flex-wrap gap-2">
              {PRESETS.map((preset) => (
                <button
                  key={preset}
                  onClick={() => setRange(preset)}
                  className={`px-2.5 py-1.5 text-xs font-medium rounded-lg transition-colors ${range === preset
                    ? "bg-slate-900 text-white shadow-sm"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                    }`}
                >
                  {PRESET_LABELS[preset]}
                </button>
              ))}
            </div>
            <div className="flex items-center gap-2 text-sm">
              <Calendar size={16} className="text-slate-400 shrink-0" />
              <input
                type="date"
                className="input-fintech text-sm"
                value={start}
                max={end}
                onChange={(e) => {
                  setRange("CUSTOM");
                  setStart(e.target.value);
                }}
              />
              <span className="text-slate-400">-</span>
              <input
                type="date"
                className="input-fintech text-sm"
                value={end}
                min={start}
                onChange={(e) => {
                  setRange("CUSTOM");
                  setEnd(e.target.value);
                }}
              />
              <button
                onClick={() => setRefreshKey((k) => k + 1)}
                className="ml-auto p-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-600 transition-colors"
                title={labels.symbolDetail.reset}
              >
                <RefreshCw size={16} />
              </button>
            </div>
          </div>

          <div className="flex gap-2 border-b border-slate-100">
            {TABS.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`flex items-center gap-1.5 px-3 py-2 text-sm font-medium transition-colors border-b-2 ${activeTab === tab.key
                  ? "text-slate-900 border-slate-900"
                  : "text-slate-500 border-transparent hover:text-slate-700"
                  }`}
              >
                {tab.icon}
                {tab.label}
              </button>
            ))}
          </div>

          {loading ? (
            <div className="text-slate-500 py-8 text-center">{labels.common.loading}</div>
          ) : error ? (
            <div className="text-rose-500 py-8 text-center">{error}</div>
          ) : (
            <div className="space-y-6">
              {activeTab === "overview" && (
                <>
                  <div className="glass-card p-5">
                    <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
                      <div className="min-w-0 overflow-hidden">
                        <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">
                          {labels.symbolDetail.price}
                        </p>
                        <p className="value-text text-2xl md:text-3xl font-bold text-slate-900 tracking-tight" title={stats ? formatCurrency(stats.last) : undefined}>
                          {stats ? formatCurrency(stats.last) : "—"}
                        </p>
                      </div>
                      <div className="flex items-center gap-3 md:gap-5 min-w-0">
                        <div className="min-w-0 overflow-hidden">
                          <p className="text-xs text-slate-500 mb-1">{labels.symbolDetail.change}</p>
                          <p
                            className={`value-text text-base md:text-lg font-semibold flex items-center gap-1 ${positive ? "text-accent-emerald" : "text-accent-rose"
                              }`}
                            title={stats ? formatCurrency(stats.last - stats.first) : undefined}
                          >
                            {positive ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
                            {stats ? formatCurrency(stats.last - stats.first) : "—"}
                          </p>
                        </div>
                        <div className="min-w-0 overflow-hidden">
                          <p className="text-xs text-slate-500 mb-1">{labels.symbolDetail.changePercent}</p>
                          <p
                            className={`value-text text-base md:text-lg font-semibold ${positive ? "text-accent-emerald" : "text-accent-rose"
                              }`}
                          >
                            {stats ? formatPercent(stats.totalReturn) : "—"}
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                    <CompactStat label={labels.symbolDetail.high} value={stats ? formatCurrency(stats.max) : "—"} />
                    <CompactStat label={labels.symbolDetail.low} value={stats ? formatCurrency(stats.min) : "—"} />
                    <CompactStat label={labels.symbolDetail.avg} value={stats ? formatCurrency(stats.avg) : "—"} />
                    <CompactStat
                      label={labels.symbolDetail.annualized}
                      value={stats ? formatPercent(stats.annualized) : "—"}
                      positive={stats ? stats.annualized >= 0 : undefined}
                    />
                    <CompactStat
                      label={labels.symbolDetail.volatility}
                      value={stats ? formatPercent(stats.volatility) : "—"}
                    />
                    <CompactStat label={labels.symbolDetail.exchange} value={exchange} />
                    <CompactStat
                      label={labels.symbolDetail.sessions}
                      value={stats ? `${stats.days} ${labels.symbolDetail.sessions}` : "—"}
                    />
                  </div>

                  <div className="h-80">
                    <div className="flex items-center justify-between mb-3">
                      <p className="text-sm font-semibold text-slate-700">{labels.symbolDetail.priceHistory}</p>
                      <span className="text-xs text-slate-400">
                        {stats ? `${stats.days} ${labels.symbolDetail.sessions}` : ""}
                      </span>
                    </div>
                    {chartData.length > 0 ? (
                      <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={chartData} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
                          <defs>
                            <linearGradient id={`detailGradient-${symbol}`} x1="0" y1="0" x2="0" y2="1">
                              <stop
                                offset="0%"
                                stopColor={positive ? "var(--accent-emerald)" : "var(--accent-rose)"}
                                stopOpacity={0.3}
                              />
                              <stop
                                offset="100%"
                                stopColor={positive ? "var(--accent-emerald)" : "var(--accent-rose)"}
                                stopOpacity={0}
                              />
                            </linearGradient>
                          </defs>
                          <CartesianGrid strokeDasharray="4 4" stroke="var(--fintech-border)" vertical={false} />
                          <XAxis
                            dataKey="date"
                            tick={{ fontSize: 12, fill: "var(--text-muted)" }}
                            tickFormatter={chartTickFormatter}
                            axisLine={false}
                            tickLine={false}
                            dy={8}
                          />
                          <YAxis
                            tick={{ fontSize: 12, fill: "var(--text-muted)" }}
                            tickFormatter={formatAxisPrice}
                            width={70}
                            axisLine={false}
                            tickLine={false}
                            dx={-4}
                          />
                          <Tooltip
                            contentStyle={chartTooltipStyle}
                            formatter={(value: number) => [formatCurrency(value), labels.symbolDetail.price]}
                            labelFormatter={(date: string) =>
                              `Ngày ${formatDate(date, dateFormat)}`
                            }
                          />
                          <Area
                            type="monotone"
                            dataKey="price"
                            stroke={positive ? "var(--accent-emerald)" : "var(--accent-rose)"}
                            strokeWidth={2.5}
                            fill={`url(#detailGradient-${symbol})`}
                            dot={false}
                            activeDot={{ r: 5, strokeWidth: 0 }}
                          />
                        </AreaChart>
                      </ResponsiveContainer>
                    ) : (
                      <div className="flex items-center justify-center h-full text-slate-500 bg-slate-50/50 rounded-xl border border-dashed border-slate-200">
                        {labels.symbolDetail.noData}
                      </div>
                    )}
                  </div>
                </>
              )}

              {activeTab === "info" && (
                <div className="rounded-xl border border-slate-100 bg-slate-50/80 p-4 space-y-3">
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    {type === "FUND" ? labels.symbolDetail.fundInfo : labels.symbolDetail.stockInfo}
                  </p>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-x-4 gap-y-2 text-sm">
                    {type === "FUND" && fundDetail ? (
                      <>
                        {fundDetail.fund_type && (
                          <div className="flex justify-between md:justify-start md:gap-2">
                            <span className="text-slate-500">{labels.symbolDetail.fundType}:</span>
                            <span className="font-medium text-slate-900 flex-1 min-w-0 overflow-hidden truncate text-right md:text-left">{fundDetail.fund_type}</span>
                          </div>
                        )}
                        {fundDetail.owner && (
                          <div className="flex justify-between md:justify-start md:gap-2">
                            <span className="text-slate-500">{labels.symbolDetail.owner}:</span>
                            <span className="font-medium text-slate-900 flex-1 min-w-0 overflow-hidden truncate text-right md:text-left">{fundDetail.owner}</span>
                          </div>
                        )}
                        {fundDetail.management_fee !== undefined && (
                          <div className="flex justify-between md:justify-start md:gap-2">
                            <span className="text-slate-500">{labels.symbolDetail.managementFee}:</span>
                            <span className="font-medium text-slate-900 flex-1 min-w-0 overflow-hidden truncate text-right md:text-left">{fundDetail.management_fee}%</span>
                          </div>
                        )}
                        {fundDetail.inception_date && (
                          <div className="flex justify-between md:justify-start md:gap-2">
                            <span className="text-slate-500">{labels.symbolDetail.inceptionDate}:</span>
                            <span className="font-medium text-slate-900 flex-1 min-w-0 overflow-hidden truncate text-right md:text-left">
                              {formatDate(fundDetail.inception_date, dateFormat)}
                            </span>
                          </div>
                        )}
                        {fundDetail.vsd_fee_id && (
                          <div className="flex justify-between md:justify-start md:gap-2">
                            <span className="text-slate-500">{labels.symbolDetail.vsdFeeId}:</span>
                            <span className="font-medium text-slate-900 flex-1 min-w-0 overflow-hidden truncate text-right md:text-left">{fundDetail.vsd_fee_id}</span>
                          </div>
                        )}
                        {fundDetail.nav_update_at && (
                          <div className="flex justify-between md:justify-start md:gap-2">
                            <span className="text-slate-500">{labels.symbolDetail.navUpdateAt}:</span>
                            <span className="font-medium text-slate-900 flex-1 min-w-0 overflow-hidden truncate text-right md:text-left">
                              {formatDate(fundDetail.nav_update_at, dateFormat)}
                            </span>
                          </div>
                        )}
                        <div className="flex justify-between md:justify-start md:gap-2">
                          <span className="text-slate-500">{labels.symbolDetail.nav}:</span>
                          <span className="font-medium text-slate-900 flex-1 min-w-0 overflow-hidden truncate text-right md:text-left">{formatCurrency(fundDetail.nav)}</span>
                        </div>
                      </>
                    ) : stockDetail ? (
                      <>
                        <div className="flex justify-between md:justify-start md:gap-2">
                          <span className="text-slate-500">{labels.symbolDetail.exchange}:</span>
                          <span className="font-medium text-slate-900 flex-1 min-w-0 overflow-hidden truncate text-right md:text-left">{stockDetail.exchange}</span>
                        </div>
                        {stockDetail.sector && (
                          <div className="flex justify-between md:justify-start md:gap-2">
                            <span className="text-slate-500">{labels.symbolDetail.sector}:</span>
                            <span className="font-medium text-slate-900 flex-1 min-w-0 overflow-hidden truncate text-right md:text-left">{stockDetail.sector}</span>
                          </div>
                        )}
                        {stockDetail.industry && (
                          <div className="flex justify-between md:justify-start md:gap-2">
                            <span className="text-slate-500">{labels.symbolDetail.industry}:</span>
                            <span className="font-medium text-slate-900 flex-1 min-w-0 overflow-hidden truncate text-right md:text-left">{stockDetail.industry}</span>
                          </div>
                        )}
                        {stockDetail.market_cap !== undefined && stockDetail.market_cap > 0 && (
                          <div className="flex justify-between md:justify-start md:gap-2">
                            <span className="text-slate-500">{labels.symbolDetail.marketCap}:</span>
                            <span className="font-medium text-slate-900 flex-1 min-w-0 overflow-hidden truncate text-right md:text-left">{formatCurrency(stockDetail.market_cap)}</span>
                          </div>
                        )}
                        {stockDetail.pe !== undefined && stockDetail.pe > 0 && (
                          <div className="flex justify-between md:justify-start md:gap-2">
                            <span className="text-slate-500">{labels.symbolDetail.pe}:</span>
                            <span className="font-medium text-slate-900 flex-1 min-w-0 overflow-hidden truncate text-right md:text-left">{formatNumber(stockDetail.pe, 2)}</span>
                          </div>
                        )}
                        {stockDetail.pb !== undefined && stockDetail.pb > 0 && (
                          <div className="flex justify-between md:justify-start md:gap-2">
                            <span className="text-slate-500">{labels.symbolDetail.pb}:</span>
                            <span className="font-medium text-slate-900 flex-1 min-w-0 overflow-hidden truncate text-right md:text-left">{formatNumber(stockDetail.pb, 2)}</span>
                          </div>
                        )}
                        {stockDetail.dividend_yield !== undefined && stockDetail.dividend_yield > 0 && (
                          <div className="flex justify-between md:justify-start md:gap-2">
                            <span className="text-slate-500">{labels.symbolDetail.dividendYield}:</span>
                            <span className="font-medium text-slate-900 flex-1 min-w-0 overflow-hidden truncate text-right md:text-left">{formatPercent(stockDetail.dividend_yield)}</span>
                          </div>
                        )}
                        <div className="flex justify-between md:justify-start md:gap-2">
                          <span className="text-slate-500">{labels.symbolDetail.price}:</span>
                          <span className="font-medium text-slate-900 flex-1 min-w-0 overflow-hidden truncate text-right md:text-left">{formatCurrency(stockDetail.price)}</span>
                        </div>
                        <div className="flex justify-between md:justify-start md:gap-2">
                          <span className="text-slate-500">{labels.symbolDetail.changePercent}:</span>
                          <span className={`font-medium flex-1 min-w-0 overflow-hidden truncate text-right md:text-left ${stockDetail.change_percent >= 0 ? "text-accent-emerald" : "text-accent-rose"}`}>
                            {formatPercent(stockDetail.change_percent)}
                          </span>
                        </div>
                      </>
                    ) : (
                      <div className="text-slate-500">{labels.symbolDetail.noData}</div>
                    )}
                  </div>
                </div>
              )}

              {activeTab === "ai" && (
                <div className="space-y-4">
                  {!aiGenerated && !aiLoading && (
                    <div className="flex justify-center">
                      <button
                        onClick={generateAIInsight}
                        disabled={aiLoading}
                        className="btn-primary inline-flex items-center gap-2"
                      >
                        <Sparkles size={16} />
                        {labels.symbolDetail.aiGenerate}
                      </button>
                    </div>
                  )}
                  <AiInsightCard
                    data={aiInsight}
                    loading={aiLoading}
                    error={aiError}
                    onClose={() => {
                      setAiInsight(null);
                      setAiGenerated(false);
                      setAiError(null);
                    }}
                  />
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
