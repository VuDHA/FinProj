import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, Plus, Trash2, TrendingDown, TrendingUp } from "lucide-react";
import API from "../api/client";
import {
  createAlert,
  deleteAlert,
  getAlerts,
  getNotifications,
  resolveAlert,
  type CreatePriceAlertRequest,
  type PriceAlert,
  type PriceAlertNotification,
} from "../api/alerts";
import { FintechCard } from "./ui/FintechCard";
import { SectionHeader } from "./ui/SectionHeader";
import { useToast } from "../contexts/ToastContext";
import { labels } from "../i18n/vi";
import { formatCurrency } from "../lib/utils";
import { Value } from "./Value";
import { FormattedNumberInput } from "./FormattedNumberInput";

export function PriceAlertsSection() {
  const qc = useQueryClient();
  const { showToast } = useToast();
  const [form, setForm] = useState<CreatePriceAlertRequest>({
    asset_id: 0,
    type: "STOP_LOSS",
    value_type: "VALUE",
    value: 0,
  });

  const assets = useQuery({
    queryKey: ["assets"],
    queryFn: async () => (await API.get("/assets/")).data,
  });

  const alerts = useQuery({
    queryKey: ["price-alerts"],
    queryFn: getAlerts,
  });

  const notifications = useQuery({
    queryKey: ["price-alerts-notifications"],
    queryFn: getNotifications,
  });

  const create = useMutation({
    mutationFn: createAlert,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["price-alerts"] });
      qc.invalidateQueries({ queryKey: ["price-alerts-notifications"] });
      setForm({ asset_id: 0, type: "STOP_LOSS", value_type: "VALUE", value: 0 });
      showToast("Đã thêm cảnh báo", "success");
    },
    onError: (error: any) => {
      showToast(error?.message || "Không thể thêm cảnh báo", "error");
    },
  });

  const remove = useMutation({
    mutationFn: deleteAlert,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["price-alerts"] });
      qc.invalidateQueries({ queryKey: ["price-alerts-notifications"] });
      showToast("Đã xóa cảnh báo", "success");
    },
  });

  const resolve = useMutation({
    mutationFn: resolveAlert,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["price-alerts"] });
      qc.invalidateQueries({ queryKey: ["price-alerts-notifications"] });
      showToast("Đã giải quyết cảnh báo", "success");
    },
  });

  const handleSubmit = () => {
    if (!form.asset_id || form.value <= 0) {
      showToast("Vui lòng chọn tài sản và nhập giá trị hợp lệ", "error");
      return;
    }
    create.mutate(form);
  };

  const activeAlerts = alerts.data?.filter((a: PriceAlert) => a.is_active) ?? [];
  const notificationCount = notifications.data?.length ?? 0;

  return (
    <FintechCard delay={0.3}>
      <SectionHeader
        title={labels.priceAlerts.title}
        subtitle={`${notificationCount} ${labels.priceAlerts.notifications.toLowerCase()}`}
      >
        <div className="p-1.5 rounded-lg bg-accent-amber/10 text-accent-amber">
          <Bell className="w-4 h-4" />
        </div>
      </SectionHeader>

      <div className="mt-4 grid grid-cols-1 md:grid-cols-5 gap-3">
        <select
          className="input-fintech md:col-span-2"
          value={form.asset_id || ""}
          onChange={(e) => setForm({ ...form, asset_id: Number(e.target.value) })}
        >
          <option value="">{labels.priceAlerts.asset}</option>
          {assets.data?.map((asset: any) => (
            <option key={asset.id} value={asset.id}>
              {asset.symbol} - {asset.name}
            </option>
          ))}
        </select>
        <select
          className="input-fintech"
          value={form.type}
          onChange={(e) => setForm({ ...form, type: e.target.value as any })}
        >
          <option value="STOP_LOSS">{labels.priceAlerts.stopLoss}</option>
          <option value="TAKE_PROFIT">{labels.priceAlerts.takeProfit}</option>
        </select>
        <select
          className="input-fintech"
          value={form.value_type}
          onChange={(e) => setForm({ ...form, value_type: e.target.value as any })}
        >
          <option value="VALUE">{labels.priceAlerts.hardValue}</option>
          <option value="PERCENT">{labels.priceAlerts.percent}</option>
        </select>
        <div className="flex gap-2">
          <FormattedNumberInput
            mode={form.value_type === "PERCENT" ? "percent" : "currency"}
            decimals={form.value_type === "PERCENT" ? 2 : 0}
            min={0}
            placeholder={form.value_type === "PERCENT" ? "%" : labels.priceAlerts.value}
            className="input-fintech flex-1"
            value={form.value || ""}
            onChange={(value) => setForm({ ...form, value: Number(value) })}
          />
          <button
            onClick={handleSubmit}
            disabled={create.isPending}
            className="btn-primary px-3"
            aria-label={labels.priceAlerts.addAlert}
          >
            <Plus className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="mt-4 space-y-3">
        {notifications.data?.map((n: PriceAlertNotification) => (
          <div
            key={n.id}
            className={`flex items-start gap-3 p-3 rounded-xl border ${n.type === "STOP_LOSS"
              ? "border-rose-100 bg-rose-50/50"
              : "border-emerald-100 bg-emerald-50/50"
              }`}
          >
            <div
              className={`p-1.5 rounded-lg ${n.type === "STOP_LOSS" ? "bg-rose-100 text-rose-600" : "bg-emerald-100 text-emerald-600"
                }`}
            >
              {n.type === "STOP_LOSS" ? <TrendingDown className="w-4 h-4" /> : <TrendingUp className="w-4 h-4" />}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-slate-900 truncate">{n.message}</p>
              <p className="text-xs text-slate-500 mt-0.5">
                {labels.priceAlerts.currentPrice}:{" "}
                <Value value={n.current_price} formatter={formatCurrency} className="value-text" />
              </p>
            </div>
            <button
              onClick={() => resolve.mutate(n.id)}
              disabled={resolve.isPending}
              className="btn-xs btn-primary whitespace-nowrap"
            >
              {labels.priceAlerts.resolve}
            </button>
          </div>
        ))}

        {activeAlerts.length === 0 && !notifications.data?.length && (
          <div className="text-sm text-slate-500 py-2">{labels.priceAlerts.noAlerts}</div>
        )}

        {activeAlerts.map((alert: PriceAlert) => (
          <div
            key={alert.id}
            className="flex items-center justify-between p-3 rounded-xl border border-slate-100 bg-slate-50/50"
          >
            <div className="flex items-center gap-2 min-w-0">
              <span
                className={`text-xs font-medium px-2 py-0.5 rounded-full ${alert.type === "STOP_LOSS"
                  ? "bg-rose-100 text-rose-700"
                  : "bg-emerald-100 text-emerald-700"
                  }`}
              >
                {alert.type === "STOP_LOSS" ? labels.priceAlerts.stopLoss : labels.priceAlerts.takeProfit}
              </span>
              <span className="text-sm font-medium text-slate-900 truncate">
                {alert.symbol} — {alert.value_type === "PERCENT" ? `${alert.value}%` : formatCurrency(alert.value)}
              </span>
              {alert.value_type === "PERCENT" && alert.reference_price && (
                <span className="text-xs text-slate-500 hidden sm:inline value-text">
                  ({labels.priceAlerts.referencePrice}: {formatCurrency(alert.reference_price)})
                </span>
              )}
            </div>
            <button
              onClick={() => remove.mutate(alert.id)}
              disabled={remove.isPending}
              className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-colors"
              aria-label={labels.common.delete}
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        ))}
      </div>
    </FintechCard>
  );
}
