import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRightLeft, Loader2, Plus, Wallet, Zap } from "lucide-react";
import API, { extractDetailMessage } from "../api/client";
import { FintechCard } from "./ui/FintechCard";
import { FormattedNumberInput } from "./FormattedNumberInput";
import { useToast } from "../contexts/ToastContext";
import { labels } from "../i18n/vi";
import { hasErrors, positiveNumber, required, validateForm } from "../lib/validation";

type AssetTypeConfig = {
  label: string;
  fields: string[];
  marketPrice: boolean;
};

type AssetTypeMap = Record<string, AssetTypeConfig>;

const today = new Date().toISOString().split("T")[0];

export function QuickAddCard() {
  const qc = useQueryClient();
  const { showToast } = useToast();
  const [mode, setMode] = useState<"asset" | "transaction">("asset");

  const [assetForm, setAssetForm] = useState({
    type: "",
    name: "",
    symbol: "",
    manual_value: "",
  });
  const [assetErrors, setAssetErrors] = useState<Record<string, string>>({});

  const [txForm, setTxForm] = useState({
    asset_id: "",
    type: "BUY",
    quantity: "",
    price: "",
  });
  const [txErrors, setTxErrors] = useState<Record<string, string>>({});

  const assetTypes = useQuery<AssetTypeMap>({
    queryKey: ["asset-types"],
    queryFn: async () => (await API.get("/settings/asset-types")).data.types,
  });

  const assets = useQuery({
    queryKey: ["assets"],
    queryFn: async () => (await API.get("/assets/")).data,
  });

  const typeConfig = assetTypes.data || {};
  const allTypeCodes = useMemo(() => Object.keys(typeConfig), [typeConfig]);
  const defaultType = useMemo(() => allTypeCodes[0] || "", [allTypeCodes]);
  const isAssetMarketPrice = typeConfig[assetForm.type]?.marketPrice !== false;

  const selectedAsset = useMemo(() => {
    return (assets.data || []).find((a: any) => String(a.id) === txForm.asset_id);
  }, [assets.data, txForm.asset_id]);

  const isNonMarketAsset = (type: string) => type && typeConfig[type]?.marketPrice === false;

  const availableTxTypes = useMemo(() => {
    const base = [
      { value: "BUY", label: labels.transactions.buy },
      { value: "SELL", label: labels.transactions.sell },
    ];
    if (selectedAsset && isNonMarketAsset(selectedAsset.type)) {
      base.push(
        { value: "DEPOSIT", label: labels.transactions.deposit },
        { value: "WITHDRAWAL", label: labels.transactions.withdrawal }
      );
    }
    return base;
  }, [selectedAsset, typeConfig]);

  useEffect(() => {
    if (defaultType && !assetForm.type) {
      setAssetForm((prev) => ({ ...prev, type: defaultType }));
    }
  }, [defaultType, assetForm.type]);

  useEffect(() => {
    setAssetForm((prev) => ({ ...prev, symbol: "", manual_value: "" }));
  }, [assetForm.type]);

  useEffect(() => {
    if (!selectedAsset) return;
    const type = selectedAsset.type;
    setTxForm((prev) => ({
      ...prev,
      type: ["DEPOSIT", "WITHDRAWAL"].includes(prev.type) && !isNonMarketAsset(type) ? "BUY" : prev.type,
    }));
  }, [selectedAsset, typeConfig]);

  useEffect(() => {
    if (!selectedAsset && !["BUY", "SELL"].includes(txForm.type)) {
      setTxForm((prev) => ({ ...prev, type: "BUY" }));
    }
  }, [selectedAsset, txForm.type]);

  const resetAssetForm = () => {
    setAssetForm({ type: defaultType, name: "", symbol: "", manual_value: "" });
  };

  const resetTxForm = () => {
    setTxForm({ asset_id: "", type: "BUY", quantity: "", price: "" });
  };

  const createAsset = useMutation({
    mutationFn: () => {
      const payload: any = {
        type: assetForm.type,
        name: assetForm.name,
        currency: "VND",
      };
      if (assetForm.symbol) payload.symbol = assetForm.symbol;
      if (!isAssetMarketPrice && assetForm.manual_value) {
        payload.manual_value = parseFloat(assetForm.manual_value);
      }
      return API.post("/assets/", payload);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["assets"] });
      qc.invalidateQueries({ queryKey: ["portfolio"] });
      resetAssetForm();
      setAssetErrors({});
      showToast("Đã thêm tài sản thành công", "success");
    },
    onError: (error: any) => {
      showToast(extractDetailMessage(error?.response?.data?.detail) || "Không thể thêm tài sản", "error");
    },
  });

  const createTransaction = useMutation({
    mutationFn: () => {
      const isNonMarket = selectedAsset && isNonMarketAsset(selectedAsset.type);
      return API.post("/transactions/", {
        asset_id: Number(txForm.asset_id),
        type: txForm.type,
        quantity: Number(txForm.quantity),
        price: isNonMarket ? Number(txForm.price) : txForm.price ? Number(txForm.price) : null,
        fee: 0,
        date: today,
        notes: "",
      });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["transactions"] });
      qc.invalidateQueries({ queryKey: ["portfolio"] });
      qc.invalidateQueries({ queryKey: ["analytics"] });
      qc.invalidateQueries({ queryKey: ["analytics-risk"] });
      qc.invalidateQueries({ queryKey: ["portfolio-history"] });
      resetTxForm();
      setTxErrors({});
      showToast("Đã thêm giao dịch thành công", "success");
    },
    onError: (error: any) => {
      showToast(extractDetailMessage(error?.response?.data?.detail) || "Không thể thêm giao dịch", "error");
    },
  });

  const handleAssetChange = (field: keyof typeof assetForm, value: string) => {
    setAssetForm((prev) => ({ ...prev, [field]: value }));
    if (assetErrors[field]) {
      setAssetErrors((prev) => ({ ...prev, [field]: "" }));
    }
  };

  const handleTxChange = (field: keyof typeof txForm, value: string) => {
    setTxForm((prev) => ({ ...prev, [field]: value }));
    if (txErrors[field]) {
      setTxErrors((prev) => ({ ...prev, [field]: "" }));
    }
  };

  const handleAssetSubmit = () => {
    const validators: Record<string, { value: string; validators: any[] }> = {
      name: { value: assetForm.name, validators: [required("Vui lòng nhập tên tài sản")] },
    };
    if (!isAssetMarketPrice) {
      validators.manual_value = { value: assetForm.manual_value, validators: [positiveNumber("Vui lòng nhập giá trị dương")] };
    }
    const validationErrors = validateForm(validators);
    setAssetErrors(validationErrors);
    if (hasErrors(validationErrors)) return;
    createAsset.mutate();
  };

  const handleTxSubmit = () => {
    const validators: Record<string, { value: string; validators: any[] }> = {
      asset_id: { value: txForm.asset_id, validators: [required("Vui lòng chọn tài sản")] },
      quantity: { value: txForm.quantity, validators: [positiveNumber("Số lượng phải lớn hơn 0")] },
    };
    const isNonMarket = selectedAsset && isNonMarketAsset(selectedAsset.type);
    if (isNonMarket || txForm.price) {
      validators.price = { value: txForm.price, validators: [positiveNumber("Giá phải lớn hơn 0")] };
    }
    const validationErrors = validateForm(validators);
    setTxErrors(validationErrors);
    if (hasErrors(validationErrors)) return;
    createTransaction.mutate();
  };

  const txTitle = labels.dashboard.quickAdd || "Thêm nhanh";
  const assetTabLabel = labels.dashboard.quickAddAssetTab || "Tài sản";
  const txTabLabel = labels.dashboard.quickAddTransactionTab || "Giao dịch";

  return (
    <FintechCard delay={0.38}>
      <div className="flex items-center gap-2 mb-3">
        <div className="p-1.5 rounded-lg bg-accent-blue/10 text-accent-blue">
          <Zap className="w-4 h-4" />
        </div>
        <h3 className="card-title">{txTitle}</h3>
      </div>
      <p className="text-sm text-slate-500 mb-4">
        {labels.dashboard.quickAddHint || "Thêm tài sản hoặc ghi nhận giao dịch mà không rời khỏi Tổng quan."}
      </p>

      <div className="flex border-b border-slate-100 mb-4">
        <button
          onClick={() => setMode("asset")}
          className={`flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-xl text-sm font-medium transition-colors ${mode === "asset" ? "bg-white text-accent-blue shadow-sm" : "text-slate-500 hover:text-slate-700"
            }`}
        >
          <Wallet className="w-4 h-4" />
          {assetTabLabel}
        </button>
        <button
          onClick={() => setMode("transaction")}
          className={`flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-xl text-sm font-medium transition-colors ${mode === "transaction" ? "bg-white text-accent-blue shadow-sm" : "text-slate-500 hover:text-slate-700"
            }`}
        >
          <ArrowRightLeft className="w-4 h-4" />
          {txTabLabel}
        </button>
      </div>

      {mode === "asset" ? (
        <div className="grid grid-cols-3 gap-3">
          <div className="col-span-3">
            <label className="block text-xs font-medium text-slate-600 mb-1">{labels.assets.type}</label>
            <select
              className="input-fintech"
              value={assetForm.type}
              onChange={(e) => handleAssetChange("type", e.target.value)}
            >
              <option value="" disabled>{labels.assets.type}</option>
              {allTypeCodes.map((t) => (
                <option key={t} value={t}>
                  {typeConfig[t]?.label || labels.assetTypes[t as keyof typeof labels.assetTypes] || t}
                </option>
              ))}
            </select>
          </div>
          <div className="col-span-2">
            <label className="block text-xs font-medium text-slate-600 mb-1">{labels.assets.name}</label>
            <input
              placeholder={labels.assets.name}
              className={`input-fintech ${assetErrors.name ? "border-rose-400 focus:border-rose-400 focus:ring-rose-200" : ""}`}
              value={assetForm.name}
              onChange={(e) => handleAssetChange("name", e.target.value)}
            />
            {assetErrors.name && <p className="text-xs text-rose-500 mt-1">{assetErrors.name}</p>}
          </div>
          <div className="col-span-1">
            <label className="block text-xs font-medium text-slate-600 mb-1">
              {isAssetMarketPrice ? labels.assets.symbol : labels.assets.value}
            </label>
            {isAssetMarketPrice ? (
              <input
                placeholder={labels.assets.symbol}
                className="input-fintech"
                value={assetForm.symbol}
                onChange={(e) => handleAssetChange("symbol", e.target.value.toUpperCase())}
              />
            ) : (
              <FormattedNumberInput
                mode="currency"
                decimals={2}
                placeholder={labels.assets.value}
                className={`input-fintech ${assetErrors.manual_value ? "border-rose-400 focus:border-rose-400 focus:ring-rose-200" : ""}`}
                value={assetForm.manual_value}
                onChange={(value) => handleAssetChange("manual_value", value)}
              />
            )}
            {assetErrors.manual_value && <p className="text-xs text-rose-500 mt-1">{assetErrors.manual_value}</p>}
          </div>
          <div className="col-span-3 flex justify-end gap-2 pt-1">
            <button onClick={resetAssetForm} className="btn-secondary text-xs">
              {labels.common.cancel}
            </button>
            <button
              onClick={handleAssetSubmit}
              disabled={createAsset.isPending || !assetForm.type}
              className="btn-primary text-xs"
            >
              {createAsset.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  {labels.common.processing}
                </>
              ) : (
                <>
                  <Plus className="w-4 h-4" />
                  {labels.assets.add}
                </>
              )}
            </button>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-3 gap-3">
          <div className="col-span-3">
            <label className="block text-xs font-medium text-slate-600 mb-1">{labels.assets.searchAssets}</label>
            <select
              className={`input-fintech ${txErrors.asset_id ? "border-rose-400 focus:border-rose-400 focus:ring-rose-200" : ""}`}
              value={txForm.asset_id}
              onChange={(e) => handleTxChange("asset_id", e.target.value)}
            >
              <option value="">{labels.transactions.selectAsset}</option>
              {(assets.data || [])
                .slice()
                .sort((a: any, b: any) => (a.symbol || "").localeCompare(b.symbol || ""))
                .map((asset: any) => (
                  <option key={asset.id} value={asset.id}>
                    {asset.symbol} — {asset.name}
                  </option>
                ))}
            </select>
            {txErrors.asset_id && <p className="text-xs text-rose-500 mt-1">{txErrors.asset_id}</p>}
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">{labels.transactions.type}</label>
            <select
              className="input-fintech"
              value={txForm.type}
              onChange={(e) => handleTxChange("type", e.target.value)}
              disabled={!selectedAsset}
            >
              {availableTxTypes.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">{labels.transactions.quantity}</label>
            <input
              type="number"
              placeholder={labels.transactions.quantity}
              className={`input-fintech ${txErrors.quantity ? "border-rose-400 focus:border-rose-400 focus:ring-rose-200" : ""}`}
              value={txForm.quantity}
              onChange={(e) => handleTxChange("quantity", e.target.value)}
            />
            {txErrors.quantity && <p className="text-xs text-rose-500 mt-1">{txErrors.quantity}</p>}
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">{labels.transactions.price}</label>
            <FormattedNumberInput
              mode="currency"
              decimals={2}
              placeholder={selectedAsset && isNonMarketAsset(selectedAsset.type) ? labels.transactions.price : "Giá (để trống = TT)"}
              className={`input-fintech ${txErrors.price ? "border-rose-400 focus:border-rose-400 focus:ring-rose-200" : ""}`}
              value={txForm.price}
              onChange={(value) => handleTxChange("price", value)}
            />
            {txErrors.price && <p className="text-xs text-rose-500 mt-1">{txErrors.price}</p>}
          </div>
          <div className="col-span-3 flex justify-end gap-2 pt-1">
            <button onClick={resetTxForm} className="btn-secondary text-xs">
              {labels.common.cancel}
            </button>
            <button
              onClick={handleTxSubmit}
              disabled={createTransaction.isPending}
              className="btn-primary text-xs"
            >
              {createTransaction.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  {labels.common.processing}
                </>
              ) : (
                <>
                  <Plus className="w-4 h-4" />
                  {labels.transactions.add}
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </FintechCard>
  );
}
