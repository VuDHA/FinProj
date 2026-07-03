import API from "./client";

export interface MarketQuote {
  symbol: string;
  price: number;
  change: number;
  change_percent: number;
  date: string;
  error?: string;
}

export interface PriceHistoryPoint {
  date: string;
  price: number;
}

export interface MarketSymbol {
  symbol: string;
  name: string;
  exchange: string;
  type: string;
  fund_type?: string;
}

export interface FundDetail {
  symbol: string;
  name: string;
  fund_type: string;
  owner: string;
  management_fee: number;
  inception_date: string;
  nav: number;
  nav_update_at: string;
  vsd_fee_id: string;
}

export interface GoldRate {
  source: string;
  buy: number;
  sell: number;
  updated_at: string;
}

export interface FxRate {
  currency: string;
  buy: number;
  transfer: number;
  sell: number;
}

export interface GoldFxResponse {
  gold: GoldRate[];
  fx: FxRate[];
}

export interface BenchmarkPoint {
  date: string;
  portfolio_value: number;
  benchmark_value: number;
}

export interface BenchmarkRawPoint {
  date: string;
  price: number;
}

export async function getMarketQuotes(
  symbols: string,
  assetType?: string,
  types?: string
): Promise<MarketQuote[]> {
  const { data } = await API.get("/prices/quote", {
    params: { symbols, asset_type: assetType, types },
  });
  return data;
}

export async function getPriceHistory(
  assetId: number,
  start: string,
  end: string
): Promise<PriceHistoryPoint[]> {
  const { data } = await API.get(`/prices/history/${assetId}`, {
    params: { start, end },
  });
  return data;
}

export async function getPricesForAsset(assetId: number): Promise<PriceHistoryPoint[]> {
  const { data } = await API.get(`/prices/${assetId}`);
  return data;
}

export async function getAllSymbols(): Promise<MarketSymbol[]> {
  const { data } = await API.get("/prices/symbols");
  return data;
}

export async function getAllStocks(): Promise<MarketSymbol[]> {
  const { data } = await API.get("/prices/stocks");
  return data;
}

export async function getAllFunds(): Promise<MarketSymbol[]> {
  const { data } = await API.get("/prices/funds");
  return data;
}

export async function getFundDetail(symbol: string): Promise<FundDetail> {
  const { data } = await API.get(`/prices/fund-detail/${symbol}`);
  return data;
}

export async function getMarketHistory(
  symbol: string,
  type: string,
  start: string,
  end: string
): Promise<PriceHistoryPoint[]> {
  const { data } = await API.get(`/prices/market-history/${symbol}`, {
    params: { type, start, end },
  });
  return data;
}

export async function getBenchmark(
  symbol: string,
  start: string,
  end: string
): Promise<BenchmarkPoint[]> {
  const { data } = await API.get(`/prices/benchmark/${symbol}`, {
    params: { start, end },
  });
  return data;
}

export async function getBenchmarkRaw(
  symbol: string,
  start: string,
  end: string
): Promise<BenchmarkRawPoint[]> {
  const { data } = await API.get(`/prices/benchmark-raw/${symbol}`, {
    params: { start, end },
  });
  return data;
}

export async function refreshAllPrices(): Promise<{
  updated: number;
  failed: number;
  warnings: string[];
  date: string;
  skipped: number;
}> {
  const { data } = await API.post("/prices/refresh-all");
  return data;
}

export async function refreshPrice(assetId: number): Promise<{
  snapshot: PriceHistoryPoint;
  warnings: string[];
}> {
  const { data } = await API.post(`/prices/refresh/${assetId}`);
  return data;
}

export async function getGoldFx(): Promise<GoldFxResponse> {
  const { data } = await API.get("/gold-fx/");
  return data;
}
