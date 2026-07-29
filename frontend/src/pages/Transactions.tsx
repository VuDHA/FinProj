import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type ColumnDef,
  type SortingState,
} from "@tanstack/react-table";
import { useVirtualizer } from "@tanstack/react-virtual";
import { zodResolver } from "@hookform/resolvers/zod";
import { Controller, useForm, type Resolver } from "react-hook-form";
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
import { formatCurrency } from "../lib/utils";
import {
  incomeFormSchema,
  transactionEditSchema,
  transactionFormSchema,
  type IncomeFormInput,
  type TransactionEditInput,
  type TransactionFormInput,
} from "../schemas/transactionSchema";

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

interface TransactionRow {
  id: number;
  asset_id: number;
  type: string;
  quantity: number;
  price: number | null;
  fee: number;
  date: string;
  notes: string | null;
}

interface IncomeRow {
  id: number;
  asset_id: number;
  type: string;
  amount: number;
  date: string;
  notes: string | null;
}

interface AssetRow {
  id: number;
  symbol: string;
  name: string;
  type: string;
}

/* ------------------------------------------------------------------ */
/* Component                                                           */
/* ------------------------------------------------------------------ */

export function Transactions() {
  const qc = useQueryClient();
  const { showToast } = useToast();
  const location = useLocation();

  /* ----------------------------- tab state ----------------------------- */
  const [tab, setTab] = usePersistentState<"transactions" | "income">("transactions.tab", "transactions");

  /* ---------------------- create-transaction form --------------------- */
  const [persistedForm, setPersistedForm] = usePersistentState<TransactionFormInput>("transactions.form", {
    asset_id: "",
    type: "BUY",
    quantity: "",
    price: "",
    price_mode: "manual",
    fee: "0",
    date: new Date().toISOString().split("T")[0],
    notes: "",
  });

  const createForm = useForm<TransactionFormInput>({
    resolver: zodResolver(transactionFormSchema) as unknown as Resolver<TransactionFormInput>,
    mode: "onTouched",
    defaultValues: persistedForm,
  });

  // Persist form changes to localStorage.
  useEffect(() => {
    const sub = createForm.watch((value) => {
      setPersistedForm(value as TransactionFormInput);
    });
    return () => sub.unsubscribe();
  }, [createForm, setPersistedForm]);

  /* ----------------------------- income form --------------------------- */
  const [persistedIncomeForm, setPersistedIncomeForm] = usePersistentState<IncomeFormInput>("transactions.incomeForm", {
    asset_id: "",
    type: "DIVIDEND",
    amount: "",
    date: new Date().toISOString().split("T")[0],
    notes: "",
  });

  const incomeForm = useForm<IncomeFormInput>({
    resolver: zodResolver(incomeFormSchema) as unknown as Resolver<IncomeFormInput>,
    mode: "onTouched",
    defaultValues: persistedIncomeForm,
  });

  useEffect(() => {
    const sub = incomeForm.watch((value) => {
      setPersistedIncomeForm(value as IncomeFormInput);
    });
    return () => sub.unsubscribe();
  }, [incomeForm, setPersistedIncomeForm]);

  /* ----------------------------- edit form ----------------------------- */
  const [editTarget, setEditTarget] = useState<TransactionRow | null>(null);
  const editForm = useForm<TransactionEditInput>({
    resolver: zodResolver(transactionEditSchema) as unknown as Resolver<TransactionEditInput>,
    mode: "onTouched",
    defaultValues: {
      quantity: "",
      price: "",
      price_mode: "manual",
      fee: "",
      date: "",
      notes: "",
    },
  });

  /* --------------------------- misc UI state --------------------------- */
  const [deleteTarget, setDeleteTarget] = useState<{ id: number; label: string; type: "transaction" | "income" } | null>(null);
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
  const [transactionSorting, setTransactionSorting] = usePersistentState<SortingState>("transactions.sorting", [{ id: "date", desc: true }]);
  const [incomeSorting, setIncomeSorting] = usePersistentState<SortingState>("transactions.incomeSorting", [{ id: "date", desc: true }]);

  /* ------------------------------ queries ------------------------------ */
  const transactions = useQuery({
    queryKey: ["transactions"],
    queryFn: async () => (await API.get("/transactions/")).data as TransactionRow[],
  });

  const income = useQuery({
    queryKey: ["income"],
    queryFn: async () => (await API.get("/income/")).data as IncomeRow[],
  });

  const assets = useQuery({
    queryKey: ["assets"],
    queryFn: async () => (await API.get("/assets/")).data as AssetRow[],
  });

  const assetTypes = useQuery<{ [key: string]: { marketPrice: boolean } }>({
    queryKey: ["asset-types"],
    queryFn: async () => (await API.get("/settings/asset-types")).data.types,
  });

  /* --------------------------- derived values -------------------------- */
  const formAssetId = createForm.watch("asset_id");
  const formType = createForm.watch("type");
  const formPriceMode = createForm.watch("price_mode");

  const selectedAsset = useMemo(() => {
    return (assets.data || []).find((a) => String(a.id) === formAssetId);
  }, [assets.data, formAssetId]);

  const isNonMarketAsset = useCallback(
    (type: string) => type && assetTypes.data?.[type]?.marketPrice === false,
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

  // Reset type to BUY when switching to a market-tracked asset while a
  // deposit/withdrawal type is selected.
  useEffect(() => {
    if (selectedAsset && !isNonMarketAsset(selectedAsset.type) && ["DEPOSIT", "WITHDRAWAL"].includes(formType)) {
      createForm.setValue("type", "BUY");
    }
  }, [selectedAsset, formType, isNonMarketAsset, createForm]);

  // Pre-fill asset from router navigation state (e.g. coming from Assets page).
  useEffect(() => {
    const state = location.state as { asset_id?: number } | null;
    if (state?.asset_id && String(state.asset_id) !== formAssetId) {
      const asset = (assets.data || []).find((a) => a.id === state.asset_id);
      createForm.setValue("asset_id", String(state.asset_id));
      createForm.setValue("price_mode", defaultPriceMode(asset?.type || ""));
      createForm.setValue("price", "");
      window.history.replaceState({}, document.title);
    }
  }, [location.state, assets.data, formAssetId, createForm]);

  const marketPricePreview = useQuery({
    queryKey: ["price-preview", formAssetId],
    queryFn: async () => {
      const res = await API.get(`/prices/${formAssetId}`);
      const snapshots = res.data as Array<{ price: number; date: string }>;
      return snapshots?.[0]?.price || null;
    },
    enabled: !!formAssetId,
    staleTime: 60 * 1000,
  });

  useEffect(() => {
    if (formPriceMode === "market" && marketPricePreview.data) {
      createForm.setValue("price", String(marketPricePreview.data));
    }
  }, [formPriceMode, marketPricePreview.data, createForm]);

  const editPriceMode = editForm.watch("price_mode");

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
    if (editTarget && editPriceMode === "market" && editMarketPricePreview.data) {
      editForm.setValue("price", String(editMarketPricePreview.data));
    }
  }, [editTarget, editPriceMode, editMarketPricePreview.data, editForm]);

  /* ----------------------------- mutations ----------------------------- */
  const create = useMutation({
    mutationFn: () => {
      const v = createForm.getValues();
      return API.post("/transactions/", {
        asset_id: Number(v.asset_id),
        type: v.type,
        quantity: Number(v.quantity),
        price: v.price_mode === "manual" ? Number(v.price) || null : null,
        fee: Number(v.fee),
        date: v.date,
        notes: v.notes,
      });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["transactions"] });
      qc.invalidateQueries({ queryKey: ["portfolio"] });
      qc.invalidateQueries({ queryKey: ["analytics"] });
      qc.invalidateQueries({ queryKey: ["analytics-risk"] });
      qc.invalidateQueries({ queryKey: ["portfolio-history"] });
      const resetValues: TransactionFormInput = {
        asset_id: "",
        type: "BUY",
        quantity: "",
        price: "",
        price_mode: "manual",
        fee: "0",
        date: new Date().toISOString().split("T")[0],
        notes: "",
      };
      createForm.reset(resetValues);
      setPersistedForm(resetValues);
      showToast("Đã thêm giao dịch thành công", "success");
    },
    onError: (error: any) => {
      showToast(error?.response?.data?.detail || "Không thể thêm giao dịch", "error");
    },
  });

  const createIncome = useMutation({
    mutationFn: () => {
      const v = incomeForm.getValues();
      return API.post("/income/", {
        asset_id: Number(v.asset_id),
        type: v.type,
        amount: Number(v.amount),
        date: v.date,
        notes: v.notes,
      });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["income"] });
      qc.invalidateQueries({ queryKey: ["analytics"] });
      const resetValues: IncomeFormInput = {
        asset_id: "",
        type: "DIVIDEND",
        amount: "",
        date: new Date().toISOString().split("T")[0],
        notes: "",
      };
      incomeForm.reset(resetValues);
      setPersistedIncomeForm(resetValues);
      showToast("Đã thêm thu nhập thành công", "success");
    },
    onError: (error: any) => {
      showToast(error?.response?.data?.detail || "Không thể thêm thu nhập", "error");
    },
  });

  const update = useMutation({
    mutationFn: (id: number) => {
      const v = editForm.getValues();
      return API.put(`/transactions/${id}`, {
        quantity: Number(v.quantity),
        price: Number(v.price) || null,
        fee: Number(v.fee),
        date: v.date,
        notes: v.notes,
      });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["transactions"] });
      qc.invalidateQueries({ queryKey: ["portfolio"] });
      qc.invalidateQueries({ queryKey: ["analytics"] });
      qc.invalidateQueries({ queryKey: ["analytics-risk"] });
      qc.invalidateQueries({ queryKey: ["portfolio-history"] });
      setEditTarget(null);
      editForm.reset();
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
      setDeleteTarget(null);
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
      setDeleteTarget(null);
    },
  });

  /* --------------------------- submit handlers ------------------------- */
  const handleSubmitTransaction = createForm.handleSubmit(() => create.mutate());
  const handleSubmitIncome = incomeForm.handleSubmit(() => createIncome.mutate());
  const handleSubmitEdit = editForm.handleSubmit(() => {
    if (editTarget) update.mutate(editTarget.id);
  });

  /* ------------------------------ helpers ------------------------------ */
  const assetById = useCallback(
    (id: number) => (assets.data || []).find((a) => a.id === id),
    [assets.data]
  );

  const filteredAssets = useMemo(() => {
    const q = assetSearch.trim().toLowerCase();
    return (assets.data || []).filter((asset) =>
      !q ||
      asset.symbol?.toLowerCase().includes(q) ||
      asset.name?.toLowerCase().includes(q) ||
      asset.type?.toLowerCase().includes(q)
    );
  }, [assets.data, assetSearch]);

  const selectedAssetLabel = selectedAsset
    ? `${selectedAsset.symbol} — ${selectedAsset.name}`
    : labels.transactions.selectAsset;

  const openEditTransaction = (tx: TransactionRow) => {
    const asset = (assets.data || []).find((a) => a.id === tx.asset_id);
    const mode = defaultPriceMode(asset?.type || "");
    setEditTarget(tx);
    editForm.reset({
      quantity: String(tx.quantity),
      price: String(tx.price || ""),
      price_mode: mode,
      fee: String(tx.fee),
      date: tx.date,
      notes: tx.notes || "",
    });
  };

  /* ----------------------- TanStack Table: tx list --------------------- */
  const filteredTransactions = useMemo(() => {
    return (transactions.data || []).filter((tx) => {
      if (!transactionSearch.trim()) return true;
      const q = transactionSearch.toLowerCase();
      const asset = assetById(tx.asset_id);
      return (
        asset?.symbol?.toLowerCase().includes(q) ||
        asset?.name?.toLowerCase().includes(q) ||
        tx.date?.includes(q) ||
        tx.type?.toLowerCase().includes(q)
      );
    });
  }, [transactions.data, transactionSearch, assetById]);

  const transactionColumns = useMemo<ColumnDef<TransactionRow>[]>(
    () => [
      {
        id: "date",
        accessorKey: "date",
        header: () => (
          <span className="inline-flex items-center gap-1">
            {labels.transactions.dateCol}
            <InfoTooltip content={labels.tooltips.backtestStartDate} />
          </span>
        ),
        cell: (info) => <span className="font-mono text-slate-500">{info.getValue() as string}</span>,
      },
      {
        id: "asset",
        accessorFn: (row) => {
          const asset = assetById(row.asset_id);
          return asset ? asset.symbol : String(row.asset_id);
        },
        header: () => (
          <span className="inline-flex items-center gap-1">
            {labels.transactions.assetCol}
            <InfoTooltip content={labels.tooltips.assetName} />
          </span>
        ),
        cell: ({ row }) => {
          const asset = assetById(row.original.asset_id);
          return (
            <div>
              <div className="font-display font-semibold text-slate-900 whitespace-nowrap">
                {asset ? asset.symbol : row.original.asset_id}
              </div>
              <span className="text-xs text-slate-500 max-w-[120px] truncate block">
                {asset ? asset.name : "-"}
              </span>
            </div>
          );
        },
      },
      {
        id: "type",
        accessorKey: "type",
        header: () => (
          <span className="inline-flex items-center gap-1">
            {labels.transactions.typeCol}
            <InfoTooltip content={labels.tooltips.transactionType} />
          </span>
        ),
        cell: (info) => (
          <span className={transactionTypeBadgeClass(info.getValue() as string)}>
            {transactionTypeLabel(info.getValue() as string)}
          </span>
        ),
      },
      {
        id: "quantity",
        accessorKey: "quantity",
        header: () => (
          <span className="inline-flex items-center gap-1">
            {labels.transactions.quantityCol}
            <InfoTooltip content={labels.tooltips.transactionQuantity} />
          </span>
        ),
        cell: (info) => (
          <span className="value-cell" title={String(info.getValue())}>
            {info.getValue() as number}
          </span>
        ),
      },
      {
        id: "price",
        accessorKey: "price",
        header: () => (
          <span className="inline-flex items-center gap-1">
            {labels.transactions.priceCol}
            <InfoTooltip content={labels.tooltips.transactionPrice} />
          </span>
        ),
        cell: (info) => (
          <span className="value-cell" title={formatCurrency(info.getValue() as number)}>
            {formatCurrency(info.getValue() as number)}
          </span>
        ),
      },
      {
        id: "fee",
        accessorKey: "fee",
        header: () => (
          <span className="inline-flex items-center gap-1">
            {labels.transactions.feeCol}
            <InfoTooltip content={labels.tooltips.transactionFee} />
          </span>
        ),
        cell: (info) => (
          <span className="value-cell" title={formatCurrency(info.getValue() as number)}>
            {formatCurrency(info.getValue() as number)}
          </span>
        ),
      },
      {
        id: "actions",
        header: () => <span>{labels.transactions.actionsCol}</span>,
        cell: ({ row }) => {
          const tx = row.original;
          const asset = assetById(tx.asset_id);
          return (
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
                onClick={() =>
                  setDeleteTarget({
                    id: tx.id,
                    label: asset ? `${asset.symbol} — ${tx.date}` : String(tx.id),
                    type: "transaction",
                  })
                }
                disabled={remove.isPending}
                className="inline-flex items-center justify-center p-2 rounded-lg text-accent-rose hover:bg-accent-rose/10 transition-colors disabled:opacity-50"
                aria-label="Xóa giao dịch"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          );
        },
      },
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [assets.data, update.isPending, remove.isPending, assetById]
  );

  const transactionTable = useReactTable({
    data: filteredTransactions,
    columns: transactionColumns,
    state: { sorting: transactionSorting },
    onSortingChange: setTransactionSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  // Virtualize the transaction table body for large lists.
  const txTableBodyRef = useRef<HTMLDivElement>(null);
  const { rows: txRows } = transactionTable.getRowModel();
  const txVirtualizer = useVirtualizer({
    count: txRows.length,
    getScrollElement: () => txTableBodyRef.current,
    estimateSize: () => 48,
    overscan: 10,
  });

  /* ---------------------- TanStack Table: income list ------------------ */
  const filteredIncome = useMemo(() => {
    return (income.data || []).filter((inc) => {
      if (!incomeSearch.trim()) return true;
      const q = incomeSearch.toLowerCase();
      const asset = assetById(inc.asset_id);
      return (
        asset?.symbol?.toLowerCase().includes(q) ||
        asset?.name?.toLowerCase().includes(q) ||
        inc.date?.includes(q) ||
        inc.type?.toLowerCase().includes(q)
      );
    });
  }, [income.data, incomeSearch, assetById]);

  const incomeColumns = useMemo<ColumnDef<IncomeRow>[]>(
    () => [
      {
        id: "date",
        accessorKey: "date",
        header: () => (
          <span className="inline-flex items-center gap-1">
            {labels.transactions.dateCol}
            <InfoTooltip content={labels.tooltips.backtestStartDate} />
          </span>
        ),
        cell: (info) => <span className="font-mono text-slate-500">{info.getValue() as string}</span>,
      },
      {
        id: "asset",
        accessorFn: (row) => {
          const asset = assetById(row.asset_id);
          return asset ? asset.symbol : String(row.asset_id);
        },
        header: () => (
          <span className="inline-flex items-center gap-1">
            {labels.transactions.assetCol}
            <InfoTooltip content={labels.tooltips.assetName} />
          </span>
        ),
        cell: ({ row }) => {
          const asset = assetById(row.original.asset_id);
          return (
            <div>
              <div className="font-display font-semibold text-slate-900 whitespace-nowrap">
                {asset ? asset.symbol : row.original.asset_id}
              </div>
              <span className="text-xs text-slate-500 max-w-[120px] truncate block">
                {asset ? asset.name : "-"}
              </span>
            </div>
          );
        },
      },
      {
        id: "type",
        accessorKey: "type",
        header: () => (
          <span className="inline-flex items-center gap-1">
            {labels.transactions.incomeType}
            <InfoTooltip content={labels.tooltips.incomeType} />
          </span>
        ),
        cell: (info) => (
          <span className="badge-gain">
            {info.getValue() === "DIVIDEND" ? labels.transactions.dividend : labels.transactions.interest}
          </span>
        ),
      },
      {
        id: "amount",
        accessorKey: "amount",
        header: () => (
          <span className="inline-flex items-center gap-1">
            {labels.transactions.amount}
            <InfoTooltip content={labels.tooltips.transactionPrice} />
          </span>
        ),
        cell: (info) => (
          <span className="value-cell" title={formatCurrency(info.getValue() as number)}>
            {formatCurrency(info.getValue() as number)}
          </span>
        ),
      },
      {
        id: "actions",
        header: () => <span>{labels.transactions.actionsCol}</span>,
        cell: ({ row }) => {
          const inc = row.original;
          const asset = assetById(inc.asset_id);
          return (
            <button
              onClick={() =>
                setDeleteTarget({
                  id: inc.id,
                  label: asset ? `${asset.symbol} — ${inc.date}` : String(inc.id),
                  type: "income",
                })
              }
              disabled={removeIncome.isPending}
              className="inline-flex items-center justify-center p-2 rounded-lg text-accent-rose hover:bg-accent-rose/10 transition-colors disabled:opacity-50"
              aria-label="Xóa thu nhập"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          );
        },
      },
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [assets.data, removeIncome.isPending, assetById]
  );

  const incomeTable = useReactTable({
    data: filteredIncome,
    columns: incomeColumns,
    state: { sorting: incomeSorting },
    onSortingChange: setIncomeSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  const incomeTableBodyRef = useRef<HTMLDivElement>(null);
  const { rows: incomeRows } = incomeTable.getRowModel();
  const incomeVirtualizer = useVirtualizer({
    count: incomeRows.length,
    getScrollElement: () => incomeTableBodyRef.current,
    estimateSize: () => 48,
    overscan: 10,
  });

  /* ------------------------------- render ------------------------------ */
  const createErrors = createForm.formState.errors;
  const incomeErrors = incomeForm.formState.errors;
  const editErrors = editForm.formState.errors;

  return (
    <div className="space-y-6">
      {transactions.isError && <ErrorMessage error={transactions.error} retry={() => transactions.refetch()} />}
      {income.isError && <ErrorMessage error={income.error} retry={() => income.refetch()} />}
      {assets.isError && <ErrorMessage error={assets.error} retry={() => assets.refetch()} />}
      {create.isError && <ErrorMessage error={create.error} retry={() => create.mutate()} />}
      {createIncome.isError && <ErrorMessage error={createIncome.error} retry={() => createIncome.mutate()} />}
      {update.isError && <ErrorMessage error={update.error} retry={() => update.reset()} />}
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
              <div className="relative md:col-span-2">
                <div ref={assetRef} className="relative z-50">
                  <input
                    type="text"
                    placeholder={labels.assets.searchAssets}
                    className={`input-fintech pr-10 ${createErrors.asset_id ? "border-rose-400 focus:border-rose-400 focus:ring-rose-200" : ""}`}
                    value={assetSearchOpen ? assetSearch : selectedAssetLabel}
                    onChange={(e) => {
                      setAssetSearch(e.target.value);
                      setAssetSearchOpen(true);
                    }}
                    onFocus={() => setAssetSearchOpen(true)}
                    aria-invalid={!!createErrors.asset_id}
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
                      {filteredAssets.map((asset) => (
                        <button
                          key={asset.id}
                          type="button"
                          className="w-full text-left px-3 py-2 text-sm hover:bg-slate-50 focus:bg-slate-50"
                          onClick={() => {
                            createForm.setValue("asset_id", String(asset.id));
                            createForm.setValue("price_mode", defaultPriceMode(asset.type));
                            createForm.clearErrors("asset_id");
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
                {createErrors.asset_id && <p className="text-xs text-rose-500 mt-1">{createErrors.asset_id.message}</p>}
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
                  {...createForm.register("type")}
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
                  className={`input-fintech pr-10 ${createErrors.quantity ? "border-rose-400 focus:border-rose-400 focus:ring-rose-200" : ""}`}
                  aria-invalid={!!createErrors.quantity}
                  {...createForm.register("quantity")}
                />
                <span className="absolute right-3 top-1/2 -translate-y-1/2">
                  <InfoTooltip content={labels.tooltips.transactionQuantity} position="top" />
                </span>
                {createErrors.quantity && <p className="text-xs text-rose-500 mt-1">{createErrors.quantity.message}</p>}
              </div>
              <div className="relative md:col-span-2">
                <div className="flex rounded-lg border border-slate-200 bg-slate-50 p-1 gap-1">
                  <button
                    type="button"
                    onClick={() => createForm.setValue("price_mode", "market")}
                    className={`flex-1 px-2 py-1.5 text-xs font-medium rounded-md transition-colors ${formPriceMode === "market"
                      ? "bg-white text-accent-blue shadow-sm"
                      : "text-slate-500 hover:text-slate-700"
                      }`}
                  >
                    {labels.transactions.marketPrice}
                  </button>
                  <button
                    type="button"
                    onClick={() => createForm.setValue("price_mode", "manual")}
                    className={`flex-1 px-2 py-1.5 text-xs font-medium rounded-md transition-colors ${formPriceMode === "manual"
                      ? "bg-white text-accent-blue shadow-sm"
                      : "text-slate-500 hover:text-slate-700"
                      }`}
                  >
                    {labels.transactions.manualPrice}
                  </button>
                </div>
                <div className="relative mt-1">
                  <Controller
                    control={createForm.control}
                    name="price"
                    render={({ field }) => (
                      <FormattedNumberInput
                        mode="currency"
                        decimals={2}
                        className={`input-fintech pr-10 ${createErrors.price ? "border-rose-400 focus:border-rose-400 focus:ring-rose-200" : ""}`}
                        value={field.value ?? ""}
                        disabled={formPriceMode === "market"}
                        onChange={(value) => field.onChange(value)}
                        aria-invalid={!!createErrors.price}
                      />
                    )}
                  />
                  <span className="absolute right-3 top-1/2 -translate-y-1/2">
                    <InfoTooltip content={formPriceMode === "market" ? labels.transactions.pricePreview : labels.tooltips.transactionPrice} position="right" />
                  </span>
                  {formPriceMode === "market" && marketPricePreview.isLoading && (
                    <span className="absolute right-10 top-1/2 -translate-y-1/2 text-xs text-slate-400">{labels.common.loading}</span>
                  )}
                  {createErrors.price && <p className="text-xs text-rose-500 mt-1">{createErrors.price.message}</p>}
                </div>
              </div>
              <div className="relative">
                <Controller
                  control={createForm.control}
                  name="fee"
                  render={({ field }) => (
                    <FormattedNumberInput
                      mode="currency"
                      decimals={2}
                      placeholder={labels.transactions.fee}
                      className={`input-fintech pr-10 ${createErrors.fee ? "border-rose-400 focus:border-rose-400 focus:ring-rose-200" : ""}`}
                      value={field.value ?? ""}
                      onChange={(value) => field.onChange(value)}
                      aria-invalid={!!createErrors.fee}
                    />
                  )}
                />
                <span className="absolute right-3 top-1/2 -translate-y-1/2">
                  <InfoTooltip content={labels.tooltips.transactionFee} position="right" />
                </span>
                {createErrors.fee && <p className="text-xs text-rose-500 mt-1">{createErrors.fee.message}</p>}
              </div>
              <div className="relative">
                <input
                  type="date"
                  className={`input-fintech pr-10 ${createErrors.date ? "border-rose-400 focus:border-rose-400 focus:ring-rose-200" : ""}`}
                  aria-invalid={!!createErrors.date}
                  {...createForm.register("date")}
                />
                <span className="absolute right-3 top-1/2 -translate-y-1/2">
                  <InfoTooltip content={labels.tooltips.backtestStartDate} position="right" />
                </span>
                {createErrors.date && <p className="text-xs text-rose-500 mt-1">{createErrors.date.message}</p>}
              </div>
              <input
                type="text"
                placeholder={labels.transactions.notes}
                className="input-fintech md:col-span-4"
                {...createForm.register("notes")}
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
                  onClick={() =>
                    setTransactionSorting((prev) => [{ id: "date", desc: !(prev[0]?.desc ?? true) }])
                  }
                  className="btn-secondary px-2"
                  title={transactionSorting[0]?.desc ? "Sắp xếp cũ nhất trước" : "Sắp xếp mới nhất trước"}
                  aria-label={transactionSorting[0]?.desc ? "Sắp xếp cũ nhất trước" : "Sắp xếp mới nhất trước"}
                >
                  <ArrowDownUp className="w-4 h-4" />
                </button>
              </div>
            </div>
            {transactions.isLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-8" count={6} />
              </div>
            ) : filteredTransactions.length === 0 ? (
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
            ) : (
              <div
                ref={txTableBodyRef}
                className="overflow-auto scrollbar-thin"
                style={{ maxHeight: 480 }}
              >
                <table className="table-fintech" style={{ display: "block" }}>
                  <thead style={{ display: "block", position: "sticky", top: 0, zIndex: 1, background: "white" }}>
                    {transactionTable.getHeaderGroups().map((headerGroup) => (
                      <tr key={headerGroup.id} style={{ display: "flex", width: "100%" }}>
                        {headerGroup.headers.map((header) => {
                          const canSort = header.column.getCanSort();
                          const sorted = header.column.getIsSorted();
                          return (
                            <th
                              key={header.id}
                              className={
                                header.column.id === "actions"
                                  ? "text-right"
                                  : ["quantity", "price", "fee"].includes(header.column.id)
                                    ? "text-right"
                                    : "text-left"
                              }
                              style={{ flex: header.column.id === "asset" ? 2 : 1, cursor: canSort ? "pointer" : "default" }}
                              onClick={canSort ? header.column.getToggleSortingHandler() : undefined}
                            >
                              <span className="inline-flex items-center gap-1 select-none">
                                {flexRender(header.column.columnDef.header, header.getContext())}
                                {canSort && (
                                  <span className="text-slate-400 text-xs">
                                    {sorted === "asc" ? " ▲" : sorted === "desc" ? " ▼" : " ↕"}
                                  </span>
                                )}
                              </span>
                            </th>
                          );
                        })}
                      </tr>
                    ))}
                  </thead>
                  <tbody
                    style={{
                      display: "block",
                      height: `${txVirtualizer.getTotalSize()}px`,
                      position: "relative",
                    }}
                  >
                    {txVirtualizer.getVirtualItems().map((virtualRow) => {
                      const row = txRows[virtualRow.index];
                      return (
                        <tr
                          key={row.id}
                          style={{
                            display: "flex",
                            width: "100%",
                            position: "absolute",
                            transform: `translateY(${virtualRow.start}px)`,
                          }}
                        >
                          {row.getVisibleCells().map((cell) => (
                            <td
                              key={cell.id}
                              className={
                                cell.column.id === "actions"
                                  ? "text-right"
                                  : ["quantity", "price", "fee"].includes(cell.column.id)
                                    ? "value-cell"
                                    : ""
                              }
                              style={{ flex: cell.column.id === "asset" ? 2 : 1 }}
                            >
                              {flexRender(cell.column.columnDef.cell, cell.getContext())}
                            </td>
                          ))}
                        </tr>
                      );
                    })}
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
                    aria-invalid={!!incomeErrors.asset_id}
                    {...incomeForm.register("asset_id")}
                  >
                    <option value="">{labels.transactions.selectAsset}</option>
                    {assets.data?.map((asset) => (
                      <option key={asset.id} value={asset.id}>
                        {asset.symbol} — {asset.name}
                      </option>
                    ))}
                  </select>
                  <span className="absolute right-8 top-1/2 -translate-y-1/2">
                    <InfoTooltip content={labels.tooltips.assetType} position="right" />
                  </span>
                  {incomeErrors.asset_id && <p className="text-xs text-rose-500 mt-1">{incomeErrors.asset_id.message}</p>}
                </div>
                <div className="relative">
                  <select
                    className="input-fintech pr-10"
                    {...incomeForm.register("type")}
                  >
                    <option value="DIVIDEND">{labels.transactions.dividend}</option>
                    <option value="INTEREST">{labels.transactions.interest}</option>
                  </select>
                  <span className="absolute right-8 top-1/2 -translate-y-1/2">
                    <InfoTooltip content={labels.tooltips.incomeType} position="right" />
                  </span>
                </div>
                <div className="relative">
                  <Controller
                    control={incomeForm.control}
                    name="amount"
                    render={({ field }) => (
                      <FormattedNumberInput
                        mode="currency"
                        decimals={2}
                        placeholder={labels.transactions.amount}
                        className={`input-fintech pr-10 ${incomeErrors.amount ? "border-rose-400 focus:border-rose-400 focus:ring-rose-200" : ""}`}
                        value={field.value ?? ""}
                        onChange={(value) => field.onChange(value)}
                        aria-invalid={!!incomeErrors.amount}
                      />
                    )}
                  />
                  <span className="absolute right-3 top-1/2 -translate-y-1/2">
                    <InfoTooltip content={labels.tooltips.transactionPrice} position="right" />
                  </span>
                  {incomeErrors.amount && <p className="text-xs text-rose-500 mt-1">{incomeErrors.amount.message}</p>}
                </div>
                <div className="relative">
                  <input
                    type="date"
                    className={`input-fintech pr-10 ${incomeErrors.date ? "border-rose-400 focus:border-rose-400 focus:ring-rose-200" : ""}`}
                    aria-invalid={!!incomeErrors.date}
                    {...incomeForm.register("date")}
                  />
                  <span className="absolute right-3 top-1/2 -translate-y-1/2">
                    <InfoTooltip content={labels.tooltips.backtestStartDate} position="right" />
                  </span>
                  {incomeErrors.date && <p className="text-xs text-rose-500 mt-1">{incomeErrors.date.message}</p>}
                </div>
                <input
                  type="text"
                  placeholder={labels.transactions.notes}
                  className="input-fintech"
                  {...incomeForm.register("notes")}
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
                    onClick={() =>
                      setIncomeSorting((prev) => [{ id: "date", desc: !(prev[0]?.desc ?? true) }])
                    }
                    className="btn-secondary px-2"
                    title={incomeSorting[0]?.desc ? "Sắp xếp cũ nhất trước" : "Sắp xếp mới nhất trước"}
                    aria-label={incomeSorting[0]?.desc ? "Sắp xếp cũ nhất trước" : "Sắp xếp mới nhất trước"}
                  >
                    <ArrowDownUp className="w-4 h-4" />
                  </button>
                </div>
              </div>
              {income.isLoading ? (
                <div className="space-y-3">
                  <Skeleton className="h-8" count={4} />
                </div>
              ) : filteredIncome.length === 0 ? (
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
              ) : (
                <div
                  ref={incomeTableBodyRef}
                  className="overflow-auto scrollbar-thin"
                  style={{ maxHeight: 480 }}
                >
                  <table className="table-fintech" style={{ display: "block" }}>
                    <thead style={{ display: "block", position: "sticky", top: 0, zIndex: 1, background: "white" }}>
                      {incomeTable.getHeaderGroups().map((headerGroup) => (
                        <tr key={headerGroup.id} style={{ display: "flex", width: "100%" }}>
                          {headerGroup.headers.map((header) => {
                            const canSort = header.column.getCanSort();
                            const sorted = header.column.getIsSorted();
                            return (
                              <th
                                key={header.id}
                                className={
                                  header.column.id === "actions"
                                    ? "text-right"
                                    : header.column.id === "amount"
                                      ? "text-right"
                                      : "text-left"
                                }
                                style={{ flex: header.column.id === "asset" ? 2 : 1, cursor: canSort ? "pointer" : "default" }}
                                onClick={canSort ? header.column.getToggleSortingHandler() : undefined}
                              >
                                <span className="inline-flex items-center gap-1 select-none">
                                  {flexRender(header.column.columnDef.header, header.getContext())}
                                  {canSort && (
                                    <span className="text-slate-400 text-xs">
                                      {sorted === "asc" ? " ▲" : sorted === "desc" ? " ▼" : " ↕"}
                                    </span>
                                  )}
                                </span>
                              </th>
                            );
                          })}
                        </tr>
                      ))}
                    </thead>
                    <tbody
                      style={{
                        display: "block",
                        height: `${incomeVirtualizer.getTotalSize()}px`,
                        position: "relative",
                      }}
                    >
                      {incomeVirtualizer.getVirtualItems().map((virtualRow) => {
                        const row = incomeRows[virtualRow.index];
                        return (
                          <tr
                            key={row.id}
                            style={{
                              display: "flex",
                              width: "100%",
                              position: "absolute",
                              transform: `translateY(${virtualRow.start}px)`,
                            }}
                          >
                            {row.getVisibleCells().map((cell) => (
                              <td
                                key={cell.id}
                                className={
                                  cell.column.id === "actions"
                                    ? "text-right"
                                    : cell.column.id === "amount"
                                      ? "value-cell"
                                      : ""
                                }
                                style={{ flex: cell.column.id === "asset" ? 2 : 1 }}
                              >
                                {flexRender(cell.column.columnDef.cell, cell.getContext())}
                              </td>
                            ))}
                          </tr>
                        );
                      })}
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
                  const asset = (assets.data || []).find((a) => a.id === editTarget.asset_id);
                  return asset ? `${asset.symbol} — ${asset.name}` : editTarget.asset_id;
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
                  {...editForm.register("quantity")}
                />
                {editErrors.quantity && <p className="text-xs text-rose-500 mt-1">{editErrors.quantity.message}</p>}
              </div>
              <div className="relative md:col-span-2">
                <div className="flex rounded-lg border border-slate-200 bg-slate-50 p-1 gap-1 mb-1">
                  <button
                    type="button"
                    onClick={() => editForm.setValue("price_mode", "market")}
                    className={`flex-1 px-2 py-1.5 text-xs font-medium rounded-md transition-colors ${editPriceMode === "market" ? "bg-white text-accent-blue shadow-sm" : "text-slate-500"
                      }`}
                  >
                    {labels.transactions.marketPrice}
                  </button>
                  <button
                    type="button"
                    onClick={() => editForm.setValue("price_mode", "manual")}
                    className={`flex-1 px-2 py-1.5 text-xs font-medium rounded-md transition-colors ${editPriceMode === "manual" ? "bg-white text-accent-blue shadow-sm" : "text-slate-500"
                      }`}
                  >
                    {labels.transactions.manualPrice}
                  </button>
                </div>
                <Controller
                  control={editForm.control}
                  name="price"
                  render={({ field }) => (
                    <FormattedNumberInput
                      mode="currency"
                      decimals={2}
                      placeholder={labels.transactions.price}
                      className={`input-fintech pr-10 ${editErrors.price ? "border-rose-400 focus:border-rose-400 focus:ring-rose-200" : ""}`}
                      value={field.value ?? ""}
                      disabled={editPriceMode === "market"}
                      onChange={(value) => field.onChange(value)}
                    />
                  )}
                />
                {editPriceMode === "market" && editMarketPricePreview.isLoading && (
                  <span className="absolute right-10 top-1/2 -translate-y-1/2 text-xs text-slate-400">{labels.common.loading}</span>
                )}
                {editErrors.price && <p className="text-xs text-rose-500 mt-1">{editErrors.price.message}</p>}
              </div>
              <div className="relative">
                <Controller
                  control={editForm.control}
                  name="fee"
                  render={({ field }) => (
                    <FormattedNumberInput
                      mode="currency"
                      decimals={2}
                      placeholder={labels.transactions.fee}
                      className={`input-fintech pr-10 ${editErrors.fee ? "border-rose-400 focus:border-rose-400 focus:ring-rose-200" : ""}`}
                      value={field.value ?? ""}
                      onChange={(value) => field.onChange(value)}
                    />
                  )}
                />
                {editErrors.fee && <p className="text-xs text-rose-500 mt-1">{editErrors.fee.message}</p>}
              </div>
              <div className="relative">
                <input
                  type="date"
                  className={`input-fintech pr-10 ${editErrors.date ? "border-rose-400 focus:border-rose-400 focus:ring-rose-200" : ""}`}
                  {...editForm.register("date")}
                />
                {editErrors.date && <p className="text-xs text-rose-500 mt-1">{editErrors.date.message}</p>}
              </div>
              <input
                type="text"
                placeholder={labels.transactions.notes}
                className="input-fintech md:col-span-2"
                {...editForm.register("notes")}
              />
            </div>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => {
                  setEditTarget(null);
                  editForm.reset();
                }}
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
