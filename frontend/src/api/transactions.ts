import API from "./client";

export interface Transaction {
  id: number;
  asset_id: number;
  type: "BUY" | "SELL";
  quantity: number;
  price: number;
  fee: number;
  date: string;
  notes?: string;
  asset?: { symbol: string; name: string };
}

export interface TransactionCreate {
  asset_id: number;
  type: "BUY" | "SELL";
  quantity: number;
  price?: number;
  fee: number;
  date: string;
  notes?: string;
}

export async function getTransactions(): Promise<Transaction[]> {
  const { data } = await API.get("/transactions/");
  return data;
}

export async function createTransaction(payload: TransactionCreate): Promise<Transaction> {
  const { data } = await API.post("/transactions/", payload);
  return data;
}

export async function deleteTransaction(id: number): Promise<void> {
  await API.delete(`/transactions/${id}`);
}

export interface Income {
  id: number;
  asset_id: number;
  type: "DIVIDEND" | "INTEREST";
  amount: number;
  date: string;
  notes?: string;
  asset?: { symbol: string; name: string };
}

export interface IncomeCreate {
  asset_id: number;
  type: "DIVIDEND" | "INTEREST";
  amount: number;
  date: string;
  notes?: string;
}

export async function getIncome(): Promise<Income[]> {
  const { data } = await API.get("/income/");
  return data;
}

export async function createIncome(payload: IncomeCreate): Promise<Income> {
  const { data } = await API.post("/income/", payload);
  return data;
}

export async function deleteIncome(id: number): Promise<void> {
  await API.delete(`/income/${id}`);
}
