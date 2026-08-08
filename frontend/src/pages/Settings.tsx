import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, FileSpreadsheet, Plus, Save, Trash2, Upload } from "lucide-react";
import API from "../api/client";
import { ErrorMessage } from "../components/ErrorMessage";
import { SmartImportDialog } from "../components/SmartImportDialog";
import { FintechCard } from "../components/ui/FintechCard";
import { SectionHeader } from "../components/ui/SectionHeader";
import { SourceSelect } from "../components/SourceSelect";
import { InfoTooltip } from "../components/InfoTooltip";
import { useToast } from "../contexts/ToastContext";
import { labels } from "../i18n/vi";
import { clearAppStorage } from "../lib/storage";

type AssetTypeConfig = {
  label: string;
  fields: string[];
  marketPrice: boolean;
  capitalMode?: string;
  showPnl?: boolean;
};

type AssetTypeMap = Record<string, AssetTypeConfig>;

type AssetTypeItem = {
  code: string;
  label: string;
  fields: string[];
  marketPrice: boolean;
  capitalMode: string;
  showPnl: boolean;
};

const FIELD_OPTIONS = [
  { key: "symbol", label: labels.assets.symbol },
  { key: "name", label: labels.assets.name },
  { key: "exchange", label: labels.assets.exchange },
  { key: "currency", label: labels.assets.currency },
  { key: "source", label: labels.sources.assetSource },
  { key: "value", label: labels.assets.value },
];

