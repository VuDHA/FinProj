import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Save, Scale } from "lucide-react";
import API from "../api/client";
import { ErrorMessage } from "../components/ErrorMessage";
import { AnimatedNumber } from "../components/ui/AnimatedNumber";
import { FintechCard } from "../components/ui/FintechCard";
import { SectionHeader } from "../components/ui/SectionHeader";
import { TrendBadge } from "../components/ui/TrendBadge";
import { labels } from "../i18n/vi";
import { formatCurrency, formatPercent } from "../lib/utils";

const TYPES = ["STOCK", "FUND", "ETF", "GOLD", "CRYPTO"];

export function Rebalance() {
  const qc = useQueryClient();

  const rebalance = useQuery({
    queryKey: ["rebalance"],
    queryFn: async () => (await API.get("/rebalance/")).data,
  });

  const targets = useQuery({
    queryKey: ["allocation-targets"],
    queryFn: async () => (await API.get("/settings/allocation-targets/")).data,
  });

  const [targetMap, setTargetMap] = useState<Record<string, string>>({});

  const save = useMutation({
    mutationFn: (payload: Array<{ type: string; target_percent: number }>) =>
      API.post("/settings/allocation-targets/", payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["allocation-targets"] });
      qc.invalidateQueries({ queryKey: ["rebalance"] });
    },
  });

  const getTarget = (type: string) => {
    if (targetMap[type] !== undefined) return targetMap[type];
    const found = targets.data?.find((t: any) => t.type === type);
    return found ? String(found.target_percent) : "0";
  };

  const totalTarget = TYPES.reduce(
    (sum, t) => sum + (Number(getTarget(t)) || 0),
    0
  );

  const handleSave = () => {
    const payload = TYPES.map((t) => ({
      type: t,
      target_percent: Number(getTarget(t)) || 0,
    }));
    save.mutate(payload);
  };

  const data = rebalance.data;

  return (
    <div className="space-y-6">
      {rebalance.isError && <ErrorMessage error={rebalance.error} retry={() => rebalance.refetch()} />}
      {targets.isError && <ErrorMessage error={targets.error} retry={() => targets.refetch()} />}
      {save.isError && <ErrorMessage error={save.error} retry={() => save.reset()} />}
      <SectionHeader title={labels.rebalance.title} />

      <FintechCard delay={0.1}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="card-title">
            <Scale className="w-4 h-4 inline mr-2" />
            {labels.rebalance.currentAllocation}
          </h3>
          <div className="text-sm text-slate-500">
            {labels.market.totalValue}:{" "}
            <span className="font-mono font-semibold text-slate-900">
              <AnimatedNumber value={data?.total_value || 0} formatter={formatCurrency} />
            </span>
          </div>
        </div>

        <div className="overflow-x-auto scrollbar-thin">
          <table className="table-fintech">
            <thead>
              <tr>
                <th className="text-left">{labels.assets.type}</th>
                <th className="text-right">{labels.rebalance.currentAllocation}</th>
                <th className="text-right">{labels.rebalance.targetAllocation}</th>
                <th className="text-right">{labels.rebalance.diff}</th>
              </tr>
            </thead>
            <tbody>
              {TYPES.map((type) => {
                const suggestion = data?.suggestions?.find((s: any) => s.type === type);
                const currentValue = suggestion?.current_value || 0;
                const currentPercent = suggestion?.current_percent || 0;
                const targetPercent = Number(getTarget(type)) || 0;
                const diff = (targetPercent - currentPercent);
                return (
                  <tr key={type}>
                    <td className="font-display font-semibold text-slate-900">
                      {labels.assetTypes[type as keyof typeof labels.assetTypes] ?? type}
                    </td>
                    <td className="text-right">
                      <div className="font-mono text-slate-700">{formatCurrency(currentValue)}</div>
                      <div className="text-xs text-slate-500">{formatPercent(currentPercent)}</div>
                    </td>
                    <td className="text-right">
                      <input
                        type="number"
                        className="input-fintech w-24 text-right"
                        value={getTarget(type)}
                        onChange={(e) => setTargetMap({ ...targetMap, [type]: e.target.value })}
                      />
                    </td>
                    <td className="text-right">
                      <TrendBadge value={diff} />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <div className="flex items-center justify-between mt-4">
          <div className={`text-sm ${totalTarget > 100 ? "text-accent-rose" : "text-slate-500"}`}>
            {labels.rebalance.targetAllocation}: {totalTarget.toFixed(2)}%
            {totalTarget > 100 && (
              <span className="ml-2 text-accent-rose">{labels.rebalance.totalTargetMustBe100}</span>
            )}
          </div>
          <button
            onClick={handleSave}
            disabled={totalTarget > 100 || save.isPending}
            className="btn-primary"
          >
            <Save className="w-4 h-4" />
            {labels.rebalance.saveTargets}
          </button>
        </div>
      </FintechCard>

      <FintechCard delay={0.2}>
        <h3 className="card-title mb-4">{labels.rebalance.suggestedTrades}</h3>
        {data?.trades?.length > 0 ? (
          <div className="overflow-x-auto scrollbar-thin">
            <table className="table-fintech">
              <thead>
                <tr>
                  <th className="text-left">{labels.market.symbol}</th>
                  <th className="text-left">{labels.rebalance.action}</th>
                  <th className="text-right">{labels.transactions.quantity}</th>
                  <th className="text-right">{labels.market.price}</th>
                  <th className="text-right">{labels.rebalance.estimatedValue}</th>
                </tr>
              </thead>
              <tbody>
                {data.trades.map((trade: any) => (
                  <tr key={`${trade.symbol}-${trade.action}`}>
                    <td>
                      <div className="font-display font-semibold text-slate-900">{trade.symbol}</div>
                      <span className="text-xs text-slate-500">{trade.name}</span>
                    </td>
                    <td>
                      <span className={trade.action === "BUY" ? "badge-gain" : "badge-loss"}>
                        {trade.action === "BUY" ? labels.rebalance.buy : labels.rebalance.sell}
                      </span>
                    </td>
                    <td className="text-right font-mono">{trade.quantity.toFixed(4)}</td>
                    <td className="text-right font-mono">{formatCurrency(trade.estimated_price)}</td>
                    <td className="text-right font-mono">{formatCurrency(trade.estimated_value)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-slate-500 py-8">{labels.rebalance.noSuggestions}</div>
        )}
      </FintechCard>
    </div>
  );
}
