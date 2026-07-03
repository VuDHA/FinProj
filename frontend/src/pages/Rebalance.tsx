import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Bot, Save, Scale } from "lucide-react";
import API from "../api/client";
import { getRebalanceInsight } from "../api/ai";
import { AiGenerateButton } from "../components/AiGenerateButton";
import { AiInsightCard } from "../components/AiInsightCard";
import { ErrorMessage } from "../components/ErrorMessage";
import { InfoTooltip } from "../components/InfoTooltip";
import { AnimatedNumber } from "../components/ui/AnimatedNumber";
import { FintechCard } from "../components/ui/FintechCard";
import { SectionHeader } from "../components/ui/SectionHeader";
import { TrendBadge } from "../components/ui/TrendBadge";
import { useAiInsight } from "../hooks/useAiInsight";
import { labels } from "../i18n/vi";
import { formatCurrency, formatPercent } from "../lib/utils";

type AssetTypeConfig = {
  label: string;
  fields: string[];
  marketPrice: boolean;
};

type AssetTypeMap = Record<string, AssetTypeConfig>;

export function Rebalance() {
  const qc = useQueryClient();

  const assetTypes = useQuery<AssetTypeMap>({
    queryKey: ["asset-types"],
    queryFn: async () => (await API.get("/settings/asset-types")).data.types,
  });

  const typeConfig = useMemo(() => assetTypes.data || {}, [assetTypes.data]);
  const allTypeCodes = useMemo(() => Object.keys(typeConfig), [typeConfig]);

  const typeLabel = (code: string) =>
    typeConfig[code]?.label || labels.assetTypes[code as keyof typeof labels.assetTypes] || code;

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

  const totalTarget = allTypeCodes.reduce(
    (sum, t) => sum + (Number(getTarget(t)) || 0),
    0
  );

  const handleSave = () => {
    const payload = allTypeCodes.map((t) => ({
      type: t,
      target_percent: Number(getTarget(t)) || 0,
    }));
    save.mutate(payload);
  };

  const data = rebalance.data;

  const rebalanceInsight = useAiInsight({
    taskName: "rebalance_insight",
    fetcher: getRebalanceInsight,
  });

  return (
    <div className="space-y-6">
      {assetTypes.isError && <ErrorMessage error={assetTypes.error} retry={() => assetTypes.refetch()} />}
      {rebalance.isError && <ErrorMessage error={rebalance.error} retry={() => rebalance.refetch()} />}
      {targets.isError && <ErrorMessage error={targets.error} retry={() => targets.refetch()} />}
      {save.isError && <ErrorMessage error={save.error} retry={() => save.reset()} />}
      <SectionHeader title={labels.rebalance.title} />

      <FintechCard delay={0.1}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="card-title inline-flex items-center">
            <Scale className="w-4 h-4 inline mr-2" />
            {labels.rebalance.currentAllocation}
            <InfoTooltip content={labels.tooltips.rebalanceCurrent} />
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
                <th className="text-left">
                  {labels.assets.type}
                  <InfoTooltip content={labels.tooltips.assetType} />
                </th>
                <th className="text-right">
                  {labels.rebalance.currentAllocation}
                  <InfoTooltip content={labels.tooltips.rebalanceCurrent} />
                </th>
                <th className="text-right">
                  {labels.rebalance.targetAllocation}
                  <InfoTooltip content={labels.tooltips.rebalanceTarget} />
                </th>
                <th className="text-right">
                  {labels.rebalance.diff}
                  <InfoTooltip content={labels.tooltips.rebalanceDiff} />
                </th>
              </tr>
            </thead>
            <tbody>
              {allTypeCodes.map((type) => {
                const suggestion = data?.suggestions?.find((s: any) => s.type === type);
                const currentValue = suggestion?.current_value || 0;
                const currentPercent = suggestion?.current_percent || 0;
                const targetPercent = Number(getTarget(type)) || 0;
                const diff = (targetPercent - currentPercent);
                return (
                  <tr key={type}>
                    <td className="font-display font-semibold text-slate-900">
                      {typeLabel(type)}
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
        <h3 className="card-title mb-4 inline-flex items-center">
          {labels.rebalance.suggestedTrades}
          <InfoTooltip content={labels.tooltips.rebalanceSuggestion} />
        </h3>
        {data?.trades?.length > 0 ? (
          <div className="overflow-x-auto scrollbar-thin">
            <table className="table-fintech">
              <thead>
                <tr>
                  <th className="text-left">
                    {labels.market.symbol}
                    <InfoTooltip content={labels.tooltips.assetSymbol} />
                  </th>
                  <th className="text-left">
                    {labels.rebalance.action}
                    <InfoTooltip content={labels.tooltips.transactionType} />
                  </th>
                  <th className="text-right">
                    {labels.transactions.quantity}
                    <InfoTooltip content={labels.tooltips.transactionQuantity} />
                  </th>
                  <th className="text-right">
                    {labels.market.price}
                    <InfoTooltip content={labels.tooltips.transactionPrice} />
                  </th>
                  <th className="text-right">
                    {labels.rebalance.estimatedValue}
                    <InfoTooltip content={labels.tooltips.totalValue} />
                  </th>
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

      <FintechCard delay={0.3}>
        <div className="flex items-center justify-between mb-3">
          <h3 className="card-title inline-flex items-center gap-2">
            <Bot className="w-4 h-4 text-indigo-500" />
            Phân tích AI cân bằng
          </h3>
          <AiGenerateButton
            label="Phân tích"
            onClick={() => rebalanceInsight.generate()}
            loading={rebalanceInsight.loading}
          />
        </div>
        <AiInsightCard
          data={rebalanceInsight.data}
          loading={rebalanceInsight.loading}
          error={rebalanceInsight.error}
          onClose={rebalanceInsight.clear}
        />
      </FintechCard>
    </div>
  );
}
