import API from "./client";

export interface FundDetail {
  symbol: string;
  name: string;
  fund_type?: string;
  owner?: string;
  management_fee?: number;
  inception_date?: string;
  nav: number;
  nav_update_at?: string;
  vsd_fee_id?: string;
}

export interface StockDetail {
  symbol: string;
  name: string;
  exchange: string;
  type: string;
  sector?: string;
  industry?: string;
  market_cap?: number;
  price: number;
  change: number;
  change_percent: number;
  date: string;
  pe?: number;
  pb?: number;
  dividend_yield?: number;
}

export interface SymbolAIInsight {
  overall: string;
  details: string;
  suggestions: string[];
  used_ollama?: boolean;
  cooldown_seconds?: number;
}

export async function getFundDetail(symbol: string): Promise<FundDetail> {
  const { data } = await API.get(`/prices/fund-detail/${encodeURIComponent(symbol)}`);
  return data;
}

export async function getStockDetail(symbol: string): Promise<StockDetail> {
  const { data } = await API.get(`/prices/stock-detail/${encodeURIComponent(symbol)}`);
  return data;
}

export async function getSymbolAIInsight(
  symbol: string,
  type: string,
  start: string,
  end: string
): Promise<SymbolAIInsight> {
  const { data } = await API.get(`/prices/symbol-ai-insight/${encodeURIComponent(symbol)}`, {
    params: { type, start, end },
  });
  return data;
}
