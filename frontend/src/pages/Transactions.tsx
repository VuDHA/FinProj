import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CSSProperties, useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { ArrowDownUp, Pencil, Plus, Search, Trash2 } from "lucide-react";
import { Link, useLocation } from "react-router-dom";
import API from "../api/client";
import { ErrorMessage } from "../components/ErrorMessage";
import { EmptyState } from "../components/EmptyState";
import { FormattedNumberInput } from "../components/FormattedNumberInput";
import { InfoTooltip } from "../components/InfoTooltip";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { FintechCard } from "../components/ui/FintechCard";
import { SectionHeader } from "../components/ui/SectionHeader";
import { Skeleton } from "../components/ui/Skeleton";
import { useToast } from "../contexts/ToastContext";
import { usePersistentState } from "../hooks/usePersistentState";
import { labels } from "../i18n/vi";
import { formatCurrency, formatDate } from "../lib/utils";
import { useDateFormat } from "../hooks/useDateFormat";
import { hasErrors, nonNegativeNumber, notFutureDate, positiveNumber, required, validateForm } from "../lib/validation";

export function Transactions() {
  const qc = useQueryClient();
  const { showToast } = useToast();
  const location = useLocation();
  const { format: dateFormat } = useDateFormat();
  const [tab, setTab] = usePersistentState<"transactions" | "income">("transactions.tab", "transactions");
  const [form, setForm] = usePersistentState("transactions.form", {
    asset_id: "",
    type: "BUY",
    quantity: "",
    price: "",
    price_mode: "manual" as "market" | "manual",
    fee: "0",
    date: new Date().toISOString().split("T")[0],
    notes: "",
  });

  const [incomeForm, setIncomeForm] = usePersistentState("transactions.incomeForm", {
    asset_id: "",
    type: "DIVIDEND",
    amount: "",
    date: new Date().toISOString().split("T")[0],
    notes: "",
  });

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [incomeErrors, setIncomeErrors] = useState<Record<string, string>>({});
  const [deleteTarget, setDeleteTarget] = useState<{ id: number; label: string; type: "transaction" | "income" } | null>(null);
  const [editTarget, setEditTarget] = useState<any | null>(null);
  const [editForm, setEditForm] = useState({
    quantity: "",
    price: "",
    price_mode: "manual" as "market" | "manual",
    fee: "",
    date: "",
    notes: "",
  });
  const [editErrors, setEditErrors] = useState<Record<string, string>>({});
  const [assetSearch, setAssetSearch] = useState("");
  const [assetSearchOpen, setAssetSearchOpen] = useState(false);
  const assetRef = useRef<HTMLDivElement>(null);
  const [assetDropdownStyle, setAssetDropdownStyle] = useState<CSSProperties>({});

  useLayoutEffect(() => {
    if (!assetSearchOpen) return;
    const update = () => {
      const rect = assetRef.current?.getBoundingClientRect();
      if (!rect) return;
      setAssetDropdownStyle({
        position: "fixed",
        top: rect.bottom + 4,
        left: rect.left,
        width: rect.width,
        zIndex: 50,
      });
    };
    update();
    const main = document.querySelector("main");
    window.addEventListener("resize", update);
    main?.addEventListener("scroll", update, { passive: true });
    return () => {
      window.removeEventListener("resize", update);
      main?.removeEventListener("scroll", update);
    };
  }, [assetSearchOpen]);
  const [transactionSearch, setTransactionSearch] = usePersistentState("transactions.search", "");
  const [incomeSearch, setIncomeSearch] = usePersistentState("transactions.incomeSearch", "");
  const [transactionSortDesc, setTransactionSortDesc] = usePersistentState("transactions.sortDesc", true);
  const [incomeSortDesc, setIncomeSortDesc] = usePersistentState("transactions.incomeSortDesc", true);

  const transactions = useQuery({
    queryKey: ["transactions"],
    queryFn: async () => (await API.get("/transactions/")).data,
  });

  const income = useQuery({
    queryKey: ["income"],
    queryFn: async () => (await API.get("/income/")).data,
  });

  const assets = useQuery({
    queryKey: ["assets"],
    queryFn: async () => (await API.get("/assets/")).data,
  });

  const assetTypes = useQuery<{ [key: string]: { marketPrice: boolean; capitalMode?: string } }>({
    queryKey: ["asset-types"],
    queryFn: async () => (await API.get("/settings/asset-types")).data.types,
  });

  const selectedAsset = useMemo(() => {
    return (assets.data || []).find((a: any) => String(a.id) === form.asset_id);
  }, [assets.data, form.asset_id]);

  // Clear stale asset_id from persisted form state if the asset no longer
  // exists (e.g. it was deleted in another session/tab).
  useEffect(() => {
    if (form.asset_id && assets.data && !selectedAsset) {
      setForm((prev) => ({ ...prev, asset_id: "" }));
    }
  }, [form.asset_id, assets.data, selectedAsset, setForm]);

  const isNonMarketAsset = useCallback(
    (type: string) => type && assetTypes.data?.[type]?.marketPrice === false,
    [assetTypes.data]
  );

  const isTotalValueAsset = useCallback(
    (type: string) => type && assetTypes.data?.[type]?.capitalMode === "total_value",
    [assetTypes.data]
  );

  const defaultPriceMode = (type: string) => (type === "FUND" ? "market" : "manual");

  const transactionTypeLabel = (type: string) => {
    switch (type) {
      case "BUY": return labels.transactions.buy;
      case "SELL": return labels.transactions.sell;
      case "DEPOSIT": return labels.transactions.deposit;
      case "WITHDRAWAL": return labels.transactions.withdrawal;
      default: return type;
    }
  };

  const transactionTypeBadgeClass = (type: string) => {
    if (type === "BUY" || type === "DEPOSIT") return "badge-gain";
    if (type === "SELL" || type === "WITHDRAWAL") return "badge-loss";
    return "badge-loss";
  };

  const availableTransactionTypes = useMemo(() => {
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
  }, [selectedAsset, isNonMarketAsset]);

  useEffect(() => {
    if (selectedAsset && !isNonMarketAsset(selectedAsset.type) && ["DEPOSIT", "WITHDRAWAL"].includes(form.type)) {
      setForm((prev) => ({ ...prev, type: "BUY" }));
    }
  }, [selectedAsset, form.type, isNonMarketAsset]);

  useEffect(() => {
    if (selectedAsset && isTotalValueAsset(selectedAsset.type) && form.price_mode === "market") {
      setForm((prev) => ({ ...prev, price_mode: "manual" }));
    }
  }, [selectedAsset, form.price_mode, isTotalValueAsset]);

  useEffect(() => {
    const state = location.state as { asset_id?: number } | null;
    if (state?.asset_id && String(state.asset_id) !== form.asset_id) {
      const asset = (assets.data || []).find((a: any) => a.id === state.asset_id);
      setForm((prev) => ({
        ...prev,
        asset_id: String(state.asset_id),
        price_mode: defaultPriceMode(asset?.type || ""),
        price: "",
      }));
      window.history.replaceState({}, document.title);
    }
  }, [location.state, assets.data, form.asset_id]);

  const marketPricePreview = useQuery({
    queryKey: ["price-preview", form.asset_id],
    queryFn: async () => {
      const res = await API.get(`/prices/${form.asset_id}`);
      const snapshots = res.data as Array<{ price: number; date: string }>;
      return snapshots?.[0]?.price || null;
    },
    enabled: !!form.asset_id,
    staleTime: 60 * 1000,
  });

  useEffect(() => {
    if (form.price_mode === "market" && marketPricePreview.data) {
      setForm((prev) => ({ ...prev, price: String(marketPricePreview.data) }));
    }
  }, [form.price_mode, marketPricePreview.data]);

  const editMarketPricePreview = useQuery({
    queryKey: ["price-preview", editTarget?.asset_id],
    queryFn: async () => {
      if (!editTarget) return null;
      const res = await API.get(`/prices/${editTarget.asset_id}`);
      const snapshots = res.data as Array<{ price: number; date: string }>;
      return snapshots?.[0]?.price || null;
    },
    enabled: !!editTarget,
    staleTime: 60 * 1000,
  });

  useEffect(() => {
    if (editTarget && editForm.price_mode === "market" && editMarketPricePreview.data) {
      setEditForm((prev) => ({ ...prev, price: String(editMarketPricePreview.data) }));
    }
  }, [editTarget, editForm.price_mode, editMarketPricePreview.data]);

  const create = useMutation({
    mutationFn: () =>
      API.post("/transactions/", {
        asset_id: Number(form.asset_id),
        type: form.type,
        quantity: Number(form.quantity),
        price: form.price_mode === "manual" ? Number(form.price) || null : null,
        fee: Number(form.fee),
        date: form.date,
        notes: form.notes,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["transactions"] });
      qc.invalidateQueries({ queryKey: ["portfolio"] });
      qc.invalidateQueries({ queryKey: ["analytics"] });
      qc.invalidateQueries({ queryKey: ["analytics-risk"] });
      qc.invalidateQueries({ queryKey: ["portfolio-history"] });
      setForm({
        asset_id: "",
        type: "BUY",
        quantity: "",
        price: "",
        price_mode: "manual",
        fee: "0",
        date: new Date().toISOString().split("T")[0],
        notes: "",
      });
      setErrors({});
      showToast("Đã thêm giao dịch thành công", "success");
    },
    onError: (error: any) => {
      showToast(error?.response?.data?.detail || "Không thể thêm giao dịch", "error");
    },
  });

  const createIncome = useMutation({
    mutationFn: () =>
      API.post("/income/", {
        ...incomeForm,
        asset_id: Number(incomeForm.asset_id),
        amount: Number(incomeForm.amount),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["income"] });
      qc.invalidateQueries({ queryKey: ["analytics"] });
      setIncomeForm({
        asset_id: "",
        type: "DIVIDEND",
        amount: "",
        date: new Date().toISOString().split("T")[0],
        notes: "",
      });
      setIncomeErrors({});
      showToast("Đã thêm thu nhập thành công", "success");
    },
    onError: (error: any) => {
      showToast(error?.response?.data?.detail || "Không thể thêm thu nhập", "error");
    },
  });

  const update = useMutation({
    mutationFn: (id: number) =>
      API.put(`/transactions/${id}`, {
        quantity: Number(editForm.quantity),
        price: Number(editForm.price) || null,
        fee: Number(editForm.fee),
        date: editForm.date,
        notes: editForm.notes,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["transactions"] });
      qc.invalidateQueries({ queryKey: ["portfolio"] });
      qc.invalidateQueries({ queryKey: ["analytics"] });
      qc.invalidateQueries({ queryKey: ["analytics-risk"] });
      qc.invalidateQueries({ queryKey: ["portfolio-history"] });
      setEditTarget(null);
      setEditErrors({});
      showToast("Đã cập nhật giao dịch", "success");
    },
    onError: (error: any) => {
      showToast(error?.response?.data?.detail || "Không thể cập nhật giao dịch", "error");
    },
  });

  const remove = useMutation({
    mutationFn: (id: number) => API.delete(`/transactions/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["transactions"] });
      qc.invalidateQueries({ queryKey: ["portfolio"] });
      qc.invalidateQueries({ queryKey: ["analytics"] });
      qc.invalidateQueries({ queryKey: ["analytics-risk"] });
      qc.invalidateQueries({ queryKey: ["portfolio-history"] });
      showToast("Đã xóa giao dịch", "success");
      setDeleteTarget(null);
    },
    onError: (error: any) => {
      showToast(error?.response?.data?.detail || "Không thể xóa giao dịch", "error");
    },
  });

  const removeIncome = useMutation({
    mutationFn: (id: number) => API.delete(`/income/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["income"] });
      qc.invalidateQueries({ queryKey: ["analytics"] });
      showToast("Đã xóa thu nhập", "success");
      setDeleteTarget(null);
    },
    onError: (error: any) => {
      showToast(error?.response?.data?.detail || "Không thể xóa thu nhập", "error");
    },
  });

  const handleSubmitTransaction = () => {
    const validators: Record<string, { value: string; validators: any[] }> = {
      asset_id: { value: form.asset_id, validators: [required("Vui lòng chọn tài sản")] },
      quantity: { value: form.quantity, validators: [positiveNumber("Số lượng phải lớn hơn 0")] },
      fee: { value: form.fee, validators: [nonNegativeNumber("Phí không được âm")] },
      date: { value: form.date, validators: [notFutureDate("Ngày không được trong tương lai")] },
    };
    if (form.price_mode === "manual") {
      validators.price = { value: form.price, validators: [positiveNumber("Giá phải lớn hơn 0")] };
    }
    const validationErrors = validateForm(validators);
    setErrors(validationErrors);
    if (hasErrors(validationErrors)) return;
    create.mutate();
  };

  const handleSubmitEdit = () => {
    const validators: Record<string, { value: string; validators: any[] }> = {
      quantity: { value: editForm.quantity, validators: [positiveNumber("Số lượng phải lớn hơn 0")] },
      fee: { value: editForm.fee, validators: [nonNegativeNumber("Phí không được âm")] },
      date: { value: editForm.date, validators: [notFutureDate("Ngày không được trong tương lai")] },
    };
    if (editForm.price_mode === "manual") {
      validators.price = { value: editForm.price, validators: [positiveNumber("Giá phải lớn hơn 0")] };
    }
    const validationErrors = validateForm(validators);
    setEditErrors(validationErrors);
    if (hasErrors(validationErrors)) return;
    if (editTarget) update.mutate(editTarget.id);
  };

  const handleSubmitIncome = () => {
    const validationErrors = validateForm({
      asset_id: { value: incomeForm.asset_id, validators: [required("Vui lòng chọn tài sản")] },
      amount: { value: incomeForm.amount, validators: [positiveNumber("Số tiền phải lớn hơn 0")] },
      date: { value: incomeForm.date, validators: [notFutureDate("Ngày không được trong tương lai")] },
    });
    setIncomeErrors(validationErrors);
    if (hasErrors(validationErrors)) return;
    createIncome.mutate();
  };

  const assetById = (id: number) => (assets.data || []).find((a: any) => a.id === id);

  const filteredTransactions = (transactions.data || [])
    .filter((tx: any) => {
      if (!transactionSearch.trim()) return true;
      const q = transactionSearch.toLowerCase();
      const asset = assetById(tx.asset_id);
      return (
        asset?.symbol?.toLowerCase().includes(q) ||
        asset?.name?.toLowerCase().includes(q) ||
        tx.date?.includes(q) ||
        tx.type?.toLowerCase().includes(q)
      );
    })
    .sort((a: any, b: any) => {
      const da = new Date(a.date).getTime();
      const db = new Date(b.date).getTime();
      return transactionSortDesc ? db - da : da - db;
    });

  const filteredIncome = (income.data || [])
    .filter((inc: any) => {
      if (!incomeSearch.trim()) return true;
      const q = incomeSearch.toLowerCase();
      const asset = assetById(inc.asset_id);
      return (
        asset?.symbol?.toLowerCase().includes(q) ||
        asset?.name?.toLowerCase().includes(q) ||
        inc.date?.includes(q) ||
        inc.type?.toLowerCase().includes(q)
      );
    })
    .sort((a: any, b: any) => {
      const da = new Date(a.date).getTime();
      const db = new Date(b.date).getTime();
      return incomeSortDesc ? db - da : da - db;
    });

  const handleChange = (field: keyof typeof form, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors((prev) => ({ ...prev, [field]: "" }));
    }
  };

  const handleIncomeChange = (field: keyof typeof incomeForm, value: string) => {
    setIncomeForm((prev) => ({ ...prev, [field]: value }));
    if (incomeErrors[field]) {
      setIncomeErrors((prev) => ({ ...prev, [field]: "" }));
    }
  };

  const filteredAssets = useMemo(() => {
    const q = assetSearch.trim().toLowerCase();
    return (assets.data || []).filter((asset: any) =>
      !q ||
      asset.symbol?.toLowerCase().includes(q) ||
      asset.name?.toLowerCase().includes(q) ||
      asset.type?.toLowerCase().includes(q)
    );
  }, [assets.data, assetSearch]);

  const selectedAssetLabel = selectedAsset ? `${selectedAsset.symbol} — ${selectedAsset.name}` : labels.transactions.selectAsset;

  const openEditTransaction = (tx: any) => {
    const asset = (assets.data || []).find((a: any) => a.id === tx.asset_id);
    const mode = defaultPriceMode(asset?.type || "");
    setEditTarget(tx);
    setEditForm({
      quantity: String(tx.quantity),
      price: String(tx.price || ""),
      price_mode: mode,
      fee: String(tx.fee),
      date: tx.date,
      notes: tx.notes || "",
    });
    setEditErrors({});
  };

  const handleEditChange = (field: keyof typeof editForm, value: string) => {
    setEditForm((prev) => ({ ...prev, [field]: value }));
    if (editErrors[field]) {
      setEditErrors((prev) => ({ ...prev, [field]: "" }));
    }
  };

  return (
    <div className="space-y-6">
      {transactions.isError && <ErrorMessage error={transactions.error} retry={() => transactions.refetch()} />}
      {income.isError && <ErrorMessage error={income.error} retry={() => income.refetch()} />}
      {assets.isError && <ErrorMessage error={assets.error} retry={() => assets.refetch()} />}
      {create.isError && <ErrorMessage error={create.error} retry={() => create.mutate()} />}
      {createIncome.isError && <ErrorMessage error={createIncome.error} retry={() => createIncome.mutate()} />}
      {update.isError && <ErrorMessage error={update.error} retry={() => { if (editTarget) handleSubmitEdit(); else update.reset(); }} />}
      {remove.isError && <ErrorMessage error={remove.error} retry={() => { if (deleteTarget && deleteTarget.type === "transaction") remove.mutate(deleteTarget.id); else remove.reset(); }} />}
      {removeIncome.isError && <ErrorMessage error={removeIncome.error} retry={() => { if (deleteTarget && deleteTarget.type === "income") removeIncome.mutate(deleteTarget.id); else removeIncome.reset(); }} />}
      <SectionHeader title={labels.transactions.title} />

      <div className="flex gap-2">
        <button
          onClick={() => setTab("transactions")}
          className={`inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${tab === "transactions" ? "bg-accent-blue text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
        >
          {labels.transactions.title}
          <InfoTooltip content={labels.tooltips.transactionType} />
        </button>
        <button
          onClick={() => setTab("income")}
          className={`inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${tab === "income" ? "bg-accent-blue text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
        >
          {labels.transactions.income}
          <InfoTooltip content={labels.tooltips.incomeType} />
        </button>
      </div>

      {tab === "transactions" && (
        <>
          <FintechCard delay={0.1}>
            <h3 className="card-title mb-4">{labels.transactions.addTransaction}</h3>
            <div className="grid grid-cols-1 md:grid-cols-6 gap-3">
              <div className="relative md:col-span-2">
                <div ref={assetRef} className="relative z-50">
                  <input
                    type="text"
                    placeholder={labels.assets.searchAssets}
                    className={`input-fintech pr-10 ${errors.asset_id ? "border-rose-400 focus:border-rose-400 focus:ring-rose-200" : ""}`}
                    value={assetSearchOpen ? assetSearch : selectedAssetLabel}
                    onChange={(e) => {
                      setAssetSearch(e.target.value);
                      setAssetSearchOpen(true);
                    }}
                    onFocus={() => setAssetSearchOpen(true)}
                    aria-invalid={!!errors.asset_id}
                    autoComplete="off"
                  />
                  <span className="absolute right-3 top-1/2 -translate-y-1/2">
                    <InfoTooltip content={labels.tooltips.assetType} position="right" />
                  </span>
                </div>
                {assetSearchOpen &&
                  createPortal(
                    <div
                      className="fixed z-50 max-h-60 overflow-auto rounded-lg border border-slate-200 bg-white shadow-lg"
                      style={assetDropdownStyle}
                    >
                      {filteredAssets.length === 0 && (
                        <div className="px-3 py-2 text-sm text-slate-500">{labels.assets.noAssets}</div>
                      )}
                      {filteredAssets.map((asset: any) => (
                        <button
                          key={asset.id}
                          type="button"
                          className="w-full text-left px-3 py-2 text-sm hover:bg-slate-50 focus:bg-slate-50"
                          onClick={() => {
                            handleChange("asset_id", String(asset.id));
                            handleChange("price_mode", defaultPriceMode(asset.type));
                            setAssetSearch("");
                            setAssetSearchOpen(false);
                          }}
                        >
                          <span className="font-semibold">{asset.symbol}</span>
                          <span className="text-slate-500"> — {asset.name}</span>
                        </button>
                      ))}
                    </div>,
                    document.body
                  )}
                {errors.asset_id && <p className="text-xs text-rose-500 mt-1">{errors.asset_id}</p>}
                {assetSearchOpen && (
                  <div
                    className="fixed inset-0 z-40"
                    onClick={() => {
                      setAssetSearchOpen(false);
                      setAssetSearch("");
                    }}
                  />
                )}
              </div>
              <div className="relative">
                <select
                  className="input-fintech pr-10"
                  value={form.type}
                  onChange={(e) => handleChange("type", e.target.value)}
                >
                  {availableTransactionTypes.map((opt) => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
                <span className="absolute right-8 top-1/2 -translate-y-1/2">
                  <InfoTooltip content={labels.tooltips.transactionType} position="top" />
                </span>
              </div>
              <div className="relative">
                <input
                  type="number"
                  placeholder={labels.transactions.quantity}
                  className={`input-fintech pr-10 ${errors.quantity ? "border-rose-400 focus:border-rose-400 focus:ring-rose-200" : ""}`}
                  value={form.quantity}
                  onChange={(e) => handleChange("quantity", e.target.value)}
                  aria-invalid={!!errors.quantity}
                />
                <span className="absolute right-3 top-1/2 -translate-y-1/2">
                  <InfoTooltip content={labels.tooltips.transactionQuantity} position="top" />
                </span>
                {errors.quantity && <p className="text-xs text-rose-500 mt-1">{errors.quantity}</p>}
              </div>
              <div className="relative md:col-span-2">
                {selectedAsset && isTotalValueAsset(selectedAsset.type) ? (
                  <div className="flex rounded-lg border border-slate-200 bg-slate-50 p-1 gap-1">
                    <div className="flex-1 px-2 py-1.5 text-xs font-medium rounded-md bg-white text-accent-blue shadow-sm text-center">
                      {labels.transactions.totalValue}
                    </div>
                  </div>
                ) : (
                <div className="flex rounded-lg border border-slate-200 bg-slate-50 p-1 gap-1">
                  <button
                    type="button"
                    onClick={() => handleChange("price_mode", "market")}
                    className={`flex-1 px-2 py-1.5 text-xs font-medium rounded-md transition-colors ${form.price_mode === "market"
                      ? "bg-white text-accent-blue shadow-sm"
                      : "text-slate-500 hover:text-slate-700"
                      }`}
                  >
                    {labels.transactions.marketPrice}
                  </button>
                  <button
                    type="button"
                    onClick={() => handleChange("price_mode", "manual")}
                    className={`flex-1 px-2 py-1.5 text-xs font-medium rounded-md transition-colors ${form.price_mode === "manual"
                      ? "bg-white text-accent-blue shadow-sm"
                      : "text-slate-500 hover:text-slate-700"
                      }`}
                  >
                    {labels.transactions.manualPrice}
                  </button>
                </div>
                )}
                <div className="relative mt-1">
                  <FormattedNumberInput
                    mode="currency"
                    decimals={2}
                    placeholder={labels.transactions.price}
                    className={`input-fintech pr-10 ${errors.price ? "border-rose-400 focus:border-rose-400 focus:ring-rose-200" : ""}`}
                    value={form.price}
                    disabled={form.price_mode === "market" && !(selectedAsset && isTotalValueAsset(selectedAsset.type))}
                    onChange={(value) => handleChange("price", value)}
                    aria-invalid={!!errors.price}
                  />
                  <span className="absolute right-3 top-1/2 -translate-y-1/2">
                    <InfoTooltip content={form.price_mode === "market" ? labels.transactions.pricePreview : labels.tooltips.transactionPrice} position="right" />
                  </span>
                  {form.price_mode === "market" && marketPricePreview.isLoading && (
                    <span className="absolute right-10 top-1/2 -translate-y-1/2 text-xs text-slate-400">{labels.common.loading}</span>
                  )}
                  {errors.price && <p className="text-xs text-rose-500 mt-1">{errors.price}</p>}
                </div>
              </div>
              <div className="relative">
                <FormattedNumberInput
                  mode="currency"
                  decimals={2}
                  placeholder={labels.transactions.fee}
                  className={`input-fintech pr-10 ${errors.fee ? "border-rose-400 focus:border-rose-400 focus:ring-rose-200" : ""}`}
                  value={form.fee}
                  onChange={(value) => handleChange("fee", value)}
                  aria-invalid={!!errors.fee}
                />
                <span className="absolute right-3 top-1/2 -translate-y-1/2">
                  <InfoTooltip content={labels.tooltips.transactionFee} position="right" />
                </span>
                {errors.fee && <p className="text-xs text-rose-500 mt-1">{errors.fee}</p>}
              </div>
              <div className="relative">
                <input
                  type="date"
                  className={`input-fintech pr-10 ${errors.date ? "border-rose-400 focus:border-rose-400 focus:ring-rose-200" : ""}`}
                  value={form.date}
                  onChange={(e) => handleChange("date", e.target.value)}
                  aria-invalid={!!errors.date}
                />
                <span className="absolute right-3 top-1/2 -translate-y-1/2">
                  <InfoTooltip content={labels.tooltips.backtestStartDate} position="right" />
                </span>
                {errors.date && <p className="text-xs text-rose-500 mt-1">{errors.date}</p>}
              </div>
              <input
                type="text"
                placeholder={labels.transactions.notes}
                className="input-fintech md:col-span-4"
                value={form.notes}
                onChange={(e) => handleChange("notes", e.target.value)}
              />
            </div>
            <button
              onClick={handleSubmitTransaction}
              disabled={create.isPending}
              className="btn-primary mt-3"
            >
              <Plus className="w-4 h-4" />
              {labels.transactions.add}
            </button>
          </FintechCard>

          <FintechCard delay={0.15}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="card-title">{labels.transactions.list}</h3>
              <div className="flex items-center gap-2">
                <div className="relative w-40 md:w-56">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                  <input
                    type="text"
                    value={transactionSearch}
                    onChange={(e) => setTransactionSearch(e.target.value)}
                    placeholder="Tìm kiếm..."
                    className="input-fintech pl-9 w-full"
                  />
                </div>
                <button
                  onClick={() => setTransactionSortDesc((prev) => !prev)}
                  className="btn-secondary px-2"
                  title={transactionSortDesc ? "Sắp xếp cũ nhất trước" : "Sắp xếp mới nhất trước"}
                  aria-label={transactionSortDesc ? "Sắp xếp cũ nhất trước" : "Sắp xếp mới nhất trước"}
                >
                  <ArrowDownUp className="w-4 h-4" />
                </button>
              </div>
            </div>
            {transactions.isLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-8" count={6} />
              </div>
            ) : (
              <div className="overflow-x-auto scrollbar-thin">
                <table className="table-fintech">
                  <thead>
                    <tr>
                      <th className="text-left">
                        {labels.transactions.dateCol}
                        <InfoTooltip content={labels.tooltips.backtestStartDate} />
                      </th>
                      <th className="text-left">
                        {labels.transactions.assetCol}
                        <InfoTooltip content={labels.tooltips.assetName} />
                      </th>
                      <th className="text-left">
                        {labels.transactions.typeCol}
                        <InfoTooltip content={labels.tooltips.transactionType} />
                      </th>
                      <th className="text-right">
                        {labels.transactions.quantityCol}
                        <InfoTooltip content={labels.tooltips.transactionQuantity} />
                      </th>
                      <th className="text-right">
                        {labels.transactions.priceCol}
                        <InfoTooltip content={labels.tooltips.transactionPrice} />
                      </th>
                      <th className="text-right">
                        {labels.transactions.feeCol}
                        <InfoTooltip content={labels.tooltips.transactionFee} />
                      </th>
                      <th className="text-right">{labels.transactions.actionsCol}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredTransactions.map((tx: any) => {
                      const asset = assets.data?.find((a: any) => a.id === tx.asset_id);
                      return (
                        <tr key={tx.id}>
                          <td className="font-mono text-slate-500">{formatDate(tx.date, dateFormat)}</td>
                          <td>
                            <div className="font-display font-semibold text-slate-900 whitespace-nowrap">
                              {asset ? asset.symbol : `#${tx.asset_id}`}
                            </div>
                            <span className="text-xs text-slate-500 max-w-[120px] truncate block">{asset ? asset.name : "(đã xóa)"}</span>
                          </td>
                          <td>
                            <span className={transactionTypeBadgeClass(tx.type)}>
                              {transactionTypeLabel(tx.type)}
                            </span>
                          </td>
                          <td className="value-cell" title={String(tx.quantity)}>{tx.quantity}</td>
                          <td className="value-cell" title={formatCurrency(tx.price)}>{formatCurrency(tx.price)}</td>
                          <td className="value-cell" title={formatCurrency(tx.fee)}>{formatCurrency(tx.fee)}</td>
                          <td className="text-right">
                            <div className="inline-flex items-center gap-1">
                              <button
                                onClick={() => openEditTransaction(tx)}
                                disabled={update.isPending}
                                className="inline-flex items-center justify-center p-2 rounded-lg text-accent-blue hover:bg-accent-blue/10 transition-colors disabled:opacity-50"
                                aria-label="Sửa giao dịch"
                              >
                                <Pencil className="w-4 h-4" />
                              </button>
                              <button
                                onClick={() => setDeleteTarget({ id: tx.id, label: asset ? `${asset.symbol} — ${formatDate(tx.date, dateFormat)}` : `#${tx.asset_id} (đã xóa)`, type: "transaction" })}
                                disabled={remove.isPending}
                                className="inline-flex items-center justify-center p-2 rounded-lg text-accent-rose hover:bg-accent-rose/10 transition-colors disabled:opacity-50"
                                aria-label="Xóa giao dịch"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                    {filteredTransactions.length === 0 && (
                      <tr>
                        <td colSpan={7} className="px-4 py-4">
                          <EmptyState
                            title={labels.transactions.noTransactions}
                            description={labels.dashboard.addAssetsHint}
                            action={
                              <Link to="/assets" className="btn-primary">
                                <Plus className="w-4 h-4" />
                                {labels.assets.addAsset}
                              </Link>
                            }
                          />
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </FintechCard>
        </>
      )
      }

      {
        tab === "income" && (
          <>
            <FintechCard delay={0.1}>
              <h3 className="card-title mb-4">{labels.transactions.addIncome}</h3>
              <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
                <div className="relative">
                  <select
                    className={`input-fintech pr-10 ${incomeErrors.asset_id ? "border-rose-400 focus:border-rose-400 focus:ring-rose-200" : ""}`}
                    value={incomeForm.asset_id}
                    onChange={(e) => handleIncomeChange("asset_id", e.target.value)}
                    aria-invalid={!!incomeErrors.asset_id}
                  >
                    <option value="">{labels.transactions.selectAsset}</option>
                    {assets.data?.map((asset: any) => (
                      <option key={asset.id} value={asset.id}>
                        {asset.symbol} — {asset.name}
                      </option>
                    ))}
                  </select>
                  <span className="absolute right-8 top-1/2 -translate-y-1/2">
                    <InfoTooltip content={labels.tooltips.assetType} position="right" />
                  </span>
                  {incomeErrors.asset_id && <p className="text-xs text-rose-500 mt-1">{incomeErrors.asset_id}</p>}
                </div>
                <div className="relative">
                  <select
                    className="input-fintech pr-10"
                    value={incomeForm.type}
                    onChange={(e) => handleIncomeChange("type", e.target.value)}
                  >
                    <option value="DIVIDEND">{labels.transactions.dividend}</option>
                    <option value="INTEREST">{labels.transactions.interest}</option>
                  </select>
                  <span className="absolute right-8 top-1/2 -translate-y-1/2">
                    <InfoTooltip content={labels.tooltips.incomeType} position="right" />
                  </span>
                </div>
                <div className="relative">
                  <FormattedNumberInput
                    mode="currency"
                    decimals={2}
                    placeholder={labels.transactions.amount}
                    className={`input-fintech pr-10 ${incomeErrors.amount ? "border-rose-400 focus:border-rose-400 focus:ring-rose-200" : ""}`}
                    value={incomeForm.amount}
                    onChange={(value) => handleIncomeChange("amount", value)}
                    aria-invalid={!!incomeErrors.amount}
                  />
                  <span className="absolute right-3 top-1/2 -translate-y-1/2">
                    <InfoTooltip content={labels.tooltips.transactionPrice} position="right" />
                  </span>
                  {incomeErrors.amount && <p className="text-xs text-rose-500 mt-1">{incomeErrors.amount}</p>}
                </div>
                <div className="relative">
                  <input
                    type="date"
                    className={`input-fintech pr-10 ${incomeErrors.date ? "border-rose-400 focus:border-rose-400 focus:ring-rose-200" : ""}`}
                    value={incomeForm.date}
                    onChange={(e) => handleIncomeChange("date", e.target.value)}
                    aria-invalid={!!incomeErrors.date}
                  />
                  <span className="absolute right-3 top-1/2 -translate-y-1/2">
                    <InfoTooltip content={labels.tooltips.backtestStartDate} position="right" />
                  </span>
                  {incomeErrors.date && <p className="text-xs text-rose-500 mt-1">{incomeErrors.date}</p>}
                </div>
                <input
                  type="text"
                  placeholder={labels.transactions.notes}
                  className="input-fintech"
                  value={incomeForm.notes}
                  onChange={(e) => handleIncomeChange("notes", e.target.value)}
                />
              </div>
              <button
                onClick={handleSubmitIncome}
                disabled={createIncome.isPending}
                className="btn-primary mt-3"
              >
                <Plus className="w-4 h-4" />
                {labels.transactions.addIncome}
              </button>
            </FintechCard>

            <FintechCard delay={0.15}>
              <div className="flex items-center justify-between mb-4">
                <h3 className="card-title">{labels.transactions.incomeList}</h3>
                <div className="flex items-center gap-2">
                  <div className="relative w-40 md:w-56">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <input
                      type="text"
                      value={incomeSearch}
                      onChange={(e) => setIncomeSearch(e.target.value)}
                      placeholder="Tìm kiếm..."
                      className="input-fintech pl-9 w-full"
                    />
                  </div>
                  <button
                    onClick={() => setIncomeSortDesc((prev) => !prev)}
                    className="btn-secondary px-2"
                    title={incomeSortDesc ? "Sắp xếp cũ nhất trước" : "Sắp xếp mới nhất trước"}
                    aria-label={incomeSortDesc ? "Sắp xếp cũ nhất trước" : "Sắp xếp mới nhất trước"}
                  >
                    <ArrowDownUp className="w-4 h-4" />
                  </button>
                </div>
              </div>
              {income.isLoading ? (
                <div className="space-y-3">
                  <Skeleton className="h-8" count={4} />
                </div>
              ) : (
                <div className="overflow-x-auto scrollbar-thin">
                  <table className="table-fintech">
                    <thead>
                      <tr>
                        <th className="text-left">
                          {labels.transactions.dateCol}
                          <InfoTooltip content={labels.tooltips.backtestStartDate} />
                        </th>
                        <th className="text-left">
                          {labels.transactions.assetCol}
                          <InfoTooltip content={labels.tooltips.assetName} />
                        </th>
                        <th className="text-left">
                          {labels.transactions.incomeType}
                          <InfoTooltip content={labels.tooltips.incomeType} />
                        </th>
                        <th className="text-right">
                          {labels.transactions.amount}
                          <InfoTooltip content={labels.tooltips.transactionPrice} />
                        </th>
                        <th className="text-right">{labels.transactions.actionsCol}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredIncome.map((inc: any) => {
                        const asset = assets.data?.find((a: any) => a.id === inc.asset_id);
                        return (
                          <tr key={inc.id}>
                            <td className="font-mono text-slate-500">{formatDate(inc.date, dateFormat)}</td>
                            <td>
                              <div className="font-display font-semibold text-slate-900 whitespace-nowrap">
                                {asset ? asset.symbol : `#${inc.asset_id}`}
                              </div>
                              <span className="text-xs text-slate-500 max-w-[120px] truncate block">{asset ? asset.name : "(đã xóa)"}</span>
                            </td>
                            <td>
                              <span className="badge-gain">
                                {inc.type === "DIVIDEND" ? labels.transactions.dividend : labels.transactions.interest}
                              </span>
                            </td>
                            <td className="value-cell" title={formatCurrency(inc.amount)}>{formatCurrency(inc.amount)}</td>
                            <td className="text-right">
                              <button
                                onClick={() => setDeleteTarget({ id: inc.id, label: asset ? `${asset.symbol} — ${formatDate(inc.date, dateFormat)}` : `#${inc.asset_id} (đã xóa)`, type: "income" })}
                                disabled={removeIncome.isPending}
                                className="inline-flex items-center justify-center p-2 rounded-lg text-accent-rose hover:bg-accent-rose/10 transition-colors disabled:opacity-50"
                                aria-label="Xóa thu nhập"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </td>
                          </tr>
                        );
                      })}
                      {filteredIncome.length === 0 && (
                        <tr>
                          <td colSpan={5} className="px-4 py-4">
                            <EmptyState
                              title={labels.transactions.noIncome}
                              description={labels.transactions.addIncomeHint}
                              action={
                                <Link to="/assets" className="btn-primary">
                                  <Plus className="w-4 h-4" />
                                  {labels.assets.addAsset}
                                </Link>
                              }
                            />
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              )}
            </FintechCard>
          </>
        )
      }
      {editTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4">
          <div className="w-full max-w-2xl rounded-xl bg-white shadow-xl p-6 space-y-4">
            <h3 className="card-title">{labels.transactions.editTransaction}</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">{labels.transactions.assetCol}</label>
                <input type="text" disabled value={(() => {
                  const asset = (assets.data || []).find((a: any) => a.id === editTarget.asset_id);
                  return asset ? `${asset.symbol} — ${asset.name}` : `#${editTarget.asset_id} (đã xóa)`;
                })()} className="input-fintech bg-slate-50" />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">{labels.transactions.typeCol}</label>
                <input type="text" disabled value={transactionTypeLabel(editTarget.type)} className="input-fintech bg-slate-50" />
              </div>
              <div className="relative">
                <input
                  type="number"
                  placeholder={labels.transactions.quantity}
                  className={`input-fintech pr-10 ${editErrors.quantity ? "border-rose-400 focus:border-rose-400 focus:ring-rose-200" : ""}`}
                  value={editForm.quantity}
                  onChange={(e) => handleEditChange("quantity", e.target.value)}
                />
                {editErrors.quantity && <p className="text-xs text-rose-500 mt-1">{editErrors.quantity}</p>}
              </div>
              <div className="relative md:col-span-2">
                {(() => {
                  const editAsset = (assets.data || []).find((a: any) => a.id === editTarget.asset_id);
                  const editIsTotalValue = editAsset && isTotalValueAsset(editAsset.type);
                  return (
                <>
                <div className="flex rounded-lg border border-slate-200 bg-slate-50 p-1 gap-1 mb-1">
                  {editIsTotalValue ? (
                    <div className="flex-1 px-2 py-1.5 text-xs font-medium rounded-md bg-white text-accent-blue shadow-sm text-center">
                      {labels.transactions.totalValue}
                    </div>
                  ) : (
                  <>
                  <button
                    type="button"
                    onClick={() => handleEditChange("price_mode", "market")}
                    className={`flex-1 px-2 py-1.5 text-xs font-medium rounded-md transition-colors ${editForm.price_mode === "market" ? "bg-white text-accent-blue shadow-sm" : "text-slate-500"
                      }`}
                  >
                    {labels.transactions.marketPrice}
                  </button>
                  <button
                    type="button"
                    onClick={() => handleEditChange("price_mode", "manual")}
                    className={`flex-1 px-2 py-1.5 text-xs font-medium rounded-md transition-colors ${editForm.price_mode === "manual" ? "bg-white text-accent-blue shadow-sm" : "text-slate-500"
                      }`}
                  >
                    {labels.transactions.manualPrice}
                  </button>
                  </>
                  )}
                </div>
                <FormattedNumberInput
                  mode="currency"
                  decimals={2}
                  placeholder={labels.transactions.price}
                  className={`input-fintech pr-10 ${editErrors.price ? "border-rose-400 focus:border-rose-400 focus:ring-rose-200" : ""}`}
                  value={editForm.price}
                  disabled={editForm.price_mode === "market" && !editIsTotalValue}
                  onChange={(value) => handleEditChange("price", value)}
                />
                {editForm.price_mode === "market" && !editIsTotalValue && editMarketPricePreview.isLoading && (
                  <span className="absolute right-10 top-1/2 -translate-y-1/2 text-xs text-slate-400">{labels.common.loading}</span>
                )}
                {editErrors.price && <p className="text-xs text-rose-500 mt-1">{editErrors.price}</p>}
                </>
                  );
                })()}
              </div>
              <div className="relative">
                <FormattedNumberInput
                  mode="currency"
                  decimals={2}
                  placeholder={labels.transactions.fee}
                  className={`input-fintech pr-10 ${editErrors.fee ? "border-rose-400 focus:border-rose-400 focus:ring-rose-200" : ""}`}
                  value={editForm.fee}
                  onChange={(value) => handleEditChange("fee", value)}
                />
                {editErrors.fee && <p className="text-xs text-rose-500 mt-1">{editErrors.fee}</p>}
              </div>
              <div className="relative">
                <input
                  type="date"
                  className={`input-fintech pr-10 ${editErrors.date ? "border-rose-400 focus:border-rose-400 focus:ring-rose-200" : ""}`}
                  value={editForm.date}
                  onChange={(e) => handleEditChange("date", e.target.value)}
                />
                {editErrors.date && <p className="text-xs text-rose-500 mt-1">{editErrors.date}</p>}
              </div>
              <input
                type="text"
                placeholder={labels.transactions.notes}
                className="input-fintech md:col-span-2"
                value={editForm.notes}
                onChange={(e) => handleEditChange("notes", e.target.value)}
              />
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
                onClick={handleSubmitEdit}
                disabled={update.isPending}
                className="btn-primary"
              >
                {update.isPending ? labels.common.saving : labels.transactions.saveTransaction}
              </button>
            </div>
          </div>
        </div>
      )}

      <ConfirmDialog
        open={!!deleteTarget}
        title={`Xác nhận xóa ${deleteTarget?.type === "income" ? "thu nhập" : "giao dịch"}`}
        message={`Bạn có chắc muốn xóa "${deleteTarget?.label ?? ""}"? Thao tác này không thể hoàn tác.`}
        confirmLabel={labels.common.delete}
        cancelLabel={labels.common.cancel}
        variant="danger"
        isLoading={deleteTarget?.type === "income" ? removeIncome.isPending : remove.isPending}
        onConfirm={() => {
          if (!deleteTarget) return;
          if (deleteTarget.type === "income") {
            removeIncome.mutate(deleteTarget.id);
          } else {
            remove.mutate(deleteTarget.id);
          }
        }}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}
