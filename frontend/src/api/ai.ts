import API from "./client";

export interface AIInsightResponse {
  overall: string;
  details: string;
  suggestions: string[];
  used_ollama: boolean;
  cooldown_seconds: number;
}

export interface AiRateLimitProvider {
  max_rpm: number;
  max_concurrent: number;
  recent_requests: number;
  current_concurrent: number;
  available_rpm: number;
  available_concurrent: number;
}

export type AiRateLimitStatus = Record<string, AiRateLimitProvider>;

export interface CompareAIInsightPayload {
  symbols: string[];
  metrics: any[];
  correlation: {
    labels: string[];
    matrix: number[][];
  };
}

export interface BacktestStressPayload {
  prompt: string;
  base_request?: any;
}

export interface BacktestStressResponse {
  request: any;
  result: any;
  used_ollama: boolean;
}

export async function getAiRateLimit(): Promise<AiRateLimitStatus> {
  const { data } = await API.get("/ai/rate-limit");
  return data;
}

export async function getPortfolioInsight(): Promise<AIInsightResponse> {
  const { data } = await API.post("/portfolio/ai-insight");
  return data;
}

export async function getAnalyticsInsight(
  filterType: string,
  startDate?: string,
  endDate?: string
): Promise<AIInsightResponse> {
  const { data } = await API.post("/analytics/ai-insight", undefined, {
    params: {
      filter_type: filterType,
      start_date: startDate,
      end_date: endDate,
    },
  });
  return data;
}

export async function getMarketInsight(): Promise<AIInsightResponse> {
  const { data } = await API.post("/prices/market-ai-insight");
  return data;
}

export async function getRebalanceInsight(): Promise<AIInsightResponse> {
  const { data } = await API.post("/rebalance/ai-insight");
  return data;
}

export async function getCompareInsight(payload: CompareAIInsightPayload): Promise<AIInsightResponse> {
  const { data } = await API.post("/compare/ai-insight", payload);
  return data;
}

export async function getBacktestStress(payload: BacktestStressPayload): Promise<BacktestStressResponse> {
  const { data } = await API.post("/backtest/ai-stress", payload);
  return data;
}
