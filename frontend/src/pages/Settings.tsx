import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { RefreshCw, Save } from "lucide-react";
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

  const save = useMutation({
    mutationFn: (payload: { key: string; value: string }) => API.post("/settings/", payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["settings"] }),
  });

  const [values, setValues] = useState<Record<string, string>>({});

  const getValue = (key: string) => {
    if (values[key] !== undefined) return values[key];
    const found = settingsQuery.data?.find((s: any) => s.key === key);
    return found ? found.value : "";
  };

  return (
    <div className="space-y-6">
      {settingsQuery.isError && <ErrorMessage error={settingsQuery.error} retry={() => settingsQuery.refetch()} />}
      {goldFx.isError && <ErrorMessage error={goldFx.error} retry={() => goldFx.refetch()} />}
      {save.isError && <ErrorMessage error={save.error} retry={() => save.reset()} />}
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
                onChange={(e) => setValues({ ...values, [item.key]: e.target.value })}
                placeholder={item.label}
              />
              <button
                onClick={() => save.mutate({ key: item.key, value: getValue(item.key) })}
                disabled={save.isPending}
                className="md:col-span-1 btn-primary"
              >
                <Save className="w-4 h-4" />
                {save.isPending ? labels.settings.saving : labels.settings.save}
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
    </div>
  );
}
