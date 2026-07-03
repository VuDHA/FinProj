import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { ArrowDownUp, Plus, Search, Trash2 } from "lucide-react";
import { Link } from "react-router-dom";
import { getAssets } from "../api/assets";
import {
  createIncome,
  createTransaction,
  deleteIncome,
  deleteTransaction,
  getIncome,
  getTransactions,
  type IncomeCreate,
  type TransactionCreate,
} from "../api/transactions";
import { ErrorMessage } from "../components/ErrorMessage";
import { EmptyState } from "../components/EmptyState";
import { InfoTooltip } from "../components/InfoTooltip";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { FintechCard } from "../components/ui/FintechCard";
import { SectionHeader } from "../components/ui/SectionHeader";
import { Skeleton } from "../components/ui/Skeleton";
import { useToast } from "../contexts/ToastContext";
import { usePersistentState } from "../hooks/usePersistentState";
import { labels } from "../i18n/vi";
import { formatCurrency } from "../lib/format";
import { hasErrors, nonNegativeNumber, notFutureDate, positiveNumber, required, validateForm } from "../lib/validation";

export function Transactions() {
  const qc = useQueryClient();
  const { showToast } = useToast();
  const [tab, setTab] = usePersistentState<"transactions" | "income">("transactions.tab", "transactions");
  const [form, setForm] = usePersistentState("transactions.form", {
    asset_id: "",
    type: "BUY",
    quantity: "",
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
  const [transactionSearch, setTransactionSearch] = usePersistentState("transactions.search", "");
  const [incomeSearch, setIncomeSearch] = usePersistentState("transactions.incomeSearch", "");
  const [transactionSortDesc, setTransactionSortDesc] = usePersistentState("transactions.sortDesc", true);
  const [incomeSortDesc, setIncomeSortDesc] = usePersistentState("transactions.incomeSortDesc", true);

  const transactions = useQuery({
    queryKey: ["transactions"],
    queryFn: async () => getTransactions(),
  });

  const income = useQuery({
    queryKey: ["income"],
    queryFn: async () => getIncome(),
  });

  const assets = useQuery({
    queryKey: ["assets"],
    queryFn: async () => getAssets(),
  });

  const create = useMutation({
    mutationFn: () =>
      createTransaction({
        ...form,
        asset_id: Number(form.asset_id),
        type: form.type as TransactionCreate["type"],
        quantity: Number(form.quantity),
        fee: Number(form.fee),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["transactions"] });
      qc.invalidateQueries({ queryKey: ["portfolio"] });
      setForm({
        asset_id: "",
        type: "BUY",
        quantity: "",
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

  const createIncomeMutation = useMutation({
    mutationFn: () =>
      createIncome({
        ...incomeForm,
        asset_id: Number(incomeForm.asset_id),
        type: incomeForm.type as IncomeCreate["type"],
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

  const remove = useMutation({
    mutationFn: (id: number) => deleteTransaction(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["transactions"] });
      qc.invalidateQueries({ queryKey: ["portfolio"] });
      showToast("Đã xóa giao dịch", "success");
      setDeleteTarget(null);
    },
    onError: (error: any) => {
      showToast(error?.response?.data?.detail || "Không thể xóa giao dịch", "error");
      setDeleteTarget(null);
    },
  });

  const removeIncome = useMutation({
    mutationFn: (id: number) => deleteIncome(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["income"] });
      qc.invalidateQueries({ queryKey: ["analytics"] });
      showToast("Đã xóa thu nhập", "success");
      setDeleteTarget(null);
    },
    onError: (error: any) => {
      showToast(error?.response?.data?.detail || "Không thể xóa thu nhập", "error");
      setDeleteTarget(null);
    },
  });

  const handleSubmitTransaction = () => {
    const validationErrors = validateForm({
      asset_id: { value: form.asset_id, validators: [required("Vui lòng chọn tài sản")] },
      quantity: { value: form.quantity, validators: [positiveNumber("Số lượng phải lớn hơn 0")] },
      fee: { value: form.fee, validators: [nonNegativeNumber("Phí không được âm")] },
      date: { value: form.date, validators: [notFutureDate("Ngày không được trong tương lai")] },
    });
    setErrors(validationErrors);
    if (hasErrors(validationErrors)) return;
    create.mutate();
  };

  const handleSubmitIncome = () => {
    const validationErrors = validateForm({
      asset_id: { value: incomeForm.asset_id, validators: [required("Vui lòng chọn tài sản")] },
      amount: { value: incomeForm.amount, validators: [positiveNumber("Số tiền phải lớn hơn 0")] },
      date: { value: incomeForm.date, validators: [notFutureDate("Ngày không được trong tương lai")] },
    });
    setIncomeErrors(validationErrors);
    if (hasErrors(validationErrors)) return;
    createIncomeMutation.mutate();
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

  return (
    <div className="space-y-6">
      {transactions.isError && <ErrorMessage error={transactions.error} retry={() => transactions.refetch()} />}
      {income.isError && <ErrorMessage error={income.error} retry={() => income.refetch()} />}
      {assets.isError && <ErrorMessage error={assets.error} retry={() => assets.refetch()} />}
      {create.isError && <ErrorMessage error={create.error} retry={() => create.mutate()} />}
      {createIncomeMutation.isError && <ErrorMessage error={createIncomeMutation.error} retry={() => createIncomeMutation.mutate()} />}
      {remove.isError && <ErrorMessage error={remove.error} retry={() => remove.reset()} />}
      {removeIncome.isError && <ErrorMessage error={removeIncome.error} retry={() => removeIncome.reset()} />}
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
            <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
              <div className="relative">
                <select
                  className={`input-fintech pr-10 ${errors.asset_id ? "border-rose-400 focus:border-rose-400 focus:ring-rose-200" : ""}`}
                  value={form.asset_id}
                  onChange={(e) => handleChange("asset_id", e.target.value)}
                  aria-invalid={!!errors.asset_id}
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
                {errors.asset_id && <p className="text-xs text-rose-500 mt-1">{errors.asset_id}</p>}
              </div>
              <div className="relative">
                <select
                  className="input-fintech pr-10"
                  value={form.type}
                  onChange={(e) => handleChange("type", e.target.value)}
                >
                  <option value="BUY">{labels.transactions.buy}</option>
                  <option value="SELL">{labels.transactions.sell}</option>
                </select>
                <span className="absolute right-8 top-1/2 -translate-y-1/2">
                  <InfoTooltip content={labels.tooltips.transactionType} position="right" />
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
                  <InfoTooltip content={labels.tooltips.transactionQuantity} position="right" />
                </span>
                {errors.quantity && <p className="text-xs text-rose-500 mt-1">{errors.quantity}</p>}
              </div>
              <div className="relative">
                <input
                  type="number"
                  placeholder={labels.transactions.fee}
                  className={`input-fintech pr-10 ${errors.fee ? "border-rose-400 focus:border-rose-400 focus:ring-rose-200" : ""}`}
                  value={form.fee}
                  onChange={(e) => handleChange("fee", e.target.value)}
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
                className="input-fintech md:col-span-5"
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
                          <td className="font-mono text-slate-500">{tx.date}</td>
                          <td>
                            <div className="font-display font-semibold text-slate-900">
                              {asset ? asset.symbol : tx.asset_id}
                            </div>
                            <span className="text-xs text-slate-500">{asset ? asset.name : "-"}</span>
                          </td>
                          <td>
                            <span className={tx.type === "BUY" ? "badge-gain" : "badge-loss"}>
                              {tx.type === "BUY" ? labels.transactions.buy : labels.transactions.sell}
                            </span>
                          </td>
                          <td className="text-right font-mono">{tx.quantity}</td>
                          <td className="text-right font-mono">{formatCurrency(tx.price)}</td>
                          <td className="text-right font-mono">{formatCurrency(tx.fee)}</td>
                          <td className="text-right">
                            <button
                              onClick={() => setDeleteTarget({ id: tx.id, label: asset ? `${asset.symbol} — ${tx.date}` : String(tx.id), type: "transaction" })}
                              disabled={remove.isPending}
                              className="inline-flex items-center justify-center p-2 rounded-lg text-accent-rose hover:bg-accent-rose/10 transition-colors disabled:opacity-50"
                              aria-label="Xóa giao dịch"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
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
                  <input
                    type="number"
                    placeholder={labels.transactions.amount}
                    className={`input-fintech pr-10 ${incomeErrors.amount ? "border-rose-400 focus:border-rose-400 focus:ring-rose-200" : ""}`}
                    value={incomeForm.amount}
                    onChange={(e) => handleIncomeChange("amount", e.target.value)}
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
                disabled={createIncomeMutation.isPending}
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
                            <td className="font-mono text-slate-500">{inc.date}</td>
                            <td>
                              <div className="font-display font-semibold text-slate-900">
                                {asset ? asset.symbol : inc.asset_id}
                              </div>
                              <span className="text-xs text-slate-500">{asset ? asset.name : "-"}</span>
                            </td>
                            <td>
                              <span className="badge-gain">
                                {inc.type === "DIVIDEND" ? labels.transactions.dividend : labels.transactions.interest}
                              </span>
                            </td>
                            <td className="text-right font-mono">{formatCurrency(inc.amount)}</td>
                            <td className="text-right">
                              <button
                                onClick={() => setDeleteTarget({ id: inc.id, label: asset ? `${asset.symbol} — ${inc.date}` : String(inc.id), type: "income" })}
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
