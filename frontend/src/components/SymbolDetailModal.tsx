import { useEffect, useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { RefreshCw, X, Calendar, TrendingUp, TrendingDown } from "lucide-react";
import API from "../api/client";
import { formatCurrency, formatPercent, formatNumber } from "../lib/utils";
import { labels } from "../i18n/vi";

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
    <div className="p-3 rounded-xl bg-slate-50/80 border border-slate-100">
      <p className="text-xs text-slate-500 mb-1">{label}</p>
      <p className={`text-base font-semibold font-mono ${colorClass}`}>{value}</p>
    </div>
  );
}

export default function SymbolDetailModal({
  symbol,
  name,
  type,
  exchange,
  onClose,
}: SymbolDetailModalProps) {
  const [fundDetail, setFundDetail] = useState<FundDetail | null>(null);
  const [history, setHistory] = useState<HistoryPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [range, setRange] = useState<RangePreset>("3M");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);

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

    const detailPromise =
      type === "FUND"
        ? API.get(`/prices/fund-detail/${encodeURIComponent(symbol)}`)
        : Promise.resolve({ data: null });

    const historyPromise = API.get(`/prices/market-history/${encodeURIComponent(symbol)}`, {
      params: { type, start, end },
    });

    Promise.all([detailPromise, historyPromise])
      .then(([detailRes, historyRes]) => {
        if (cancelled) return;
        setFundDetail(detailRes.data);
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
    return d.toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit" });
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

          {loading ? (
            <div className="text-slate-500 py-8 text-center">{labels.common.loading}</div>
          ) : error ? (
            <div className="text-rose-500 py-8 text-center">{error}</div>
          ) : (
            <>
              <div className="glass-card p-5">
                <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
                  <div className="min-w-0">
                    <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">
                      {labels.symbolDetail.price}
                    </p>
                    <p className="text-3xl font-bold text-slate-900 font-mono tracking-tight">
                      {stats ? formatCurrency(stats.last) : "—"}
                    </p>
                  </div>
                  <div className="flex items-center gap-5">
                    <div>
                      <p className="text-xs text-slate-500 mb-1">{labels.symbolDetail.change}</p>
                      <p
                        className={`text-lg font-semibold font-mono flex items-center gap-1 ${positive ? "text-accent-emerald" : "text-accent-rose"
                          }`}
                      >
                        {positive ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
                        {stats ? formatCurrency(stats.last - stats.first) : "—"}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-slate-500 mb-1">{labels.symbolDetail.changePercent}</p>
                      <p
                        className={`text-lg font-semibold font-mono ${positive ? "text-accent-emerald" : "text-accent-rose"
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

              {fundDetail && (
                <div className="rounded-xl border border-slate-100 bg-slate-50/80 p-4 space-y-3">
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    Thông tin quỹ
                  </p>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-x-4 gap-y-2 text-sm">
                    {fundDetail.fund_type && (
                      <div className="flex justify-between md:justify-start md:gap-2">
                        <span className="text-slate-500">Loại quỹ:</span>
                        <span className="font-medium text-slate-900">{fundDetail.fund_type}</span>
                      </div>
                    )}
                    {fundDetail.owner && (
                      <div className="flex justify-between md:justify-start md:gap-2">
                        <span className="text-slate-500">Công ty quản lý:</span>
                        <span className="font-medium text-slate-900">{fundDetail.owner}</span>
                      </div>
                    )}
                    {fundDetail.management_fee !== undefined && (
                      <div className="flex justify-between md:justify-start md:gap-2">
                        <span className="text-slate-500">Phí quản lý:</span>
                        <span className="font-medium text-slate-900">{fundDetail.management_fee}%</span>
                      </div>
                    )}
                    {fundDetail.inception_date && (
                      <div className="flex justify-between md:justify-start md:gap-2">
                        <span className="text-slate-500">Ngày thành lập:</span>
                        <span className="font-medium text-slate-900">
                          {new Date(fundDetail.inception_date).toLocaleDateString("vi-VN")}
                        </span>
                      </div>
                    )}
                    {fundDetail.vsd_fee_id && (
                      <div className="flex justify-between md:justify-start md:gap-2">
                        <span className="text-slate-500">Mã VSD:</span>
                        <span className="font-medium text-slate-900">{fundDetail.vsd_fee_id}</span>
                      </div>
                    )}
                    {fundDetail.nav_update_at && (
                      <div className="flex justify-between md:justify-start md:gap-2">
                        <span className="text-slate-500">Cập nhật NAV:</span>
                        <span className="font-medium text-slate-900">
                          {new Date(fundDetail.nav_update_at).toLocaleDateString("vi-VN")}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              )}

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
                            stopColor={positive ? "#10b981" : "#f43f5e"}
                            stopOpacity={0.3}
                          />
                          <stop
                            offset="100%"
                            stopColor={positive ? "#10b981" : "#f43f5e"}
                            stopOpacity={0}
                          />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="4 4" stroke="#e2e8f0" vertical={false} />
                      <XAxis
                        dataKey="date"
                        tick={{ fontSize: 12, fill: "#64748b" }}
                        tickFormatter={chartTickFormatter}
                        axisLine={false}
                        tickLine={false}
                        dy={8}
                      />
                      <YAxis
                        tick={{ fontSize: 12, fill: "#64748b" }}
                        tickFormatter={formatAxisPrice}
                        width={70}
                        axisLine={false}
                        tickLine={false}
                        dx={-4}
                      />
                      <Tooltip
                        contentStyle={{
                          background: "rgba(255, 255, 255, 0.95)",
                          border: "1px solid rgba(15, 23, 42, 0.08)",
                          borderRadius: "12px",
                          color: "#1e293b",
                          boxShadow: "0 4px 24px rgba(15, 23, 42, 0.08)",
                        }}
                        formatter={(value: number) => [formatCurrency(value), labels.symbolDetail.price]}
                        labelFormatter={(date: string) =>
                          `Ngày ${new Date(date).toLocaleDateString("vi-VN")}`
                        }
                      />
                      <Area
                        type="monotone"
                        dataKey="price"
                        stroke={positive ? "#10b981" : "#f43f5e"}
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
        </div>
      </div>
    </div>
  );
}
