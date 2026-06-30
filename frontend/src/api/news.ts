import API from "./client";

export interface Article {
  id: number;
  source_id: number;
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
  language: string | null;
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

export async function getTrending(hours = 24): Promise<Trending> {
  const { data } = await API.get("/news/trending/now", { params: { hours } });
  return data;
}

export async function getDailyBrief(hours = 24): Promise<DailyBrief> {
  const { data } = await API.get("/news/brief/daily", { params: { hours } });
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

export async function refreshNews(source?: string): Promise<{ results: Record<string, number>; alerts_generated: number }> {
  const { data } = await API.post("/news/refresh", null, { params: source ? { source } : undefined });
  return data;
}
