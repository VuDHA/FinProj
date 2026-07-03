import API from "./client";

export interface CompareSymbol {
  symbol: string;
  name: string;
  exchange: string;
  type: string;
  fund_type?: string | null;
}

export interface CompareMetrics {
  symbol: string;
  total_return?: number | null;
  annualized_return?: number | null;
  volatility?: number | null;
  max_drawdown_percent?: number | null;
  sharpe_ratio?: number | null;
}

export interface CompareCorrelation {
  labels: string[];
  matrix: number[][];
}

export interface CompareQuote {
  symbol: string;
  price: number;
  change: number;
  change_percent: number;
  date: string;
  error?: string | null;
}

export async function getSymbols(): Promise<CompareSymbol[]> {
  const [stocks, funds] = await Promise.all([
    API.get("/prices/stocks"),
    API.get("/prices/funds"),
  ]);
  return [...(stocks.data || []), ...(funds.data || [])];
}

export async function getCompareQuotes(symbols: string[], types: string[]): Promise<CompareQuote[]> {
  if (symbols.length === 0) return [];
  const { data } = await API.get("/prices/quote", {
    params: { symbols: symbols.join(","), types: types.join(",") },
  });
  return data;
}

export async function getHistory(
  symbol: string,
  type: string,
  start: string,
  end: string
): Promise<Array<{ date: string; price: number }>> {
  const { data } = await API.get(`/prices/market-history/${symbol}`, {
    params: { type, start, end },
  });
  return data;
}

export async function getMetrics(
  symbols: string[],
  types: string[],
  start: string,
  end: string
): Promise<CompareMetrics[]> {
  const { data } = await API.get("/compare/metrics", {
    params: {
      symbols: symbols.join(","),
      types: types.join(","),
      start,
      end,
    },
  });
  return data;
}

export async function getCorrelation(
  symbols: string[],
  types: string[],
  start: string,
  end: string
): Promise<CompareCorrelation> {
  const { data } = await API.get("/compare/correlation", {
    params: {
      symbols: symbols.join(","),
      types: types.join(","),
      start,
      end,
    },
  });
  return data;
}