export function Settings() {
  const qc = useQueryClient();
  const { showToast } = useToast();
  const [smartImportType, setSmartImportType] = useState<"assets" | "transactions" | null>(null);

  const assetTypes = useQuery<AssetTypeMap>({
    queryKey: ["asset-types"],
    queryFn: async () => (await API.get("/settings/asset-types")).data.types,
  });

  const saveAssetTypes = useMutation({
    mutationFn: (payload: AssetTypeMap) => API.post("/settings/asset-types", { types: payload }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["asset-types"] });
      qc.invalidateQueries({ queryKey: ["default-sources"] });
      qc.invalidateQueries({ queryKey: ["allocation-targets"] });
      showToast("Đã lưu loại tài sản", "success");
    },
    onError: (error: any) => {
      showToast(error?.response?.data?.detail || "Không thể lưu loại tài sản", "error");
    },
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

  const [typeList, setTypeList] = useState<AssetTypeItem[]>([]);

  useEffect(() => {
    if (assetTypes.data && typeList.length === 0) {
      setTypeList(
        Object.entries(assetTypes.data).map(([code, info]) => ({
          code,
          ...info,
          capitalMode: info.capitalMode || "unit_price",
          showPnl: info.showPnl ?? info.marketPrice,
        }))
      );
    }
  }, [assetTypes.data, typeList.length]);

  const [targetValues, setTargetValues] = useState<Record<string, string>>({});
  const [defaultSourceValues, setDefaultSourceValues] = useState<Record<string, string | null>>({});

  const allTypeCodes = useMemo(() => Object.keys(assetTypes.data || {}), [assetTypes.data]);
  const marketTypeCodes = useMemo(
    () => allTypeCodes.filter((code) => assetTypes.data?.[code]?.marketPrice),
    [allTypeCodes, assetTypes.data]
  );

  const typeLabel = (code: string) =>
    assetTypes.data?.[code]?.label || labels.assetTypes[code as keyof typeof labels.assetTypes] || code;

  const getDefaultSource = (type: string) => {
    if (defaultSourceValues[type] !== undefined) return defaultSourceValues[type];
    return defaultSources.data?.[type] || "";
  };

  const handleSaveDefaultSources = () => {
    const payload: Record<string, string> = {};
    marketTypeCodes.forEach((type) => {
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

  const totalTarget = allTypeCodes.reduce((sum, t) => sum + (Number(getTarget(t)) || 0), 0);

  const handleSaveTargets = () => {
    const payload = allTypeCodes.map((type) => ({
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

  const updateTypeItem = (index: number, patch: Partial<AssetTypeItem>) => {
    const next = [...typeList];
    next[index] = { ...next[index], ...patch };
    setTypeList(next);
  };

  const toggleField = (index: number, field: string) => {
    const item = typeList[index];
    const fields = item.fields.includes(field)
      ? item.fields.filter((f) => f !== field)
      : [...item.fields, field];
    updateTypeItem(index, { fields });
  };

  const handleAddType = () => {
    const base = "NEW_TYPE";
    let code = base;
    let i = 1;
    while (typeList.some((t) => t.code === code)) {
      code = `${base}_${i++}`;
    }
    setTypeList([
      ...typeList,
      { code, label: "", fields: ["name", "value"], marketPrice: false, capitalMode: "unit_price", showPnl: false },
    ]);
  };

  const handleRemoveType = (index: number) => {
    const next = [...typeList];
    next.splice(index, 1);
    setTypeList(next);
  };

  const handleSaveAssetTypes = () => {
    const seen = new Set<string>();
    const payload: AssetTypeMap = {};
    for (const item of typeList) {
      const code = item.code.trim().toUpperCase();
      if (!code || seen.has(code)) continue;
      seen.add(code);
      const fields = item.fields.includes("name") ? item.fields : ["name", ...item.fields];
      payload[code] = {
        label: item.label.trim() || code,
        fields,
        marketPrice: item.marketPrice,
        capitalMode: item.marketPrice ? "unit_price" : item.capitalMode,
        showPnl: item.marketPrice ? true : item.showPnl,
      };
    }
    saveAssetTypes.mutate(payload);
  };

  return (
    <div className="space-y-6">
      {assetTypes.isError && <ErrorMessage error={assetTypes.error} retry={() => assetTypes.refetch()} />}
      {saveAssetTypes.isError && <ErrorMessage error={saveAssetTypes.error} retry={() => saveAssetTypes.reset()} />}
      {targets.isError && <ErrorMessage error={targets.error} retry={() => targets.refetch()} />}
      {saveTargets.isError && <ErrorMessage error={saveTargets.error} retry={() => saveTargets.reset()} />}
      {defaultSources.isError && <ErrorMessage error={defaultSources.error} retry={() => defaultSources.refetch()} />}
      {saveDefaultSources.isError && <ErrorMessage error={saveDefaultSources.error} retry={() => saveDefaultSources.reset()} />}
      {importAssets.isError && <ErrorMessage error={importAssets.error} retry={() => importAssets.reset()} />}
      {importTransactions.isError && <ErrorMessage error={importTransactions.error} retry={() => importTransactions.reset()} />}
      <SectionHeader title={labels.settings.title} />

      <FintechCard delay={0.05}>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <h3 className="card-title">{labels.settings.assetTypes}</h3>
            <InfoTooltip content={labels.tooltips.assetType} />
          </div>
          <button
            onClick={handleSaveAssetTypes}
            disabled={saveAssetTypes.isPending || typeList.length === 0}
            className="btn-primary"
          >
            <Save className="w-4 h-4" />
            {saveAssetTypes.isPending ? labels.settings.saving : labels.settings.save}
          </button>
        </div>
        <div className="space-y-4">
          {typeList.map((item, idx) => (
            <div key={idx} className="p-3 rounded-lg border border-slate-200 bg-slate-50/50 space-y-3">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-3 items-center">
                <input
                  type="text"
                  className="input-fintech"
                  value={item.code}
                  onChange={(e) => updateTypeItem(idx, { code: e.target.value.toUpperCase() })}
                  placeholder={labels.settings.assetTypeCode}
                />
                <input
                  type="text"
                  className="md:col-span-2 input-fintech"
                  value={item.label}
                  onChange={(e) => updateTypeItem(idx, { label: e.target.value })}
                  placeholder={labels.settings.assetTypeName}
                />
                <button
                  onClick={() => handleRemoveType(idx)}
                  className="btn-secondary text-rose-600"
                >
                  <Trash2 className="w-4 h-4" />
                  {labels.settings.removeAssetType}
                </button>
              </div>
              <div className="flex flex-wrap gap-2">
                {FIELD_OPTIONS.map((option) => (
                  <label key={option.key} className="inline-flex items-center gap-1.5 text-sm text-slate-600 bg-white px-2 py-1 rounded border border-slate-200 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={item.fields.includes(option.key)}
                      onChange={() => toggleField(idx, option.key)}
                    />
                    {option.label}
                  </label>
                ))}
              </div>
              <label className="inline-flex items-center gap-2 text-sm text-slate-600">
                <input
                  type="checkbox"
                  checked={item.marketPrice}
                  onChange={(e) => updateTypeItem(idx, { marketPrice: e.target.checked })}
                />
                {labels.settings.assetTypeMarketPrice}
              </label>
              {!item.marketPrice && (
                <div className="flex items-center gap-2 text-sm text-slate-600">
                  <span className="text-slate-500">{labels.settings.assetTypeCapitalMode}:</span>
                  <label className="inline-flex items-center gap-1.5 bg-white px-2 py-1 rounded border border-slate-200 cursor-pointer">
                    <input
                      type="radio"
                      name={`capital-mode-${idx}`}
                      checked={item.capitalMode !== "total_value"}
                      onChange={() => updateTypeItem(idx, { capitalMode: "unit_price" })}
                    />
                    {labels.settings.assetTypeCapitalModeUnitPrice}
                  </label>
                  <label className="inline-flex items-center gap-1.5 bg-white px-2 py-1 rounded border border-slate-200 cursor-pointer">
                    <input
                      type="radio"
                      name={`capital-mode-${idx}`}
                      checked={item.capitalMode === "total_value"}
                      onChange={() => updateTypeItem(idx, { capitalMode: "total_value" })}
                    />
                    {labels.settings.assetTypeCapitalModeTotalValue}
                  </label>
                </div>
              )}
              {!item.marketPrice && (
                <label className="inline-flex items-center gap-2 text-sm text-slate-600">
                  <input
                    type="checkbox"
                    checked={item.showPnl}
                    onChange={(e) => updateTypeItem(idx, { showPnl: e.target.checked })}
                  />
                  {labels.settings.assetTypeShowPnl}
                  <span className="text-xs text-slate-400">({labels.settings.assetTypeShowPnlHint})</span>
                </label>
              )}
            </div>
          ))}
          <button onClick={handleAddType} className="btn-secondary">
            <Plus className="w-4 h-4" />
            {labels.settings.addAssetType}
          </button>
        </div>
      </FintechCard>

      <FintechCard delay={0.1}>
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
          {marketTypeCodes.map((type) => (
            <div key={type} className="grid grid-cols-1 md:grid-cols-4 gap-3 items-center">
              <label className="text-sm font-medium text-slate-500 md:col-span-1">
                {typeLabel(type)}
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
          {marketTypeCodes.length === 0 && (
            <p className="text-sm text-slate-500">Chưa có loại tài sản nào cần nguồn dữ liệu thị trường.</p>
          )}
        </div>
      </FintechCard>

      <FintechCard delay={0.2}>
        <div className="flex items-center gap-2 mb-4">
          <h3 className="card-title">{labels.settings.allocationTargets}</h3>
          <InfoTooltip content={labels.tooltips.allocationTargets} />
        </div>
        <div className="space-y-3">
          {allTypeCodes.map((type) => (
            <div key={type} className="grid grid-cols-1 md:grid-cols-4 gap-3 items-center">
              <label className="text-sm font-medium text-slate-500 md:col-span-1">
                {typeLabel(type)}
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
            <p className="text-xs text-slate-500">{labels.importExport.sampleHint}</p>
            <div className="flex flex-wrap gap-2">
              <label className="btn-secondary cursor-pointer">
                <Upload className="w-4 h-4" />
                {labels.settings.importAssets}
                <input
                  type="file"
                  accept=".csv,.xlsx,.zip"
                  className="hidden"
                  onChange={(e) => handleFileChange(e, "assets")}
                />
              </label>
              <label className="btn-secondary cursor-pointer">
                <Upload className="w-4 h-4" />
                {labels.settings.importTransactions}
                <input
                  type="file"
                  accept=".csv,.xlsx,.zip"
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
              <a
                href="/sample_assets.csv"
                download
                className="btn-secondary"
              >
                <FileSpreadsheet className="w-4 h-4" />
                {labels.importExport.sampleAssets}
              </a>
              <a
                href="/sample_transactions.csv"
                download
                className="btn-secondary"
              >
                <FileSpreadsheet className="w-4 h-4" />
                {labels.importExport.sampleTransactions}
              </a>
              <a
                href="/sample_assets.xlsx"
                download
                className="btn-secondary"
              >
                <FileSpreadsheet className="w-4 h-4" />
                {labels.importExport.sampleAssetsExcel}
              </a>
              <a
                href="/sample_transactions.xlsx"
                download
                className="btn-secondary"
              >
                <FileSpreadsheet className="w-4 h-4" />
                {labels.importExport.sampleTransactionsExcel}
              </a>
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

      <FintechCard delay={0.3}>
        <div className="flex items-center justify-between">
          <div>
            <h3 className="card-title">{labels.settings.clearCache}</h3>
            <p className="text-sm text-slate-500 mt-1">{labels.settings.clearCacheDescription}</p>
          </div>
          <button
            onClick={() => {
              if (window.confirm(labels.settings.clearCacheConfirm)) {
                qc.clear();
                clearAppStorage();
                window.location.reload();
              }
            }}
            className="btn-secondary text-rose-600 hover:bg-rose-50"
          >
            <Trash2 className="w-4 h-4" />
            {labels.settings.clearCache}
          </button>
        </div>
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
