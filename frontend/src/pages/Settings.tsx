import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Download, RefreshCw, Save, Upload } from "lucide-react";
import API from "../api/client";
import { ErrorMessage } from "../components/ErrorMessage";
import { SmartImportDialog } from "../components/SmartImportDialog";
import { FintechCard } from "../components/ui/FintechCard";
import { SectionHeader } from "../components/ui/SectionHeader";
import { Skeleton } from "../components/ui/Skeleton";
import { SourceSelect } from "../components/SourceSelect";
import { InfoTooltip } from "../components/InfoTooltip";
import { useToast } from "../contexts/ToastContext";
import { labels } from "../i18n/vi";
import { formatCurrency } from "../lib/utils";

const ASSET_TYPES = ["STOCK", "FUND", "ETF", "GOLD", "CRYPTO"];

export function Settings() {
  const qc = useQueryClient();
  const { showToast } = useToast();
  const [smartImportType, setSmartImportType] = useState<"assets" | "transactions" | null>(null);

  const goldFx = useQuery({
    queryKey: ["gold-fx"],
    queryFn: async () => (await API.get("/gold-fx/")).data,
  });

  const targets = useQuery({
    queryKey: ["allocation-targets"],
    queryFn: async () => (await API.get("/settings/allocation-targets/")).data,
  });

  const saveTargets = useMutation({
    mutationFn: (payload: Array<{ type: string; target_percent: number }>) =>
      API.post("/settings/allocation-targets/", payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["allocation-targets"] });
      showToast("Đã lưu mục tiêu phân bổ", "success");
    },
    onError: (error: any) => {
      showToast(error?.response?.data?.detail || "Không thể lưu mục tiêu phân bổ", "error");
    },
  });

  const defaultSources = useQuery({
    queryKey: ["default-sources"],
    queryFn: async () => (await API.get("/settings/default-sources")).data,
  });

  const saveDefaultSources = useMutation({
    mutationFn: (payload: Record<string, string>) => API.post("/settings/default-sources", payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["default-sources"] });
      showToast("Đã lưu nguồn dữ liệu mặc định", "success");
    },
    onError: (error: any) => {
      showToast(error?.response?.data?.detail || "Không thể lưu nguồn dữ liệu mặc định", "error");
    },
  });

  const importAssets = useMutation({
    mutationFn: async (file: File) => {
      const form = new FormData();
      form.append("file", file);
      return (await API.post("/import-export/import/assets", form)).data;
    },
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["assets"] });
      showToast(`Nhập tài sản: ${data.created} đã tạo, ${data.skipped} bỏ qua${data.errors.length ? `, ${data.errors.length} lỗi` : ""}`, data.errors.length ? "error" : "success");
    },
    onError: (error: any) => {
      showToast(error?.response?.data?.detail || "Không thể nhập tài sản", "error");
    },
  });

  const importTransactions = useMutation({
    mutationFn: async (file: File) => {
      const form = new FormData();
      form.append("file", file);
      return (await API.post("/import-export/import/transactions", form)).data;
    },
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["transactions"] });
      qc.invalidateQueries({ queryKey: ["portfolio"] });
      showToast(`Nhập giao dịch: ${data.created} đã tạo, ${data.skipped} bỏ qua${data.errors.length ? `, ${data.errors.length} lỗi` : ""}`, data.errors.length ? "error" : "success");
    },
    onError: (error: any) => {
      showToast(error?.response?.data?.detail || "Không thể nhập giao dịch", "error");
    },
  });

  const [targetValues, setTargetValues] = useState<Record<string, string>>({});
  const [defaultSourceValues, setDefaultSourceValues] = useState<Record<string, string | null>>({});

  const getDefaultSource = (type: string) => {
    if (defaultSourceValues[type] !== undefined) return defaultSourceValues[type];
    return defaultSources.data?.[type] || "";
  };

  const handleSaveDefaultSources = () => {
    const payload: Record<string, string> = {};
    ASSET_TYPES.forEach((type) => {
      const value = getDefaultSource(type);
      if (value) payload[type] = value;
    });
    saveDefaultSources.mutate(payload);
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
      {goldFx.isError && <ErrorMessage error={goldFx.error} retry={() => goldFx.refetch()} />}
      {targets.isError && <ErrorMessage error={targets.error} retry={() => targets.refetch()} />}
      {saveTargets.isError && <ErrorMessage error={saveTargets.error} retry={() => saveTargets.reset()} />}
      {defaultSources.isError && <ErrorMessage error={defaultSources.error} retry={() => defaultSources.refetch()} />}
      {saveDefaultSources.isError && <ErrorMessage error={saveDefaultSources.error} retry={() => saveDefaultSources.reset()} />}
      {importAssets.isError && <ErrorMessage error={importAssets.error} retry={() => importAssets.reset()} />}
      {importTransactions.isError && <ErrorMessage error={importTransactions.error} retry={() => importTransactions.reset()} />}
      <SectionHeader title={labels.settings.title} />

      <FintechCard delay={0.1}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="card-title inline-flex items-center">
            {labels.settings.goldFx}
            <InfoTooltip content={labels.tooltips.settingsGoldFx} />
          </h3>
          <button
            onClick={() => qc.invalidateQueries({ queryKey: ["gold-fx"] })}
            className="btn-secondary"
          >
            <RefreshCw className={`w-4 h-4 ${goldFx.isFetching ? "animate-spin" : ""}`} />
            {labels.settings.refresh}
          </button>
        </div>

        {goldFx.isLoading && <Skeleton className="h-48" />}

        {goldFx.data && (
          <div className="space-y-6">
            <div>
              <h4 className="font-display font-semibold text-slate-900 mb-3">{labels.settings.gold}</h4>
              {goldFx.data.gold.length > 0 ? (
                <div className="overflow-x-auto scrollbar-thin">
                  <table className="table-fintech">
                    <thead>
                      <tr>
                        <th className="text-left">
                          {labels.settings.source}
                          <InfoTooltip content={labels.tooltips.sourceDefault} />
                        </th>
                        <th className="text-right">
                          {labels.settings.buy}
                          <InfoTooltip content={labels.tooltips.settingsGoldFx} />
                        </th>
                        <th className="text-right">
                          {labels.settings.sell}
                          <InfoTooltip content={labels.tooltips.settingsGoldFx} />
                        </th>
                        <th className="text-right">
                          {labels.settings.updated}
                          <InfoTooltip content={labels.tooltips.backtestStartDate} />
                        </th>
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
                        <th className="text-left">
                          {labels.settings.currency}
                          <InfoTooltip content={labels.tooltips.assetCurrency} />
                        </th>
                        <th className="text-right">
                          {labels.settings.buy}
                          <InfoTooltip content={labels.tooltips.settingsGoldFx} />
                        </th>
                        <th className="text-right">
                          {labels.settings.transfer}
                          <InfoTooltip content={labels.tooltips.settingsGoldFx} />
                        </th>
                        <th className="text-right">
                          {labels.settings.sell}
                          <InfoTooltip content={labels.tooltips.settingsGoldFx} />
                        </th>
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

      <FintechCard delay={0.18}>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <h3 className="card-title">{labels.sources.defaultSources}</h3>
            <InfoTooltip content={labels.sources.defaultSourcesDescription} />
          </div>
          <button
            onClick={handleSaveDefaultSources}
            disabled={saveDefaultSources.isPending}
            className="btn-primary"
          >
            <Save className="w-4 h-4" />
            {saveDefaultSources.isPending ? labels.settings.saving : labels.settings.save}
          </button>
        </div>
        <div className="space-y-3">
          {ASSET_TYPES.map((type) => (
            <div key={type} className="grid grid-cols-1 md:grid-cols-4 gap-3 items-center">
              <label className="text-sm font-medium text-slate-500 md:col-span-1">
                {labels.assetTypes[type as keyof typeof labels.assetTypes] ?? type}
              </label>
              <div className="md:col-span-3">
                <SourceSelect
                  assetType={type}
                  value={getDefaultSource(type)}
                  onChange={(value) => setDefaultSourceValues({ ...defaultSourceValues, [type]: value })}
                />
              </div>
            </div>
          ))}
        </div>
      </FintechCard>

      <FintechCard delay={0.2}>
        <div className="flex items-center gap-2 mb-4">
          <h3 className="card-title">{labels.settings.allocationTargets}</h3>
          <InfoTooltip content={labels.tooltips.allocationTargets} />
        </div>
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
        <div className="mt-4 space-y-3">
          <div className="flex items-center justify-between">
            <div className={`text-sm ${totalTarget > 100 ? "text-accent-rose" : totalTarget < 100 ? "text-amber-600" : "text-emerald-600"}`}>
              {labels.rebalance.targetAllocation}: {totalTarget.toFixed(2)}%
              {totalTarget > 100 && ` — ${labels.rebalance.totalTargetMustBe100}`}
              {totalTarget < 100 && totalTarget > 0 && ` — Còn ${(100 - totalTarget).toFixed(2)}% chưa phân bổ`}
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
          <div className="h-2 w-full rounded-full bg-slate-100 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${totalTarget > 100 ? "bg-accent-rose" : totalTarget < 100 ? "bg-amber-400" : "bg-emerald-500"}`}
              style={{ width: `${Math.min(totalTarget, 100)}%` }}
            />
          </div>
        </div>
      </FintechCard>

      <FintechCard delay={0.25}>
        <h3 className="card-title mb-4 inline-flex items-center">
          {labels.settings.importExport}
          <InfoTooltip content={labels.tooltips.settingsImportExport} />
        </h3>
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
            <div className="flex flex-wrap gap-2">
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
              <button
                onClick={() => setSmartImportType("assets")}
                className="btn-secondary"
              >
                <Upload className="w-4 h-4" />
                {labels.importExport.smartImportAssets}
              </button>
              <button
                onClick={() => setSmartImportType("transactions")}
                className="btn-secondary"
              >
                <Upload className="w-4 h-4" />
                {labels.importExport.smartImportTransactions}
              </button>
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

      {smartImportType && (
        <SmartImportDialog
          importType={smartImportType}
          onClose={() => setSmartImportType(null)}
          onSuccess={() => {
            qc.invalidateQueries({ queryKey: ["assets"] });
            qc.invalidateQueries({ queryKey: ["transactions"] });
          }}
        />
      )}
    </div>
  );
}
