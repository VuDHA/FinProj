import API from "./client";

export interface BacktestPosition {
  symbol: string;
  price: number;
  quantity: number;
  ratio?: number;
}

export interface BacktestRequest {
  symbols?: string[];
  start_date: string;
  end_date: string;
  strategy: "buy_and_hold" | "rebalancing";
  rebalance_frequency: "monthly" | "quarterly";
  initial_cash: number;
  allocations?: Record<string, number>;
  positions?: BacktestPosition[];
}

export interface BacktestTrade {
  date: string;
  symbol: string;
  action: "BUY" | "SELL";
  quantity: number;
  price: number;
  value: number;
}

export interface BacktestResult {
  final_value: number;
  total_return: number;
  total_return_percent: number;
  max_drawdown_percent: number;
  equity_curve: { date: string; value: number }[];
  trades: BacktestTrade[];
  warnings: string[];
}

export interface BacktestPromptRequest {
  prompt: string;
}

export interface BacktestPromptResponse {
  request: BacktestRequest;
  result: BacktestResult;
  used_ollama: boolean;
}

export async function runBacktest(payload: BacktestRequest): Promise<BacktestResult> {
  const { data } = await API.post("/backtest/", payload);
  return data;
}

export async function runBacktestFromPrompt(
  prompt: string
): Promise<BacktestPromptResponse> {
  const { data } = await API.post("/backtest/ai", { prompt });
  return data;
}
