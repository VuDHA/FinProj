import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, Check, X } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { getNotifications, resolveAlert, type PriceAlertNotification } from "../api/alerts";
import { useToast } from "../contexts/ToastContext";
import { labels } from "../i18n/vi";
import { formatCurrency } from "../lib/utils";
import { Value } from "./Value";

export function PriceAlertsBell() {
  const qc = useQueryClient();
  const { showToast } = useToast();
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const notifications = useQuery({
    queryKey: ["price-alerts-notifications"],
    queryFn: getNotifications,
  });

  const resolve = useMutation({
    mutationFn: resolveAlert,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["price-alerts-notifications"] });
      qc.invalidateQueries({ queryKey: ["price-alerts"] });
      showToast("Đã giải quyết cảnh báo", "success");
    },
    onError: (error: any) => {
      showToast(error?.message || "Không thể giải quyết", "error");
    },
  });

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const count = notifications.data?.length ?? 0;

  const handleResolve = (id: number) => {
    resolve.mutate(id);
  };

  return (
    <div ref={containerRef} className="fixed top-4 right-4 z-50">
      <button
        onClick={() => setOpen((prev) => !prev)}
        className="relative p-2.5 rounded-xl bg-white/80 border border-fintech-border shadow-lg shadow-slate-900/5 backdrop-blur-md text-slate-700 hover:text-slate-900 hover:bg-white transition-colors"
        aria-label={labels.priceAlerts.notifications}
      >
        <Bell className="w-5 h-5" />
        {count > 0 && (
          <span className="absolute -top-1 -right-1 flex items-center justify-center min-w-[18px] h-[18px] px-1 rounded-full bg-rose-500 text-white text-[10px] font-bold border-2 border-white">
            {count}
          </span>
        )}
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -8, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.95 }}
            transition={{ duration: 0.15 }}
            className="absolute right-0 z-50 mt-2 w-80 sm:w-96 rounded-xl border border-fintech-border bg-white shadow-xl shadow-slate-900/10 overflow-hidden"
          >
            <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100 bg-slate-50/50">
              <h3 className="font-display font-semibold text-slate-900">{labels.priceAlerts.notifications}</h3>
              <button
                onClick={() => setOpen(false)}
                className="p-1 rounded-md text-slate-400 hover:text-slate-600 hover:bg-slate-200/50 transition-colors"
                aria-label={labels.common.close}
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="max-h-[60vh] overflow-y-auto">
              {notifications.isLoading && (
                <div className="p-4 text-sm text-slate-500">{labels.common.loading}</div>
              )}
              {!notifications.isLoading && count === 0 && (
                <div className="p-6 text-center text-sm text-slate-500">
                  {labels.priceAlerts.noNotifications}
                </div>
              )}
              {notifications.data?.map((n: PriceAlertNotification) => (
                <div
                  key={n.id}
                  className="flex items-start gap-3 p-4 border-b border-slate-100 last:border-b-0 hover:bg-slate-50/50 transition-colors"
                >
                  <div
                    className={`mt-0.5 p-1.5 rounded-lg ${n.type === "STOP_LOSS" ? "bg-rose-100 text-rose-600" : "bg-emerald-100 text-emerald-600"
                      }`}
                  >
                    <Check className="w-3.5 h-3.5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-900 truncate">{n.message}</p>
                    <p className="text-xs text-slate-500 mt-0.5">
                      {labels.priceAlerts.currentPrice}:{" "}
                      <Value value={n.current_price} formatter={formatCurrency} className="value-text" />
                    </p>
                  </div>
                  <button
                    onClick={() => handleResolve(n.id)}
                    disabled={resolve.isPending}
                    className="btn-xs btn-primary whitespace-nowrap"
                  >
                    {labels.priceAlerts.resolve}
                  </button>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
