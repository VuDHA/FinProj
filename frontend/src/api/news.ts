import API from "./client";
import { labels } from "../i18n/vi";

export interface Article {
  id: number;
  source_id: number;
  source_name: string | null;
  url: string;
  title: string;
  summary: string | null;
  author: string | null;
  category: string | null;
  tags: string | null;
  published_at: string | null;
  fetched_at: string;
  sentiment_score: number | null;
  impact_score: number | null;
  relevance_score: number | null;
  is_standout: boolean;
  language: string | null;
  region: string;
  symbols: string[];
  sentiment_label: string | null;
  impact_label: string | null;
}

export interface ArticleList {
  items: Article[];
  total: number;
  limit: number;
  offset: number;
}

export interface Alert {
  id: number;
  alert_type: string;
  symbol: string | null;
  article_id: number;
  title: string;
  message: string;
  is_read: boolean;
  created_at: string;
}

export interface WatchlistItem {
  id: number;
  symbol: string;
  name: string | null;
  notes: string | null;
  added_at: string;
}

export interface Trending {
  symbols: { symbol: string; mentions: number }[];
  sentiment: Record<string, number>;
}

export interface NewsSource {
  id: number;
  name: string;
  code: string;
  region: string;
}

export interface AiSummaryRequest {
  search?: string;
  symbol?: string;
  sentiment?: string;
  min_impact?: number;
  date_from?: string;
  date_to?: string;
  source_id?: number;
  tag?: string;
  region?: "vn" | "global";
  limit?: number;
}

export interface AiSummaryResponse {
  summary: string;
  article_count: number;
  used_ollama: boolean;
  personalized: boolean;
}

export interface ArticleSummarizeRequest {
  url: string;
  title?: string;
  language?: string;
}

export interface ArticleSummarizeTextRequest {
  content_text: string;
  title?: string;
  language?: string;
}

export interface ArticleSummarizeResponse {
  summary: string;
  tags: string[];
  source_url: string;
  title: string | null;
  used_ai: boolean;
  partial: boolean;
}

export interface AiStatus {
  busy: boolean;
  queue_length: number;
  current_task: string | null;
  gemini_configured?: boolean;
  ai_provider?: string;
}

export interface DailyBrief {
  generated_at: string;
  period_hours: number;
  total_articles: number;
  top_articles: Article[];
  key_symbols: { symbol: string; mentions: number }[];
}

export async function getNews(params?: Record<string, any>): Promise<ArticleList> {
  const { data } = await API.get("/news", { params });
  return data;
}

export async function getFeed(params?: Record<string, any>): Promise<ArticleList> {
  const { data } = await API.get("/news/feed", { params });
  return data;
}

export async function getTrending(hours = 24, region: "vn" | "global" = "vn"): Promise<Trending> {
  const { data } = await API.get("/news/trending/now", { params: { hours, region } });
  return data;
}

export async function getSources(): Promise<NewsSource[]> {
  const { data } = await API.get("/news/sources");
  return data;
}

export async function aiSummary(payload: AiSummaryRequest): Promise<AiSummaryResponse> {
  const { data } = await API.post("/news/ai-summary", payload);
  return data;
}

export async function summarizeArticle(payload: ArticleSummarizeRequest): Promise<ArticleSummarizeResponse> {
  const { data } = await API.post("/news/summarize", payload, { timeout: 90000 });
  return data;
}

export async function summarizeText(payload: ArticleSummarizeTextRequest): Promise<ArticleSummarizeResponse> {
  const { data } = await API.post("/news/summarize-text", payload, { timeout: 90000 });
  return data;
}

export async function getAiStatus(): Promise<AiStatus> {
  const { data } = await API.get("/ai/status");
  return data;
}

export async function getDailyBrief(hours = 24, scope?: "vn" | "global"): Promise<DailyBrief> {
  const { data } = await API.get("/news/brief/daily", { params: { hours, scope } });
  return data;
}

export async function getAlerts(unread_only = false): Promise<Alert[]> {
  const { data } = await API.get("/news/alerts/list", { params: { unread_only } });
  return data;
}

export async function markAlertRead(id: number): Promise<Alert> {
  const { data } = await API.post(`/news/alerts/${id}/read`);
  return data;
}

export async function getWatchlist(): Promise<WatchlistItem[]> {
  const { data } = await API.get("/news/watchlist/list");
  return data;
}

export async function addWatchlist(symbol: string, name?: string, notes?: string): Promise<WatchlistItem> {
  const { data } = await API.post("/news/watchlist", { symbol, name, notes });
  return data;
}

export async function removeWatchlist(symbol: string): Promise<void> {
  await API.delete(`/news/watchlist/${symbol}`);
}

export interface RefreshProgress {
  id: string;
  source_code: string | null;
  status: "running" | "completed" | "error" | "timeout";
  total_sources: number;
  current_source_index: number;
  current_source: string;
  processed: number;
  new_articles: number;
  errors: string[];
  results: Record<string, number>;
  alerts_generated: number;
  message: string;
}

export async function refreshNewsPoll(
  source?: string,
  region?: "vn" | "global",
  onProgress?: (progress: RefreshProgress) => void,
  signal?: AbortSignal
): Promise<RefreshProgress> {
  const params: Record<string, string> = {};
  if (source) params.source = source;
  if (region) params.region = region;
  const { data } = await API.post("/news/refresh", undefined, { params: Object.keys(params).length ? params : undefined });
  const jobId = data.job_id as string;

  // Poll the job status endpoint. WebView2 does not support streaming
  // fetch() response bodies, so we use simple polling instead of SSE.
  const pollInterval = 1500; // 1.5 seconds
  const maxDuration = 5 * 60 * 1000; // 5 minutes
  const deadline = Date.now() + maxDuration;

  while (true) {
    if (signal?.aborted) {
      throw new DOMException("Aborted", "AbortError");
    }
    if (Date.now() > deadline) {
      throw new Error(labels.errors.streamEnded);
    }

    let status: RefreshProgress;
    try {
      const { data: statusData } = await API.get(`/news/refresh/${jobId}`);
      status = statusData as RefreshProgress;
    } catch (err: any) {
      if (err?.name === "AbortError" || err?.code === "ERR_CANCELED" || signal?.aborted) {
        throw new DOMException("Aborted", "AbortError");
      }
      console.error("[news] poll failed:", err?.message || err, "code:", err?.code);
      throw err;
    }

    if (onProgress) {
      onProgress(status);
    }

    if (status.status === "completed" || status.status === "error" || status.status === "timeout") {
      return status;
    }

    // Wait before next poll, but resolve early if aborted
    await new Promise<void>((resolve) => {
      const timer = setTimeout(resolve, pollInterval);
      signal?.addEventListener("abort", () => {
        clearTimeout(timer);
        resolve();
      }, { once: true });
    });
  }
}
