import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Pencil, Search, Trash2, ArrowRightLeft } from "lucide-react";
import { useNavigate } from "react-router-dom";
import API from "../api/client";
import { ErrorMessage } from "../components/ErrorMessage";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { FintechCard } from "../components/ui/FintechCard";
import { SectionHeader } from "../components/ui/SectionHeader";
import { Skeleton } from "../components/ui/Skeleton";
import { SourceSelect } from "../components/SourceSelect";
import { InfoTooltip } from "../components/InfoTooltip";
import { useToast } from "../contexts/ToastContext";
import { usePersistentState } from "../hooks/usePersistentState";
import { labels } from "../i18n/vi";
import { hasErrors, positiveNumber, required, validateForm } from "../lib/validation";

type AssetTypeConfig = {
  label: string;
  fields: string[];
  marketPrice: boolean;
};

type AssetTypeMap = Record<string, AssetTypeConfig>;

const typeColor: Record<string, string> = {
  STOCK: "bg-accent-blue/10 text-accent-blue ring-accent-blue/20",
  FUND: "bg-accent-violet/10 text-accent-violet ring-accent-violet/20",
  ETF: "bg-accent-cyan/10 text-accent-cyan ring-accent-cyan/20",
  GOLD: "bg-accent-amber/10 text-accent-amber ring-accent-amber/20",
  CRYPTO: "bg-accent-emerald/10 text-accent-emerald ring-accent-emerald/20",
  REAL_ESTATE: "bg-accent-rose/10 text-accent-rose ring-accent-rose/20",
  LIFE_INSURANCE: "bg-accent-indigo/10 text-accent-indigo ring-accent-indigo/20",
};

function typeBadgeClass(type: string): string {
  if (typeColor[type]) return typeColor[type];
  const palette = [
    "bg-accent-blue/10 text-accent-blue ring-accent-blue/20",
    "bg-accent-violet/10 text-accent-violet ring-accent-violet/20",
    "bg-accent-cyan/10 text-accent-cyan ring-accent-cyan/20",
    "bg-accent-amber/10 text-accent-amber ring-accent-amber/20",
    "bg-accent-emerald/10 text-accent-emerald ring-accent-emerald/20",
    "bg-accent-rose/10 text-accent-rose ring-accent-rose/20",
    "bg-accent-indigo/10 text-accent-indigo ring-accent-indigo/20",
  ];
  let hash = 0;
  for (let i = 0; i < type.length; i++) hash = type.charCodeAt(i) + ((hash << 5) - hash);
  return palette[Math.abs(hash) % palette.length];
}

