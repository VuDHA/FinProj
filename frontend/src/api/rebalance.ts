import API from "./client";

export interface RebalanceSuggestion {
  type: string;
  current_value: number;
  current_percent: number;
  target_percent: number;
  target_value: number;
  diff_value: number;
}

export interface RebalanceTrade {
  symbol: string;
  name: string;
  action: "BUY" | "SELL";
  quantity: number;
  estimated_price: number;
  estimated_value: number;
}

export interface RebalanceResult {
  total_value: number;
  suggestions: RebalanceSuggestion[];
  trades: RebalanceTrade[];
}

export async function getRebalance(): Promise<RebalanceResult> {
  const { data } = await API.get("/rebalance/");
  return data;
}
