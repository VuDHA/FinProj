import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Check, Download, RefreshCw, Save, Upload } from "lucide-react";
import API from "../api/client";
import { ErrorMessage } from "../components/ErrorMessage";
import { FintechCard } from "../components/ui/FintechCard";
import { SectionHeader } from "../components/ui/SectionHeader";
import { labels } from "../i18n/vi";
import { formatCurrency } from "../lib/utils";

const API_KEYS = [
  { key: "vndirect_api_key", label: labels.settings.vndirectKey },
  { key: "ssi_consumer_key", label: labels.settings.ssiKey },
  { key: "ssi_consumer_secret", label: labels.settings.ssiSecret },
  { key: "fireant_api_key", label: labels.settings.fireantKey },
];

const ASSET_TYPES = ["STOCK", "FUND", "ETF", "GOLD", "CRYPTO"];

export function Settings() {
  const qc = useQueryClient();

  const settingsQuery = useQuery({
    queryKey: ["settings"],
    queryFn: async () => (await API.get("/settings/")).data,
  });

  const goldFx = useQuery({
    queryKey: ["gold-fx"],
    queryFn: async () => (await API.get("/gold-fx/")).data,
  });

  const targets = useQuery({
    queryKey: ["allocation-targets"],
    queryFn: async () => (await API.get("/settings/allocation-targets/")).data,
  });

  const save = useMutation({
    mutationFn: (payload: { key: string; value: string }) => API.post("/settings/", payload),
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: ["settings"] });
      setSavedKey(variables.key);
      setTimeout(() => setSavedKey(null), 2000);
    },
  });

  const saveTargets = useMutation({
    mutationFn: (payload: Array<{ type: string; target_percent: number }>) =>
      API.post("/settings/allocation-targets/", payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["allocation-targets"] }),
  });

  const importAssets = useMutation({
    mutationFn: async (file: File) => {
      const form = new FormData();
      form.append("file", file);
      return (await API.post("/import-export/import/assets", form)).data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["assets"] });
    },
  });

  const importTransactions = useMutation({
    mutationFn: async (file: File) => {
      const form = new FormData();
      form.append("file", file);
      return (await API.post("/import-export/import/transactions", form)).data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["transactions"] });
      qc.invalidateQueries({ queryKey: ["portfolio"] });
    },
  });

  const [values, setValues] = useState<Record<string, string>>({});
  const [targetValues, setTargetValues] = useState<Record<string, string>>({});
  const [savedKey, setSavedKey] = useState<string | null>(null);

  const getValue = (key: string) => {
    if (values[key] !== undefined) return values[key];
    const found = settingsQuery.data?.find((s: any) => s.key === key);
    return found ? found.value : "";
  };

  const getTarget = (type: string) => {
    if (targetValues[type] !== undefined) return targetValues[type];
    const found = targets.data?.find((t: any) => t.type === type);
    return found ? String(found.target_percent) : "0";
  };

  const totalTarget = ASSET_TYPES.reduce((sum, t) => sum + (Number(getTarget(t)) || 0), 0);

  const handleSaveTargets = () => {
    const payload = ASSET_TYPES.map((type) => ({
      type,
      target_percent: Number(getTarget(type)) || 0,
    }));
    saveTargets.mutate(payload);
  };

  const handleExport = (type: "assets" | "transactions") => {
    window.open(`/api/v1/import-export/export/${type}`, "_blank");
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>, type: "assets" | "transactions") => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (type === "assets") {
      importAssets.mutate(file);
    } else {
      importTransactions.mutate(file);
    }
  };

  return (
    <div className="space-y-6">
      {settingsQuery.isError && <ErrorMessage error={settingsQuery.error} retry={() => settingsQuery.refetch()} />}
      {goldFx.isError && <ErrorMessage error={goldFx.error} retry={() => goldFx.refetch()} />}
      {targets.isError && <ErrorMessage error={targets.error} retry={() => targets.refetch()} />}
      {save.isError && <ErrorMessage error={save.error} retry={() => save.reset()} />}
      {saveTargets.isError && <ErrorMessage error={saveTargets.error} retry={() => saveTargets.reset()} />}
      {importAssets.isError && <ErrorMessage error={importAssets.error} retry={() => importAssets.reset()} />}
      {importTransactions.isError && <ErrorMessage error={importTransactions.error} retry={() => importTransactions.reset()} />}
      <SectionHeader title={labels.settings.title} />

      <FintechCard delay={0.1}>
        <h3 className="card-title mb-4">{labels.settings.apiKeys}</h3>
        <div className="space-y-3">
          {API_KEYS.map((item) => (
            <div key={item.key} className="grid grid-cols-1 md:grid-cols-4 gap-3 items-center">
              <label className="text-sm font-medium text-slate-500 md:col-span-1">{item.label}</label>
              <input
                type="password"
                className="md:col-span-2 input-fintech"
                value={getValue(item.key)}
                onChange={(e) => {
                  setValues({ ...values, [item.key]: e.target.value });
                  if (savedKey === item.key) setSavedKey(null);
                }}
                placeholder={item.label}
              />
              <button
                onClick={() => save.mutate({ key: item.key, value: getValue(item.key) })}
                disabled={save.isPending}
                className="md:col-span-1 btn-primary"
              >
                {save.isPending ? (
                  labels.settings.saving
                ) : savedKey === item.key ? (
                  <>
                    <Check className="w-4 h-4" />
                    {labels.settings.saved}
                  </>
                ) : (
                  <>
                    <Save className="w-4 h-4" />
                    {labels.settings.save}
                  </>
                )}
              </button>
            </div>
          ))}
        </div>
      </FintechCard>

      <FintechCard delay={0.15}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="card-title">{labels.settings.goldFx}</h3>
          <button
            onClick={() => qc.invalidateQueries({ queryKey: ["gold-fx"] })}
            className="btn-secondary"
          >
            <RefreshCw className={`w-4 h-4 ${goldFx.isFetching ? "animate-spin" : ""}`} />
            {labels.settings.refresh}
          </button>
        </div>

        {goldFx.isLoading && <div className="text-slate-500">{labels.common.loading}</div>}

        {goldFx.data && (
          <div className="space-y-6">
            <div>
              <h4 className="font-display font-semibold text-slate-900 mb-3">{labels.settings.gold}</h4>
              {goldFx.data.gold.length > 0 ? (
                <div className="overflow-x-auto scrollbar-thin">
                  <table className="table-fintech">
                    <thead>
                      <tr>
                        <th className="text-left">{labels.settings.source}</th>
                        <th className="text-right">{labels.settings.buy}</th>
                        <th className="text-right">{labels.settings.sell}</th>
                        <th className="text-right">{labels.settings.updated}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {goldFx.data.gold.map((rate: any, idx: number) => (
                        <tr key={idx}>
                          <td className="font-medium text-slate-900">{rate.source}</td>
                          <td className="text-right font-mono">{formatCurrency(rate.buy)}</td>
                          <td className="text-right font-mono">{formatCurrency(rate.sell)}</td>
                          <td className="text-right font-mono text-slate-500">{rate.updated_at ?? "-"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="text-slate-500">{labels.settings.empty}</div>
              )}
            </div>

            <div>
              <h4 className="font-display font-semibold text-slate-900 mb-3">{labels.settings.fx}</h4>
              {goldFx.data.fx.length > 0 ? (
                <div className="overflow-x-auto scrollbar-thin">
                  <table className="table-fintech">
                    <thead>
                      <tr>
                        <th className="text-left">{labels.settings.currency}</th>
                        <th className="text-right">{labels.settings.buy}</th>
                        <th className="text-right">{labels.settings.transfer}</th>
                        <th className="text-right">{labels.settings.sell}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {goldFx.data.fx.map((rate: any, idx: number) => (
                        <tr key={idx}>
                          <td className="font-medium text-slate-900">{rate.currency}</td>
                          <td className="text-right font-mono">{formatCurrency(rate.buy)}</td>
                          <td className="text-right font-mono">{formatCurrency(rate.transfer)}</td>
                          <td className="text-right font-mono">{formatCurrency(rate.sell)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="text-slate-500">{labels.settings.empty}</div>
              )}
            </div>
          </div>
        )}
      </FintechCard>

      <FintechCard delay={0.2}>
        <h3 className="card-title mb-4">{labels.settings.allocationTargets}</h3>
        <div className="space-y-3">
          {ASSET_TYPES.map((type) => (
            <div key={type} className="grid grid-cols-1 md:grid-cols-4 gap-3 items-center">
              <label className="text-sm font-medium text-slate-500 md:col-span-1">
                {labels.assetTypes[type as keyof typeof labels.assetTypes] ?? type}
              </label>
              <input
                type="number"
                className="md:col-span-2 input-fintech"
                value={getTarget(type)}
                onChange={(e) => setTargetValues({ ...targetValues, [type]: e.target.value })}
                placeholder="%"
              />
              <span className="md:col-span-1 text-sm text-slate-500">%</span>
            </div>
          ))}
        </div>
        <div className="flex items-center justify-between mt-4">
          <div className={`text-sm ${totalTarget > 100 ? "text-accent-rose" : "text-slate-500"}`}>
            {labels.rebalance.targetAllocation}: {totalTarget.toFixed(2)}%
          </div>
          <button
            onClick={handleSaveTargets}
            disabled={totalTarget > 100 || saveTargets.isPending}
            className="btn-primary"
          >
            <Save className="w-4 h-4" />
            {saveTargets.isPending ? labels.settings.saving : labels.settings.save}
          </button>
        </div>
      </FintechCard>

      <FintechCard delay={0.25}>
        <h3 className="card-title mb-4">{labels.settings.importExport}</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-3">
            <h4 className="font-medium text-slate-700">{labels.common.save}</h4>
            <div className="flex gap-2">
              <button onClick={() => handleExport("assets")} className="btn-secondary">
                <Download className="w-4 h-4" />
                {labels.settings.exportAssets}
              </button>
              <button onClick={() => handleExport("transactions")} className="btn-secondary">
                <Download className="w-4 h-4" />
                {labels.settings.exportTransactions}
              </button>
            </div>
          </div>
          <div className="space-y-3">
            <h4 className="font-medium text-slate-700">{labels.common.add}</h4>
            <div className="flex gap-2">
              <label className="btn-secondary cursor-pointer">
                <Upload className="w-4 h-4" />
                {labels.settings.importAssets}
                <input
                  type="file"
                  accept=".csv"
                  className="hidden"
                  onChange={(e) => handleFileChange(e, "assets")}
                />
              </label>
              <label className="btn-secondary cursor-pointer">
                <Upload className="w-4 h-4" />
                {labels.settings.importTransactions}
                <input
                  type="file"
                  accept=".csv"
                  className="hidden"
                  onChange={(e) => handleFileChange(e, "transactions")}
                />
              </label>
            </div>
          </div>
        </div>

        {(importAssets.data || importTransactions.data) && (
          <div className="mt-4 p-3 rounded-lg bg-slate-50 text-sm space-y-1">
            <div className="font-medium text-slate-700">{labels.settings.importResult}</div>
            {importAssets.data && (
              <div className="text-slate-600">
                {labels.settings.importAssets}: {labels.settings.created} {importAssets.data.created},
                {" "}{labels.settings.skipped} {importAssets.data.skipped},
                {" "}{labels.settings.errors} {importAssets.data.errors.length}
              </div>
            )}
            {importTransactions.data && (
              <div className="text-slate-600">
                {labels.settings.importTransactions}: {labels.settings.created} {importTransactions.data.created},
                {" "}{labels.settings.skipped} {importTransactions.data.skipped},
                {" "}{labels.settings.errors} {importTransactions.data.errors.length}
              </div>
            )}
          </div>
        )}
      </FintechCard>
    </div>
  );
}
