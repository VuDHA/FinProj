import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { Link } from "react-router-dom";
import API from "../api/client";
import { ErrorMessage } from "../components/ErrorMessage";
import { EmptyState } from "../components/EmptyState";
import { InfoTooltip } from "../components/InfoTooltip";
import { FintechCard } from "../components/ui/FintechCard";
import { SectionHeader } from "../components/ui/SectionHeader";
import { labels } from "../i18n/vi";
import { formatCurrency } from "../lib/utils";

export function Transactions() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<"transactions" | "income">("transactions");
  const [form, setForm] = useState({
    asset_id: "",
    type: "BUY",
    quantity: "",
    price: "",
    fee: "0",
    date: new Date().toISOString().split("T")[0],
    notes: "",
  });

  const [incomeForm, setIncomeForm] = useState({
    asset_id: "",
    type: "DIVIDEND",
    amount: "",
    date: new Date().toISOString().split("T")[0],
    notes: "",
  });

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

  const create = useMutation({
    mutationFn: () =>
      API.post("/transactions/", {
        ...form,
        asset_id: Number(form.asset_id),
        quantity: Number(form.quantity),
        price: Number(form.price),
        fee: Number(form.fee),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["transactions"] });
      qc.invalidateQueries({ queryKey: ["portfolio"] });
      setForm({
        asset_id: "",
        type: "BUY",
        quantity: "",
        price: "",
        fee: "0",
        date: new Date().toISOString().split("T")[0],
        notes: "",
      });
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
    },
  });

  const remove = useMutation({
    mutationFn: (id: number) => API.delete(`/transactions/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["transactions"] });
      qc.invalidateQueries({ queryKey: ["portfolio"] });
    },
  });

  const removeIncome = useMutation({
    mutationFn: (id: number) => API.delete(`/income/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["income"] });
      qc.invalidateQueries({ queryKey: ["analytics"] });
    },
  });

  return (
    <div className="space-y-6">
      {transactions.isError && <ErrorMessage error={transactions.error} retry={() => transactions.refetch()} />}
      {income.isError && <ErrorMessage error={income.error} retry={() => income.refetch()} />}
      {assets.isError && <ErrorMessage error={assets.error} retry={() => assets.refetch()} />}
      {create.isError && <ErrorMessage error={create.error} retry={() => create.mutate()} />}
      {createIncome.isError && <ErrorMessage error={createIncome.error} retry={() => createIncome.mutate()} />}
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
            <div className="grid grid-cols-1 md:grid-cols-6 gap-3">
              <div className="relative">
                <select
                  className="input-fintech pr-10"
                  value={form.asset_id}
                  onChange={(e) => setForm({ ...form, asset_id: e.target.value })}
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
              </div>
              <div className="relative">
                <select
                  className="input-fintech pr-10"
                  value={form.type}
                  onChange={(e) => setForm({ ...form, type: e.target.value })}
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
                  className="input-fintech pr-10"
                  value={form.quantity}
                  onChange={(e) => setForm({ ...form, quantity: e.target.value })}
                />
                <span className="absolute right-3 top-1/2 -translate-y-1/2">
                  <InfoTooltip content={labels.tooltips.transactionQuantity} position="right" />
                </span>
              </div>
              <div className="relative">
                <input
                  type="number"
                  placeholder={labels.transactions.price}
                  className="input-fintech pr-10"
                  value={form.price}
                  onChange={(e) => setForm({ ...form, price: e.target.value })}
                />
                <span className="absolute right-3 top-1/2 -translate-y-1/2">
                  <InfoTooltip content={labels.tooltips.transactionPrice} position="right" />
                </span>
              </div>
              <div className="relative">
                <input
                  type="number"
                  placeholder={labels.transactions.fee}
                  className="input-fintech pr-10"
                  value={form.fee}
                  onChange={(e) => setForm({ ...form, fee: e.target.value })}
                />
                <span className="absolute right-3 top-1/2 -translate-y-1/2">
                  <InfoTooltip content={labels.tooltips.transactionFee} position="right" />
                </span>
              </div>
              <div className="relative">
                <input
                  type="date"
                  className="input-fintech pr-10"
                  value={form.date}
                  onChange={(e) => setForm({ ...form, date: e.target.value })}
                />
                <span className="absolute right-3 top-1/2 -translate-y-1/2">
                  <InfoTooltip content={labels.tooltips.backtestStartDate} position="right" />
                </span>
              </div>
              <input
                type="text"
                placeholder={labels.transactions.notes}
                className="input-fintech md:col-span-6"
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
              />
            </div>
            <button
              onClick={() => create.mutate()}
              disabled={!form.asset_id || !form.quantity || !form.price || create.isPending}
              className="btn-primary mt-3"
            >
              <Plus className="w-4 h-4" />
              {labels.transactions.add}
            </button>
          </FintechCard>

          <FintechCard delay={0.15}>
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
                  {transactions.data?.map((tx: any) => {
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
                            onClick={() => remove.mutate(tx.id)}
                            disabled={remove.isPending}
                            className="inline-flex items-center justify-center p-2 rounded-lg text-accent-rose hover:bg-accent-rose/10 transition-colors disabled:opacity-50"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                  {transactions.data?.length === 0 && (
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
                    className="input-fintech pr-10"
                    value={incomeForm.asset_id}
                    onChange={(e) => setIncomeForm({ ...incomeForm, asset_id: e.target.value })}
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
                </div>
                <div className="relative">
                  <select
                    className="input-fintech pr-10"
                    value={incomeForm.type}
                    onChange={(e) => setIncomeForm({ ...incomeForm, type: e.target.value })}
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
                    className="input-fintech pr-10"
                    value={incomeForm.amount}
                    onChange={(e) => setIncomeForm({ ...incomeForm, amount: e.target.value })}
                  />
                  <span className="absolute right-3 top-1/2 -translate-y-1/2">
                    <InfoTooltip content={labels.tooltips.transactionPrice} position="right" />
                  </span>
                </div>
                <div className="relative">
                  <input
                    type="date"
                    className="input-fintech pr-10"
                    value={incomeForm.date}
                    onChange={(e) => setIncomeForm({ ...incomeForm, date: e.target.value })}
                  />
                  <span className="absolute right-3 top-1/2 -translate-y-1/2">
                    <InfoTooltip content={labels.tooltips.backtestStartDate} position="right" />
                  </span>
                </div>
                <input
                  type="text"
                  placeholder={labels.transactions.notes}
                  className="input-fintech"
                  value={incomeForm.notes}
                  onChange={(e) => setIncomeForm({ ...incomeForm, notes: e.target.value })}
                />
              </div>
              <button
                onClick={() => createIncome.mutate()}
                disabled={!incomeForm.asset_id || !incomeForm.amount || createIncome.isPending}
                className="btn-primary mt-3"
              >
                <Plus className="w-4 h-4" />
                {labels.transactions.addIncome}
              </button>
            </FintechCard>

            <FintechCard delay={0.15}>
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
                    {income.data?.map((inc: any) => {
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
                              onClick={() => removeIncome.mutate(inc.id)}
                              disabled={removeIncome.isPending}
                              className="inline-flex items-center justify-center p-2 rounded-lg text-accent-rose hover:bg-accent-rose/10 transition-colors disabled:opacity-50"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                    {income.data?.length === 0 && (
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
            </FintechCard>
          </>
        )
      }
    </div >
  );
}
