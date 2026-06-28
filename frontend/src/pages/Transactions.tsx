import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import API from "../api/client";
import { ErrorMessage } from "../components/ErrorMessage";
import { FintechCard } from "../components/ui/FintechCard";
import { SectionHeader } from "../components/ui/SectionHeader";
import { labels } from "../i18n/vi";
import { formatCurrency } from "../lib/utils";

export function Transactions() {
  const qc = useQueryClient();
  const [form, setForm] = useState({
    asset_id: "",
    type: "BUY",
    quantity: "",
    price: "",
    fee: "0",
    date: new Date().toISOString().split("T")[0],
    notes: "",
  });

  const transactions = useQuery({
    queryKey: ["transactions"],
    queryFn: async () => (await API.get("/transactions/")).data,
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

  const remove = useMutation({
    mutationFn: (id: number) => API.delete(`/transactions/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["transactions"] });
      qc.invalidateQueries({ queryKey: ["portfolio"] });
    },
  });

  return (
    <div className="space-y-6">
      {transactions.isError && <ErrorMessage error={transactions.error} retry={() => transactions.refetch()} />}
      {assets.isError && <ErrorMessage error={assets.error} retry={() => assets.refetch()} />}
      {create.isError && <ErrorMessage error={create.error} retry={() => create.mutate()} />}
      {remove.isError && <ErrorMessage error={remove.error} retry={() => remove.reset()} />}
      <SectionHeader title={labels.transactions.title} />

      <FintechCard delay={0.1}>
        <h3 className="card-title mb-4">{labels.transactions.addTransaction}</h3>
        <div className="grid grid-cols-1 md:grid-cols-6 gap-3">
          <select
            className="input-fintech"
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
          <select
            className="input-fintech"
            value={form.type}
            onChange={(e) => setForm({ ...form, type: e.target.value })}
          >
            <option value="BUY">{labels.transactions.buy}</option>
            <option value="SELL">{labels.transactions.sell}</option>
          </select>
          <input
            type="number"
            placeholder={labels.transactions.quantity}
            className="input-fintech"
            value={form.quantity}
            onChange={(e) => setForm({ ...form, quantity: e.target.value })}
          />
          <input
            type="number"
            placeholder={labels.transactions.price}
            className="input-fintech"
            value={form.price}
            onChange={(e) => setForm({ ...form, price: e.target.value })}
          />
          <input
            type="number"
            placeholder={labels.transactions.fee}
            className="input-fintech"
            value={form.fee}
            onChange={(e) => setForm({ ...form, fee: e.target.value })}
          />
          <input
            type="date"
            className="input-fintech"
            value={form.date}
            onChange={(e) => setForm({ ...form, date: e.target.value })}
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
                <th className="text-left">{labels.transactions.dateCol}</th>
                <th className="text-left">{labels.transactions.assetCol}</th>
                <th className="text-left">{labels.transactions.typeCol}</th>
                <th className="text-right">{labels.transactions.quantityCol}</th>
                <th className="text-right">{labels.transactions.priceCol}</th>
                <th className="text-right">{labels.transactions.feeCol}</th>
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
                  <td colSpan={7} className="px-4 py-8 text-center text-slate-500">
                    {labels.transactions.noTransactions}
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
