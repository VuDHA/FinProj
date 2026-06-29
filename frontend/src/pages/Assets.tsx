import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import API from "../api/client";
import { ErrorMessage } from "../components/ErrorMessage";
import { FintechCard } from "../components/ui/FintechCard";
import { SectionHeader } from "../components/ui/SectionHeader";
import { SourceSelect } from "../components/SourceSelect";
import { InfoTooltip } from "../components/InfoTooltip";
import { labels } from "../i18n/vi";

const TYPES = ["STOCK", "FUND", "ETF", "GOLD", "CRYPTO"];

const typeColor: Record<string, string> = {
  STOCK: "bg-accent-blue/10 text-accent-blue ring-accent-blue/20",
  FUND: "bg-accent-violet/10 text-accent-violet ring-accent-violet/20",
  ETF: "bg-accent-cyan/10 text-accent-cyan ring-accent-cyan/20",
  GOLD: "bg-accent-amber/10 text-accent-amber ring-accent-amber/20",
  CRYPTO: "bg-accent-emerald/10 text-accent-emerald ring-accent-emerald/20",
};

export function Assets() {
  const qc = useQueryClient();
  const [form, setForm] = useState({
    symbol: "",
    name: "",
    type: "STOCK",
    exchange: "",
    currency: "VND",
    source: null as string | null,
  });

  const assets = useQuery({
    queryKey: ["assets"],
    queryFn: async () => (await API.get("/assets/")).data,
  });

  const create = useMutation({
    mutationFn: () => API.post("/assets/", form),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["assets"] });
      setForm({ symbol: "", name: "", type: "STOCK", exchange: "", currency: "VND", source: null });
    },
  });

  const remove = useMutation({
    mutationFn: (id: number) => API.delete(`/assets/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["assets"] }),
  });

  return (
    <div className="space-y-6">
      {assets.isError && <ErrorMessage error={assets.error} retry={() => assets.refetch()} />}
      {create.isError && <ErrorMessage error={create.error} retry={() => create.mutate()} />}
      {remove.isError && <ErrorMessage error={remove.error} retry={() => remove.reset()} />}
      <SectionHeader title={labels.assets.title} />

      <FintechCard delay={0.1}>
        <h3 className="card-title mb-4">{labels.assets.addAsset}</h3>
        <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
          <div className="relative">
            <input
              placeholder={labels.assets.symbol}
              className="input-fintech pr-10"
              value={form.symbol}
              onChange={(e) => setForm({ ...form, symbol: e.target.value.toUpperCase() })}
            />
            <span className="absolute right-3 top-1/2 -translate-y-1/2">
              <InfoTooltip content={labels.tooltips.assetSymbol} position="right" />
            </span>
          </div>
          <div className="relative">
            <input
              placeholder={labels.assets.name}
              className="input-fintech pr-10"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
            <span className="absolute right-3 top-1/2 -translate-y-1/2">
              <InfoTooltip content={labels.tooltips.assetName} position="right" />
            </span>
          </div>
          <div className="relative">
            <select
              className="input-fintech pr-10"
              value={form.type}
              onChange={(e) => setForm({ ...form, type: e.target.value })}
            >
              {TYPES.map((t) => (
                <option key={t} value={t}>
                  {labels.assetTypes[t as keyof typeof labels.assetTypes]}
                </option>
              ))}
            </select>
            <span className="absolute right-8 top-1/2 -translate-y-1/2">
              <InfoTooltip content={labels.tooltips.assetType} position="right" />
            </span>
          </div>
          <div className="relative">
            <input
              placeholder={labels.assets.exchange}
              className="input-fintech pr-10"
              value={form.exchange}
              onChange={(e) => setForm({ ...form, exchange: e.target.value })}
            />
            <span className="absolute right-3 top-1/2 -translate-y-1/2">
              <InfoTooltip content={labels.tooltips.assetExchange} position="right" />
            </span>
          </div>
          <div className="relative">
            <SourceSelect
              assetType={form.type}
              value={form.source}
              onChange={(value) => setForm({ ...form, source: value })}
            />
            <span className="absolute right-8 top-1/2 -translate-y-1/2">
              <InfoTooltip content={labels.sources.assetSourceHint} position="right" />
            </span>
          </div>
        </div>
        <button
          onClick={() => create.mutate()}
          disabled={!form.symbol || !form.name || create.isPending}
          className="btn-primary mt-3"
        >
          <Plus className="w-4 h-4" />
          {labels.assets.add}
        </button>
      </FintechCard>

      <FintechCard delay={0.15}>
        <div className="overflow-x-auto scrollbar-thin">
          <table className="table-fintech">
            <thead>
              <tr>
                <th className="text-left">
                  {labels.assets.symbol}
                  <InfoTooltip content={labels.tooltips.assetSymbol} />
                </th>
                <th className="text-left">
                  {labels.assets.name}
                  <InfoTooltip content={labels.tooltips.assetName} />
                </th>
                <th className="text-left">
                  {labels.assets.type}
                  <InfoTooltip content={labels.tooltips.assetType} />
                </th>
                <th className="text-left">
                  {labels.assets.exchange}
                  <InfoTooltip content={labels.tooltips.assetExchange} />
                </th>
                <th className="text-left">
                  {labels.sources.activeSource}
                  <InfoTooltip content={labels.sources.assetSourceHint} />
                </th>
                <th className="text-right">{labels.assets.actions}</th>
              </tr>
            </thead>
            <tbody>
              {assets.data?.map((asset: any) => (
                <tr key={asset.id}>
                  <td className="font-display font-semibold text-slate-900">{asset.symbol}</td>
                  <td className="text-slate-700">{asset.name}</td>
                  <td>
                    <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${typeColor[asset.type] ?? "bg-slate-200 text-slate-700"}`}>
                      {labels.assetTypes[asset.type as keyof typeof labels.assetTypes] ?? asset.type}
                    </span>
                  </td>
                  <td className="text-slate-500">{asset.exchange || "-"}</td>
                  <td className="text-slate-500">
                    {asset.source ? (
                      <span className="inline-flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-accent-violet" />
                        {asset.source}
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-slate-300" />
                        {labels.sources.default}
                      </span>
                    )}
                  </td>
                  <td className="text-right">
                    <button
                      onClick={() => remove.mutate(asset.id)}
                      disabled={remove.isPending}
                      className="inline-flex items-center justify-center p-2 rounded-lg text-accent-rose hover:bg-accent-rose/10 transition-colors disabled:opacity-50"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))}
              {assets.data?.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-slate-500">
                    {labels.assets.noAssets}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </FintechCard>
    </div>
  );
}
