/**
 * Centralized TanStack Query key factory.
 *
 * Usage:
 *   queryKeys.transactions.list({ page: 1 })
 *   queryKeys.portfolio.detail()
 *
 * Following the nested factory pattern recommended by TanStack Query docs.
 */
export const queryKeys = {
  transactions: {
    all: ["transactions"] as const,
    lists: () => [...queryKeys.transactions.all, "list"] as const,
    list: (filters: Record<string, unknown>) =>
      [...queryKeys.transactions.lists(), filters] as const,
    details: () => [...queryKeys.transactions.all, "detail"] as const,
    detail: (id: string | number) =>
      [...queryKeys.transactions.details(), id] as const,
  },
  assets: {
    all: ["assets"] as const,
    lists: () => [...queryKeys.assets.all, "list"] as const,
    list: (filters: Record<string, unknown>) =>
      [...queryKeys.assets.lists(), filters] as const,
    details: () => [...queryKeys.assets.all, "detail"] as const,
    detail: (id: string | number) =>
      [...queryKeys.assets.details(), id] as const,
    types: () => [...queryKeys.assets.all, "types"] as const,
  },
  prices: {
    all: ["prices"] as const,
    quotes: () => [...queryKeys.prices.all, "quotes"] as const,
    quote: (symbols: string, types?: string) =>
      [...queryKeys.prices.quotes(), { symbols, types }] as const,
    preview: (assetId: string | number) =>
      [...queryKeys.prices.all, "preview", assetId] as const,
    history: (symbol: string, type: string, start: string, end: string) =>
      [...queryKeys.prices.all, "history", symbol, type, start, end] as const,
    stocks: () => [...queryKeys.prices.all, "stocks"] as const,
    funds: () => [...queryKeys.prices.all, "funds"] as const,
    stockDetail: (symbol: string) =>
      [...queryKeys.prices.all, "stock-detail", symbol] as const,
    fundDetail: (symbol: string) =>
      [...queryKeys.prices.all, "fund-detail", symbol] as const,
  },
  portfolio: {
    all: ["portfolio"] as const,
    detail: () => [...queryKeys.portfolio.all, "detail"] as const,
    history: (start?: string, end?: string) =>
      [...queryKeys.portfolio.all, "history", { start, end }] as const,
    historyTrend: (start?: string, end?: string) =>
      [...queryKeys.portfolio.all, "history-trend", { start, end }] as const,
    benchmarkTrend: (start?: string, end?: string) =>
      [...queryKeys.portfolio.all, "benchmark-trend", { start, end }] as const,
  },
  analytics: {
    all: ["analytics"] as const,
    summary: (filterType?: string, start?: string, end?: string) =>
      [...queryKeys.analytics.all, "summary", { filterType, start, end }] as const,
    risk: () => [...queryKeys.analytics.all, "risk"] as const,
  },
  news: {
    all: ["news"] as const,
    list: (filters: Record<string, unknown>) =>
      [...queryKeys.news.all, "list", filters] as const,
    feed: (region: string, page: number, pageSize: number) =>
      [...queryKeys.news.all, "feed", { region, page, pageSize }] as const,
    trending: (region: string) =>
      [...queryKeys.news.all, "trending", region] as const,
    brief: (scope?: string) =>
      [...queryKeys.news.all, "brief", { scope }] as const,
    alerts: () => [...queryKeys.news.all, "alerts"] as const,
    alertsUnread: () => [...queryKeys.news.all, "alerts", "unread"] as const,
    sources: () => [...queryKeys.news.all, "sources"] as const,
    watchlist: () => [...queryKeys.news.all, "watchlist"] as const,
  },
  alerts: {
    all: ["price-alerts"] as const,
    lists: () => [...queryKeys.alerts.all, "list"] as const,
    list: () => [...queryKeys.alerts.lists()] as const,
    details: () => [...queryKeys.alerts.all, "detail"] as const,
    detail: (id: string | number) =>
      [...queryKeys.alerts.details(), id] as const,
    notifications: () => [...queryKeys.alerts.all, "notifications"] as const,
  },
  income: {
    all: ["income"] as const,
    lists: () => [...queryKeys.income.all, "list"] as const,
    list: (filters: Record<string, unknown>) =>
      [...queryKeys.income.lists(), filters] as const,
    details: () => [...queryKeys.income.all, "detail"] as const,
    detail: (id: string | number) =>
      [...queryKeys.income.details(), id] as const,
  },
  goldFx: {
    all: ["gold-fx"] as const,
    detail: () => [...queryKeys.goldFx.all, "detail"] as const,
  },
  compare: {
    all: ["compare"] as const,
    symbols: () => [...queryKeys.compare.all, "symbols"] as const,
    quotes: (symbols: string, types: string) =>
      [...queryKeys.compare.all, "quotes", { symbols, types }] as const,
    metrics: (symbols: string, types: string, start: string, end: string) =>
      [...queryKeys.compare.all, "metrics", { symbols, types, start, end }] as const,
    correlation: (symbols: string, types: string, start: string, end: string) =>
      [...queryKeys.compare.all, "correlation", { symbols, types, start, end }] as const,
    history: (symbol: string, start: string, end: string) =>
      [...queryKeys.compare.all, "history", symbol, { start, end }] as const,
  },
  ai: {
    all: ["ai"] as const,
    status: () => [...queryKeys.ai.all, "status"] as const,
    rateLimit: () => [...queryKeys.ai.all, "rate-limit"] as const,
    insight: (scope: string, filters?: Record<string, unknown>) =>
      [...queryKeys.ai.all, "insight", scope, filters ?? {}] as const,
  },
  settings: {
    all: ["settings"] as const,
    assetTypes: () => [...queryKeys.settings.all, "asset-types"] as const,
    allocationTargets: () =>
      [...queryKeys.settings.all, "allocation-targets"] as const,
    defaultSources: () => [...queryKeys.settings.all, "default-sources"] as const,
    envConfig: () => [...queryKeys.settings.all, "env-config"] as const,
  },
  rebalance: {
    all: ["rebalance"] as const,
    detail: () => [...queryKeys.rebalance.all, "detail"] as const,
    targets: () => [...queryKeys.rebalance.all, "targets"] as const,
  },
  backtest: {
    all: ["backtest"] as const,
    benchmark: (start: string, end: string) =>
      [...queryKeys.backtest.all, "benchmark", { start, end }] as const,
  },
  market: {
    all: ["market"] as const,
    quotes: (symbols: string, tab?: string) =>
      [...queryKeys.market.all, "quotes", { symbols, tab }] as const,
    watchlist: () => [...queryKeys.market.all, "watchlist"] as const,
    symbols: (tab: string) =>
      [...queryKeys.market.all, "symbols", tab] as const,
  },
} as const;
