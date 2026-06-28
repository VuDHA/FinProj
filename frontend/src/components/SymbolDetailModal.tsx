import { useEffect, useMemo, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import API from "../api/client";
import { formatCurrency, formatPercent } from "../lib/utils";
import { X } from "lucide-react";

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

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    const end = new Date();
    const start = new Date();
    start.setMonth(start.getMonth() - 3);
    const startStr = start.toISOString().split("T")[0];
    const endStr = end.toISOString().split("T")[0];

    const detailPromise =
      type === "FUND"
        ? API.get(`/prices/fund-detail/${encodeURIComponent(symbol)}`)
        : Promise.resolve({ data: null });

    const historyPromise = API.get(`/prices/market-history/${encodeURIComponent(symbol)}`, {
      params: { type, start: startStr, end: endStr },
    });

    Promise.all([detailPromise, historyPromise])
      .then(([detailRes, historyRes]) => {
        if (cancelled) return;
        setFundDetail(detailRes.data);
        setHistory(historyRes.data || []);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err?.response?.data?.detail || err.message || "Lỗi tải dữ liệu");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [symbol, type]);

  const chartData = useMemo(
    () =>
      history.map((h) => ({
        date: h.date,
        label: new Date(h.date).toLocaleDateString("vi-VN", {
          day: "2-digit",
          month: "2-digit",
        }),
        price: h.price,
      })),
    [history]
  );

  const firstPrice = chartData[0]?.price;
  const lastPrice = chartData[chartData.length - 1]?.price;
  const change = firstPrice && lastPrice ? lastPrice - firstPrice : 0;
  const changePercent = firstPrice ? (change / firstPrice) * 100 : 0;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl shadow-2xl w-full max-w-3xl max-h-[90vh] overflow-y-auto border border-slate-100"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">{symbol}</h2>
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
          {loading ? (
            <div className="text-slate-500 py-8 text-center">Đang tải...</div>
          ) : error ? (
            <div className="text-rose-500 py-8 text-center">{error}</div>
          ) : (
            <>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="p-4 rounded-xl bg-slate-50">
                  <p className="text-xs text-slate-500 mb-1">Giá / NAV</p>
                  <p className="text-lg font-semibold text-slate-900 font-mono">
                    {lastPrice ? formatCurrency(lastPrice) : "—"}
                  </p>
                </div>
                <div className="p-4 rounded-xl bg-slate-50">
                  <p className="text-xs text-slate-500 mb-1">Biến động (3 tháng)</p>
                  <p
                    className={`text-lg font-semibold font-mono ${change >= 0 ? "text-accent-emerald" : "text-accent-rose"
                      }`}
                  >
                    {change ? formatCurrency(change) : "—"}
                  </p>
                </div>
                <div className="p-4 rounded-xl bg-slate-50">
                  <p className="text-xs text-slate-500 mb-1">% Biến động</p>
                  <p
                    className={`text-lg font-semibold font-mono ${changePercent >= 0 ? "text-accent-emerald" : "text-accent-rose"
                      }`}
                  >
                    {formatPercent(changePercent)}
                  </p>
                </div>
                <div className="p-4 rounded-xl bg-slate-50">
                  <p className="text-xs text-slate-500 mb-1">Sàn / Nguồn</p>
                  <p className="text-lg font-semibold text-slate-900">{exchange}</p>
                </div>
              </div>

              {fundDetail && (
                <div className="p-4 rounded-xl bg-slate-50 space-y-2">
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    Thông tin quỹ
                  </p>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                    {fundDetail.fund_type && (
                      <div>
                        <span className="text-slate-500">Loại quỹ:</span>{" "}
                        <span className="font-medium text-slate-900">{fundDetail.fund_type}</span>
                      </div>
                    )}
                    {fundDetail.owner && (
                      <div>
                        <span className="text-slate-500">Công ty quản lý:</span>{" "}
                        <span className="font-medium text-slate-900">{fundDetail.owner}</span>
                      </div>
                    )}
                    {fundDetail.management_fee !== undefined && (
                      <div>
                        <span className="text-slate-500">Phí quản lý:</span>{" "}
                        <span className="font-medium text-slate-900">
                          {fundDetail.management_fee}%
                        </span>
                      </div>
                    )}
                    {fundDetail.inception_date && (
                      <div>
                        <span className="text-slate-500">Ngày thành lập:</span>{" "}
                        <span className="font-medium text-slate-900">
                          {new Date(fundDetail.inception_date).toLocaleDateString("vi-VN")}
                        </span>
                      </div>
                    )}
                    {fundDetail.vsd_fee_id && (
                      <div>
                        <span className="text-slate-500">Mã VSD:</span>{" "}
                        <span className="font-medium text-slate-900">{fundDetail.vsd_fee_id}</span>
                      </div>
                    )}
                    {fundDetail.nav_update_at && (
                      <div>
                        <span className="text-slate-500">Cập nhật NAV:</span>{" "}
                        <span className="font-medium text-slate-900">
                          {new Date(fundDetail.nav_update_at).toLocaleDateString("vi-VN")}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              )}

              <div className="h-72">
                <p className="text-sm font-semibold text-slate-700 mb-3">Biến động giá 3 tháng</p>
                {chartData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                      <XAxis dataKey="label" tick={{ fontSize: 12, fill: "#64748b" }} />
                      <YAxis
                        tick={{ fontSize: 12, fill: "#64748b" }}
                        tickFormatter={(v: number) => formatCurrency(v).replace("₫", "")}
                        width={80}
                      />
                      <Tooltip
                        contentStyle={{
                          background: "rgba(255, 255, 255, 0.95)",
                          border: "1px solid rgba(15, 23, 42, 0.08)",
                          borderRadius: "12px",
                          color: "#1e293b",
                        }}
                        formatter={(value: number) => [formatCurrency(value), "Giá / NAV"]}
                        labelFormatter={(label: string) => `Ngày ${label}`}
                      />
                      <Line
                        type="monotone"
                        dataKey="price"
                        stroke={changePercent >= 0 ? "#10b981" : "#f43f5e"}
                        strokeWidth={2}
                        dot={false}
                        activeDot={{ r: 5 }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex items-center justify-center h-full text-slate-500">
                    Không có dữ liệu biểu đồ
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
