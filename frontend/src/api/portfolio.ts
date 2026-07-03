import API from "./client";

export interface PortfolioSummary {
  total_value: number;
  total_cost: number;
  total_pnl: number;
  total_pnl_percent: number;
  items: PortfolioItem[];
}

export interface PortfolioItem {
  asset_id: number;
  symbol: string;
  name: string;
  type: string;
  quantity: number;
  avg_cost: number;
  latest_price: number;
  current_value: number;
  cost: number;
  pnl: number;
  pnl_percent: number;
}

export interface PortfolioHistoryPoint {
  date: string;
  value: number;
  cost: number;
  by_type?: Record<string, number>;
}

export async function getPortfolio(): Promise<PortfolioSummary> {
  const { data } = await API.get("/portfolio/");
  return data;
}

export async function getPortfolioHistory(
  start?: string,
  end?: string
): Promise<PortfolioHistoryPoint[]> {
  const { data } = await API.get("/portfolio/history", { params: { start, end } });
  return data;
}