export function Assets() {
  const qc = useQueryClient();
  const { showToast } = useToast();
  const navigate = useNavigate();
  const [form, setForm] = usePersistentState("assets.form", {
    symbol: "",
    name: "",
    type: "",
    exchange: "",
    currency: "VND",
    source: null as string | null,
    manual_value: "",
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [deleteTarget, setDeleteTarget] = useState<{ id: number; name: string } | null>(null);
  const [editTarget, setEditTarget] = useState<any | null>(null);
  const [editForm, setEditForm] = useState({
    name: "",
    exchange: "",
    currency: "VND",
    source: null as string | null,
    manual_value: "",
  });
  const [editErrors, setEditErrors] = useState<Record<string, string>>({});
  const [search, setSearch] = usePersistentState("assets.search", "");

  const assetTypes = useQuery<AssetTypeMap>({
    queryKey: ["asset-types"],
    queryFn: async () => (await API.get("/settings/asset-types")).data.types,
  });

  const typeConfig = useMemo(() => assetTypes.data || {}, [assetTypes.data]);
  const allTypeCodes = useMemo(() => Object.keys(typeConfig), [typeConfig]);
  const defaultType = useMemo(() => allTypeCodes[0] || "", [allTypeCodes]);
  const fields = typeConfig[form.type]?.fields || ["symbol", "name"];
  const isMarketPrice = typeConfig[form.type]?.marketPrice !== false;
  const needsManualValue = !isMarketPrice;

  useEffect(() => {
    if (defaultType && !form.type) {
      setForm((prev) => ({ ...prev, type: defaultType }));
    }
  }, [defaultType, form.type]);

  useEffect(() => {
    if (isMarketPrice && form.manual_value) {
      setForm((prev) => ({ ...prev, manual_value: "" }));
    }
  }, [form.type, isMarketPrice]);

  const assets = useQuery({
    queryKey: ["assets"],
    queryFn: async () => (await API.get("/assets/")).data,
  });

  const typeLabel = (code: string) =>
    typeConfig[code]?.label || labels.assetTypes[code as keyof typeof labels.assetTypes] || code;

  const resetForm = () => {
    setForm({ symbol: "", name: "", type: defaultType, exchange: "", currency: "VND", source: null, manual_value: "" });
  };

  const create = useMutation({
    mutationFn: () => {
      const payload: any = { ...form };
      if (!payload.symbol) delete payload.symbol;
      if (!isMarketPrice && payload.manual_value) {
        payload.manual_value = parseFloat(payload.manual_value);
      } else {
        delete payload.manual_value;
      }
      return API.post("/assets/", payload);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["assets"] });
      resetForm();
      setErrors({});
      showToast("Đã thêm tài sản thành công", "success");
    },
    onError: (error: any) => {
      showToast(error?.response?.data?.detail || "Không thể thêm tài sản", "error");
    },
  });

  const remove = useMutation({
    mutationFn: (id: number) => API.delete(`/assets/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["assets"] });
      showToast("Đã xóa tài sản", "success");
      setDeleteTarget(null);
    },
    onError: (error: any) => {
      showToast(error?.response?.data?.detail || "Không thể xóa tài sản", "error");
      setDeleteTarget(null);
    },
  });

  const update = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: any }) => API.put(`/assets/${id}`, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["assets"] });
      qc.invalidateQueries({ queryKey: ["portfolio"] });
      setEditTarget(null);
      setEditErrors({});
      showToast("Đã cập nhật tài sản", "success");
    },
    onError: (error: any) => {
      showToast(error?.response?.data?.detail || "Không thể cập nhật tài sản", "error");
    },
  });

  const openEditAsset = (asset: any) => {
    setEditTarget(asset);
    setEditForm({
      name: asset.name || "",
      exchange: asset.exchange || "",
      currency: asset.currency || "VND",
      source: asset.source || null,
      manual_value: asset.manual_value ? String(asset.manual_value) : "",
    });
    setEditErrors({});
  };

  const handleEditChange = (field: keyof typeof editForm, value: string | null) => {
    setEditForm((prev) => ({ ...prev, [field]: value }));
    if (editErrors[field]) {
      setEditErrors((prev) => ({ ...prev, [field]: "" }));
    }
  };

  const handleEditSubmit = () => {
    const assetType = typeConfig[editTarget.type];
    const needsManualValue = assetType?.marketPrice === false;
    const validators: Record<string, { value: string; validators: any[] }> = {
      name: { value: editForm.name, validators: [required("Vui lòng nhập tên tài sản")] },
    };
    if (needsManualValue) {
      validators.manual_value = { value: editForm.manual_value, validators: [positiveNumber("Vui lòng nhập giá trị dương")] };
    }
    const validationErrors = validateForm(validators);
    setEditErrors(validationErrors);
    if (hasErrors(validationErrors)) return;

    const payload: any = {
      name: editForm.name,
      exchange: editForm.exchange,
      currency: editForm.currency,
      source: editForm.source,
    };
    if (editForm.manual_value) {
      payload.manual_value = parseFloat(editForm.manual_value);
    }
    update.mutate({ id: editTarget.id, payload });
  };

  const handleNewTransaction = (asset: any) => {
    navigate("/transactions", { state: { asset_id: asset.id } });
  };

  const handleSubmit = () => {
    const validators: Record<string, { value: string; validators: any[] }> = {
      name: { value: form.name, validators: [required("Vui lòng nhập tên tài sản")] },
    };
    if (fields.includes("symbol")) {
      validators.symbol = { value: form.symbol, validators: [required("Vui lòng nhập mã tài sản")] };
    }
    if (needsManualValue || fields.includes("value")) {
      validators.manual_value = { value: form.manual_value, validators: [positiveNumber("Vui lòng nhập giá trị dương")] };
    }
    const validationErrors = validateForm(validators);
    setErrors(validationErrors);
    if (hasErrors(validationErrors)) return;
    create.mutate();
  };

  const handleChange = (field: keyof typeof form, value: string | null) => {
    setForm((prev) => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors((prev) => ({ ...prev, [field]: "" }));
    }
  };

  const renderField = (field: string) => {
    switch (field) {
      case "symbol":
        return (
          <div key="symbol" className="relative">
            <input
              placeholder={labels.assets.symbol}
              className={`input-fintech pr-10 ${errors.symbol ? "border-rose-400 focus:border-rose-400 focus:ring-rose-200" : ""}`}
              value={form.symbol}
              onChange={(e) => handleChange("symbol", e.target.value.toUpperCase())}
              aria-invalid={!!errors.symbol}
            />
            <span className="absolute right-3 top-1/2 -translate-y-1/2">
              <InfoTooltip content={labels.tooltips.assetSymbol} position="right" />
            </span>
            {errors.symbol && <p className="text-xs text-rose-500 mt-1">{errors.symbol}</p>}
          </div>
        );
      case "name":
        return (
          <div key="name" className="relative">
            <input
              placeholder={labels.assets.name}
              className={`input-fintech pr-10 ${errors.name ? "border-rose-400 focus:border-rose-400 focus:ring-rose-200" : ""}`}
              value={form.name}
              onChange={(e) => handleChange("name", e.target.value)}
              aria-invalid={!!errors.name}
            />
            <span className="absolute right-3 top-1/2 -translate-y-1/2">
              <InfoTooltip content={labels.tooltips.assetName} position="right" />
            </span>
            {errors.name && <p className="text-xs text-rose-500 mt-1">{errors.name}</p>}
          </div>
        );
      case "exchange":
        return (
          <div key="exchange" className="relative">
            <input
              placeholder={labels.assets.exchange}
              className="input-fintech pr-10"
              value={form.exchange}
              onChange={(e) => handleChange("exchange", e.target.value)}
            />
            <span className="absolute right-3 top-1/2 -translate-y-1/2">
              <InfoTooltip content={labels.tooltips.assetExchange} position="right" />
            </span>
          </div>
        );
      case "currency":
        return (
          <div key="currency" className="relative">
            <input
              placeholder={labels.assets.currency}
              className="input-fintech pr-10"
              value={form.currency}
              onChange={(e) => handleChange("currency", e.target.value.toUpperCase())}
            />
            <span className="absolute right-3 top-1/2 -translate-y-1/2">
              <InfoTooltip content={labels.tooltips.assetCurrency} position="right" />
            </span>
          </div>
        );
      case "source":
        return (
          <div key="source" className="relative">
            <SourceSelect
              assetType={form.type}
              value={form.source}
              onChange={(value) => handleChange("source", value)}
            />
            <span className="absolute right-8 top-1/2 -translate-y-1/2">
              <InfoTooltip content={labels.sources.assetSourceHint} position="right" />
            </span>
          </div>
        );
      case "value":
        return (
          <div key="value" className="relative">
            <input
              type="number"
              placeholder={labels.assets.value}
              className={`input-fintech pr-10 ${errors.manual_value ? "border-rose-400 focus:border-rose-400 focus:ring-rose-200" : ""}`}
              value={form.manual_value}
              onChange={(e) => handleChange("manual_value", e.target.value)}
              aria-invalid={!!errors.manual_value}
            />
            {errors.manual_value && <p className="text-xs text-rose-500 mt-1">{errors.manual_value}</p>}
          </div>
        );
      default:
        return null;
    }
  };

  const filteredAssets = (assets.data || []).filter((asset: any) => {
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return (
      asset.symbol?.toLowerCase().includes(q) ||
      asset.name?.toLowerCase().includes(q) ||
      asset.type?.toLowerCase().includes(q) ||
      asset.exchange?.toLowerCase().includes(q) ||
      asset.source?.toLowerCase().includes(q)
    );
  });

  return (
    <div className="space-y-6">
      {assetTypes.isError && <ErrorMessage error={assetTypes.error} retry={() => assetTypes.refetch()} />}
      {assets.isError && <ErrorMessage error={assets.error} retry={() => assets.refetch()} />}
      {create.isError && <ErrorMessage error={create.error} retry={() => create.mutate()} />}
      {update.isError && <ErrorMessage error={update.error} retry={() => update.reset()} />}
      {remove.isError && <ErrorMessage error={remove.error} retry={() => remove.reset()} />}
      <SectionHeader title={labels.assets.title} />

      <FintechCard delay={0.1}>
        <h3 className="card-title mb-4">{labels.assets.addAsset}</h3>
        <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
          <div className="relative">
            <select
              className="input-fintech pr-10"
              value={form.type}
              onChange={(e) => handleChange("type", e.target.value)}
            >
              <option value="" disabled>{labels.assets.type}</option>
              {allTypeCodes.map((t) => (
                <option key={t} value={t}>
                  {typeLabel(t)}
                </option>
              ))}
            </select>
            <span className="absolute right-8 top-1/2 -translate-y-1/2">
              <InfoTooltip content={labels.tooltips.assetType} position="right" />
            </span>
          </div>
          {fields.map(renderField)}
          {needsManualValue && !fields.includes("value") && renderField("value")}
        </div>
        <button
          onClick={handleSubmit}
          disabled={create.isPending || !form.type}
          className="btn-primary mt-3"
        >
          <Plus className="w-4 h-4" />
          {labels.assets.add}
        </button>
      </FintechCard>

      <FintechCard delay={0.15}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="card-title">{labels.assets.list}</h3>
          <div className="relative w-full max-w-xs">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Tìm kiếm tài sản..."
              className="input-fintech pl-9 w-full"
            />
          </div>
        </div>
        {assets.isLoading ? (
          <div className="space-y-3">
            <Skeleton className="h-8" count={6} />
          </div>
        ) : (
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
                {filteredAssets.map((asset: any) => (
                  <tr key={asset.id}>
                    <td className="font-display font-semibold text-slate-900">{asset.symbol}</td>
                    <td className="text-slate-700">{asset.name}</td>
                    <td>
                      <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${typeBadgeClass(asset.type)}`}>
                        {typeLabel(asset.type)}
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
                      <div className="inline-flex items-center gap-1">
                        <button
                          onClick={() => handleNewTransaction(asset)}
                          className="inline-flex items-center justify-center p-2 rounded-lg text-accent-emerald hover:bg-accent-emerald/10 transition-colors"
                          title={labels.assets.newTransaction}
                          aria-label={`${labels.assets.newTransaction} ${asset.name}`}
                        >
                          <ArrowRightLeft className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => openEditAsset(asset)}
                          disabled={update.isPending}
                          className="inline-flex items-center justify-center p-2 rounded-lg text-accent-blue hover:bg-accent-blue/10 transition-colors disabled:opacity-50"
                          aria-label={`Sửa ${asset.name}`}
                        >
                          <Pencil className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => setDeleteTarget({ id: asset.id, name: asset.name })}
                          disabled={remove.isPending}
                          className="inline-flex items-center justify-center p-2 rounded-lg text-accent-rose hover:bg-accent-rose/10 transition-colors disabled:opacity-50"
                          aria-label={`Xóa ${asset.name}`}
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {filteredAssets.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-slate-500">
                      {labels.assets.noAssets}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </FintechCard>

      {editTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4">
          <div className="w-full max-w-lg rounded-xl bg-white shadow-xl p-6 space-y-4">
            <h3 className="card-title">{labels.assets.edit}</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">{labels.assets.symbol}</label>
                <input type="text" disabled value={editTarget.symbol} className="input-fintech bg-slate-50" />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">{labels.assets.type}</label>
                <input type="text" disabled value={typeLabel(editTarget.type)} className="input-fintech bg-slate-50" />
              </div>
              <div className="md:col-span-2">
                <input
                  type="text"
                  placeholder={labels.assets.name}
                  className={`input-fintech ${editErrors.name ? "border-rose-400 focus:border-rose-400 focus:ring-rose-200" : ""}`}
                  value={editForm.name}
                  onChange={(e) => handleEditChange("name", e.target.value)}
                />
                {editErrors.name && <p className="text-xs text-rose-500 mt-1">{editErrors.name}</p>}
              </div>
              <div>
                <input
                  type="text"
                  placeholder={labels.assets.exchange}
                  className="input-fintech"
                  value={editForm.exchange}
                  onChange={(e) => handleEditChange("exchange", e.target.value)}
                />
              </div>
              <div>
                <input
                  type="text"
                  placeholder={labels.assets.currency}
                  className="input-fintech"
                  value={editForm.currency}
                  onChange={(e) => handleEditChange("currency", e.target.value)}
                />
              </div>
              <div>
                <SourceSelect
                  assetType={editTarget.type}
                  value={editForm.source}
                  onChange={(value) => handleEditChange("source", value)}
                />
              </div>
              {typeConfig[editTarget.type]?.marketPrice === false && (
                <div>
                  <input
                    type="number"
                    placeholder={labels.assets.manualValue}
                    className={`input-fintech ${editErrors.manual_value ? "border-rose-400 focus:border-rose-400 focus:ring-rose-200" : ""}`}
                    value={editForm.manual_value}
                    onChange={(e) => handleEditChange("manual_value", e.target.value)}
                  />
                  {editErrors.manual_value && <p className="text-xs text-rose-500 mt-1">{editErrors.manual_value}</p>}
                </div>
              )}
            </div>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setEditTarget(null)}
                className="btn-secondary"
                disabled={update.isPending}
              >
                {labels.common.cancel}
              </button>
              <button
                onClick={handleEditSubmit}
                disabled={update.isPending}
                className="btn-primary"
              >
                {update.isPending ? labels.common.saving : labels.common.save}
              </button>
            </div>
          </div>
        </div>
      )}

      <ConfirmDialog
        open={!!deleteTarget}
        title="Xác nhận xóa tài sản"
        message={`Bạn có chắc muốn xóa "${deleteTarget?.name ?? ""}"? Thao tác này không thể hoàn tác.`}
        confirmLabel={labels.common.delete}
        cancelLabel={labels.common.cancel}
        variant="danger"
        isLoading={remove.isPending}
        onConfirm={() => deleteTarget && remove.mutate(deleteTarget.id)}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}
