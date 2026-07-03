import API from "./client";

export interface AnalyticsSummary {
  top_performers: any[];
  bottom_performers: any[];
  type_returns: any[];
  monthly_pnl: any[];
  income: any[];
  total_income: number;
  total_value: number;
  total_cost: number;
  portfolio_value_by_type: any[];
  filter_type: string;
  period_start: string;
  period_end: string;
}

export interface RiskMetrics {
  volatility: number;
  sharpe_ratio: number;
  max_drawdown_percent: number;
  beta: number;
}

export async function getAnalytics(
  filterType: string = "month",
  startDate?: string,
  endDate?: string
): Promise<AnalyticsSummary> {
  const { data } = await API.get("/analytics/", {
    params: { filter_type: filterType, start_date: startDate, end_date: endDate },
  });
  return data;
}

export async function getRiskMetrics(): Promise<RiskMetrics> {
  const { data } = await API.get("/analytics/risk");
  return data;
}
