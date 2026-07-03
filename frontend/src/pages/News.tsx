import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient, keepPreviousData } from "@tanstack/react-query";
import {
  AlertCircle,
  AlertTriangle,
  Bell,
  Calendar,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  Filter,
  Flame,
  Minus,
  Newspaper,
  RefreshCw,
  Search,
  Sparkles,
  Star,
  ThumbsDown,
  ThumbsUp,
  TrendingUp,
  UserCircle,
  X,
} from "lucide-react";
import {
  addWatchlist,
  aiSummary,
  type AiSummaryResponse,
  getAiStatus,
  getAlerts,
  getDailyBrief,
  getFeed,
  getNews,
  getSources,
  getTrending,
  getWatchlist,
  markAlertRead,
  refreshNewsStream,
  type RefreshProgress,
  removeWatchlist,
} from "../api/news";
import { ErrorMessage } from "../components/ErrorMessage";
import { EmptyState } from "../components/EmptyState";
import { FintechCard } from "../components/ui/FintechCard";
import { SectionHeader } from "../components/ui/SectionHeader";
import { Skeleton } from "../components/ui/Skeleton";
import { useAiQueue } from "../contexts/AiQueueContext";
import { useToast } from "../contexts/ToastContext";
import { usePersistentState } from "../hooks/usePersistentState";
import { labels } from "../i18n/vi";

type Tab = "feed" | "all" | "trending" | "watchlist" | "alerts";
type Region = "vn" | "global";
type ImpactOption = "" | "high" | "medium";

const vnTabs: { key: Tab; label: string; icon: typeof Newspaper }[] = [
  { key: "feed", label: labels.news.feed, icon: UserCircle },
  { key: "all", label: labels.news.all, icon: Newspaper },
  { key: "trending", label: labels.news.trending, icon: TrendingUp },
  { key: "watchlist", label: labels.news.watchlist, icon: Star },
  { key: "alerts", label: labels.news.alerts, icon: Bell },
];

const globalTabs: { key: Tab; label: string; icon: typeof Newspaper }[] = [
  { key: "all", label: labels.news.all, icon: Newspaper },
  { key: "trending", label: labels.news.trending, icon: TrendingUp },
];

function sentimentClass(label: string | null) {
  if (label === "positive") return "bg-emerald-100 text-emerald-700";
  if (label === "negative") return "bg-rose-100 text-rose-700";
  return "bg-slate-100 text-slate-600";
}

function impactClass(label: string | null) {
  if (label === "high") return "bg-amber-100 text-amber-700";
  if (label === "medium") return "bg-blue-100 text-blue-700";
  return "bg-slate-100 text-slate-600";
}

function SentimentBadge({ label, score }: { label: string | null; score: number | null }) {
  const text = labels.news[label as keyof typeof labels.news] ?? labels.news.neutral;
  const Icon = label === "positive" ? ThumbsUp : label === "negative" ? ThumbsDown : Minus;
  const scoreText =
    score != null ? `${score > 0 ? "+" : ""}${score.toFixed(2)}` : "";
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${sentimentClass(label)}`}
      title={`Cảm xúc: ${text}${scoreText ? ` (${scoreText})` : ""}`}
    >
      <Icon className="w-3 h-3" />
      {text}
      {scoreText && <span className="opacity-75 font-normal">{scoreText}</span>}
    </span>
  );
}

function ImpactBadge({ label, score }: { label: string | null; score: number | null }) {
  const text = labels.news[label as keyof typeof labels.news] ?? labels.news.low;
  const Icon = label === "high" ? AlertTriangle : label === "medium" ? AlertCircle : Minus;
  const scoreText = score != null ? `${Math.round(score * 100)}%` : "";
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${impactClass(label)}`}
      title={`Tác động: ${text}${scoreText ? ` (${scoreText})` : ""}`}
    >
      <Icon className="w-3 h-3" />
      {text}
      {scoreText && <span className="opacity-75 font-normal">{scoreText}</span>}
    </span>
  );
}

function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}

function Pagination({
  page,
  pageSize,
  total,
  onPageChange,
}: {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (p: number) => void;
}) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  const visiblePages = ((): (number | "ellipsis")[] => {
    if (totalPages <= 7) {
      return Array.from({ length: totalPages }, (_, i) => i + 1);
    }
    const pages: (number | "ellipsis")[] = [1];
    if (page + 1 > 4) pages.push("ellipsis");
    const start = Math.max(2, page + 1 - 1);
    const end = Math.min(totalPages - 1, page + 1 + 1);
    for (let i = start; i <= end; i++) pages.push(i);
    if (page + 1 < totalPages - 3) pages.push("ellipsis");
    if (totalPages > 1) pages.push(totalPages);
    return pages;
  })();

  const buttonBase =
    "min-w-[2rem] h-8 px-2 rounded-lg text-xs font-medium transition-colors flex items-center justify-center";
  const buttonInactive =
    "border border-fintech-border text-slate-600 hover:bg-slate-100 disabled:opacity-40 disabled:cursor-not-allowed";
  const buttonActive = "bg-slate-900 text-white border border-slate-900";

  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mt-4 pt-3 border-t border-fintech-border">
      <span className="text-xs text-slate-500">
        {total > 0
          ? `${page * pageSize + 1}-${Math.min((page + 1) * pageSize, total)} / ${total}`
          : labels.common.noData}
      </span>
      <div className="flex items-center gap-1.5">
        <button
          onClick={() => onPageChange(0)}
          disabled={page <= 0}
          className={`${buttonBase} ${buttonInactive}`}
          title="Trang đầu"
          aria-label="Trang đầu"
        >
          <ChevronsLeft className="w-4 h-4" />
        </button>
        <button
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 0}
          className={`${buttonBase} ${buttonInactive} gap-1`}
        >
          <ChevronLeft className="w-4 h-4" />
          <span className="hidden sm:inline">{labels.news.previous ?? "Trước"}</span>
        </button>
        {visiblePages.map((p, idx) =>
          p === "ellipsis" ? (
            <span key={`ellipsis-${idx}`} className="px-1 text-xs text-slate-400">
              …
            </span>
          ) : (
            <button
              key={p}
              onClick={() => onPageChange(p - 1)}
              className={`${buttonBase} ${page + 1 === p ? buttonActive : buttonInactive}`}
              aria-current={page + 1 === p ? "page" : undefined}
            >
              {p}
            </button>
          )
        )}
        <button
          onClick={() => onPageChange(page + 1)}
          disabled={page >= totalPages - 1}
          className={`${buttonBase} ${buttonInactive} gap-1`}
        >
          <span className="hidden sm:inline">{labels.news.next ?? "Sau"}</span>
          <ChevronRight className="w-4 h-4" />
        </button>
        <button
          onClick={() => onPageChange(totalPages - 1)}
          disabled={page >= totalPages - 1}
          className={`${buttonBase} ${buttonInactive}`}
          title="Trang cuối"
          aria-label="Trang cuối"
        >
          <ChevronsRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}

function ArticleRow({ article }: { article: any }) {
  return (
    <a
      href={article.url}
      target="_blank"
      rel="noreferrer"
      className="block p-4 rounded-xl border border-fintech-border bg-white/60 hover:bg-white transition-colors"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <h4 className="font-display font-semibold text-slate-900 leading-snug mb-1">
            {article.title}
          </h4>
          {article.summary && (
            <p className="text-sm text-slate-500 line-clamp-2 mb-2">{article.summary}</p>
          )}
          <div className="flex flex-wrap items-center gap-2 text-xs">
            {article.symbols?.map((s: string) => (
              <span key={s} className="px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 font-mono">
                {s}
              </span>
            ))}
            {article.tags
              ?.split(",")
              .map((tag: string) => tag.trim())
              .filter(Boolean)
              .map((tag: string) => (
                <span
                  key={tag}
                  className="px-2 py-0.5 rounded-md bg-indigo-50 text-indigo-700 font-medium"
                >
                  {tag}
                </span>
              ))}
            <span className="text-slate-400">
              {article.published_at
                ? new Date(article.published_at).toLocaleString("vi-VN")
                : labels.common.noData}
            </span>
          </div>
        </div>
        <div className="flex flex-col items-end gap-1.5">
          <SentimentBadge label={article.sentiment_label} score={article.sentiment_score} />
          <ImpactBadge label={article.impact_label} score={article.impact_score} />
        </div>
      </div>
    </a>
  );
}

export function News() {
  const qc = useQueryClient();
  const { showToast } = useToast();
  const { isBusy, runAi } = useAiQueue();
  const [region, setRegion] = usePersistentState<Region>("news.region", "vn");
  const [activeTab, setActiveTab] = usePersistentState<Tab>("news.activeTab", "feed");
  const tabs = region === "vn" ? vnTabs : globalTabs;
  const [search, setSearch] = usePersistentState("news.search", "");
  const debouncedSearch = useDebounce(search, 300);
  const [symbolFilter, setSymbolFilter] = usePersistentState("news.symbolFilter", "");
  const [sentimentFilter, setSentimentFilter] = usePersistentState("news.sentimentFilter", "");
  const [impactFilter, setImpactFilter] = usePersistentState<ImpactOption>("news.impactFilter", "");
  const [tagFilter, setTagFilter] = usePersistentState("news.tagFilter", "");
  const [sourceFilter, setSourceFilter] = usePersistentState("news.sourceFilter", "");
  const [dateFrom, setDateFrom] = usePersistentState("news.dateFrom", "");
  const [dateTo, setDateTo] = usePersistentState("news.dateTo", "");
  const [page, setPage] = usePersistentState("news.page", 0);
  const [feedPage, setFeedPage] = usePersistentState("news.feedPage", 0);
  const briefScope = region;
  const pageSize = 10;
  const [newSymbol, setNewSymbol] = usePersistentState("news.watchlistSymbol", "");
  const [newName, setNewName] = usePersistentState("news.watchlistName", "");
  const [aiSummaryOpen, setAiSummaryOpen] = useState(false);
  const [aiSummaryData, setAiSummaryData] = useState<AiSummaryResponse | null>(null);

  const minImpact = useMemo(() => {
    if (impactFilter === "high") return 0.7;
    if (impactFilter === "medium") return 0.4;
    return undefined;
  }, [impactFilter]);

  const resetFilters = () => {
    setSearch("");
    setSymbolFilter("");
    setSentimentFilter("");
    setImpactFilter("");
    setTagFilter("");
    setSourceFilter("");
    setDateFrom("");
    setDateTo("");
    setPage(0);
  };

  useEffect(() => {
    setPage(0);
  }, [debouncedSearch, symbolFilter, sentimentFilter, impactFilter, tagFilter, sourceFilter, dateFrom, dateTo]);

  useEffect(() => {
    if (activeTab !== "all") {
      setAiSummaryOpen(false);
    }
  }, [activeTab]);

  useEffect(() => {
    setActiveTab("all");
    resetFilters();
    setFeedPage(0);
    setAiSummaryOpen(false);
  }, [region]);

  const [refreshProgress, setRefreshProgress] = useState<RefreshProgress | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [refreshError, setRefreshError] = useState<Error | null>(null);

  const handleRefresh = async () => {
    if (isRefreshing) return;
    setIsRefreshing(true);
    setRefreshProgress(null);
    setRefreshError(null);

    const controller = new AbortController();
    const timeoutMs = 5 * 60 * 1000; // 5 minutes
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    try {
      for await (const progress of refreshNewsStream(undefined, region, controller.signal)) {
        setRefreshProgress(progress);
        if (progress.status === "completed" || progress.status === "error" || progress.status === "timeout") {
          break;
        }
      }
      qc.invalidateQueries({ queryKey: ["news"] });
      qc.invalidateQueries({ queryKey: ["news-feed"] });
      qc.invalidateQueries({ queryKey: ["news-trending"] });
      qc.invalidateQueries({ queryKey: ["news-brief"] });
      qc.invalidateQueries({ queryKey: ["news-alerts"] });
      qc.invalidateQueries({ queryKey: ["news-sources"] });
      showToast(labels.news.refreshSuccess || "Đã làm mới tin tức", "success");
    } catch (error: any) {
      if (error.name === "AbortError") {
        showToast(labels.news.refreshTimeout || "Yêu cầu làm mới đã hết thời gian", "error");
      } else {
        setRefreshError(error);
        showToast(error?.message || "Không thể làm mới tin", "error");
      }
    } finally {
      clearTimeout(timeoutId);
      setIsRefreshing(false);
      setRefreshProgress(null);
    }
  };

  const allNews = useQuery({
    queryKey: [
      "news",
      region,
      debouncedSearch,
      symbolFilter,
      sentimentFilter,
      impactFilter,
      tagFilter,
      sourceFilter,
      dateFrom,
      dateTo,
      page,
      pageSize,
    ],
    queryFn: () =>
      getNews({
        region,
        search: debouncedSearch || undefined,
        symbol: symbolFilter || undefined,
        sentiment: sentimentFilter || undefined,
        min_impact: minImpact,
        tag: tagFilter || undefined,
        source_id: sourceFilter ? Number(sourceFilter) : undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        limit: pageSize,
        offset: page * pageSize,
      }),
    enabled: activeTab === "all",
    placeholderData: keepPreviousData,
  });

  const feed = useQuery({
    queryKey: ["news-feed", region, feedPage, pageSize],
    queryFn: () =>
      getFeed({
        region,
        limit: pageSize,
        offset: feedPage * pageSize,
      }),
    enabled: activeTab === "feed" && region === "vn",
    placeholderData: keepPreviousData,
  });

  const trending = useQuery({
    queryKey: ["news-trending", region],
    queryFn: () => getTrending(24, region),
    enabled: activeTab === "trending",
  });

  const brief = useQuery({
    queryKey: ["news-brief", briefScope],
    queryFn: () => getDailyBrief(24, briefScope),
    placeholderData: keepPreviousData,
  });

  const alerts = useQuery({
    queryKey: ["news-alerts"],
    queryFn: () => getAlerts(),
    enabled: activeTab === "alerts" && region === "vn",
  });

  const sources = useQuery({
    queryKey: ["news-sources"],
    queryFn: () => getSources(),
    enabled: activeTab === "all",
  });

  const aiStatus = useQuery({
    queryKey: ["ai-status"],
    queryFn: () => getAiStatus(),
    refetchInterval: 3000,
    enabled: activeTab === "all",
  });

  const watchlist = useQuery({
    queryKey: ["news-watchlist"],
    queryFn: () => getWatchlist(),
    enabled: region === "vn" && (activeTab === "watchlist" || activeTab === "feed"),
  });

  const addWatchlistMutation = useMutation({
    mutationFn: ({ symbol, name }: { symbol: string; name: string }) => addWatchlist(symbol, name),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["news-watchlist"] });
      qc.invalidateQueries({ queryKey: ["news-feed"] });
      setNewSymbol("");
      setNewName("");
      showToast("Đã thêm vào danh sách theo dõi", "success");
    },
    onError: (error: any) => {
      showToast(error?.message || "Không thể thêm mã", "error");
    },
  });

  const removeWatchlistMutation = useMutation({
    mutationFn: (symbol: string) => removeWatchlist(symbol),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["news-watchlist"] });
      qc.invalidateQueries({ queryKey: ["news-feed"] });
      showToast("Đã xóa khỏi danh sách theo dõi", "success");
    },
  });

  const markReadMutation = useMutation({
    mutationFn: (id: number) => markAlertRead(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["news-alerts"] });
    },
  });

  const aiSummaryMutation = useMutation({
    mutationFn: () =>
      runAi("news_summary", () =>
        aiSummary({
          search: debouncedSearch || undefined,
          symbol: symbolFilter || undefined,
          sentiment: sentimentFilter || undefined,
          min_impact: minImpact,
          tag: tagFilter || undefined,
          source_id: sourceFilter ? Number(sourceFilter) : undefined,
          date_from: dateFrom || undefined,
          date_to: dateTo || undefined,
          region,
          limit: 5,
        })
      ),
    onSuccess: (data) => {
      setAiSummaryData(data);
      setAiSummaryOpen(true);
    },
    onError: (error: any) => {
      showToast(error?.message || "Không thể tạo tóm tắt AI", "error");
    },
  });

  const isLoading =
    (activeTab === "all" && allNews.isLoading) ||
    (activeTab === "feed" && feed.isLoading) ||
    (activeTab === "trending" && trending.isLoading) ||
    (activeTab === "alerts" && alerts.isLoading) ||
    (activeTab === "watchlist" && watchlist.isLoading);

  const error: Error | null =
    (activeTab === "all" ? allNews.error : null) ||
    (activeTab === "feed" ? feed.error : null) ||
    (activeTab === "trending" ? trending.error : null) ||
    (activeTab === "alerts" ? alerts.error : null) ||
    (activeTab === "watchlist" ? watchlist.error : null) ||
    refreshError ||
    null;

  const retry = () => {
    if (refreshError) {
      handleRefresh();
      return;
    }
    if (activeTab === "all") {
      allNews.refetch();
      sources.refetch();
    }
    if (activeTab === "feed") feed.refetch();
    if (activeTab === "trending") trending.refetch();
    if (activeTab === "alerts") alerts.refetch();
    if (activeTab === "watchlist") watchlist.refetch();
  };

  return (
    <div className="space-y-6">
      {error && <ErrorMessage error={error} retry={retry} />}

      <SectionHeader title={labels.news.title}>
        <div className="flex items-center gap-3">
          {brief.data && (
            <span className="text-xs text-slate-500 hidden sm:inline">
              {brief.data.total_articles} tin nổi bật 24h qua
            </span>
          )}
          <button onClick={handleRefresh} disabled={isRefreshing} className="btn-primary">
            <RefreshCw className={`w-4 h-4 ${isRefreshing ? "animate-spin" : ""}`} />
            {isRefreshing ? labels.news.refreshing : labels.news.refresh}
          </button>
        </div>
      </SectionHeader>

      {isRefreshing && refreshProgress && (
        <div className="w-full space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-600">
            <span className="inline-flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse" />
              {refreshProgress.message || labels.news.refreshing}
            </span>
            <span>
              {refreshProgress.current_source_index}/{refreshProgress.total_sources}
            </span>
          </div>
          <div className="w-full h-2 bg-slate-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-indigo-600 transition-all duration-300"
              style={{
                width: `${refreshProgress.total_sources > 0
                  ? (refreshProgress.current_source_index / refreshProgress.total_sources) * 100
                  : 0
                  }%`,
              }}
            />
          </div>
          <p className="text-xs text-slate-500">
            {labels.news.refreshProgress
              ? `${labels.news.refreshProgress}: ${refreshProgress.new_articles} tin mới`
              : `${refreshProgress.new_articles} tin mới`}
          </p>
        </div>
      )}

      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-1 p-1 rounded-xl bg-slate-100">
          {([
            { key: "vn", label: labels.news.vnNews ?? "Tin Việt Nam" },
            { key: "global", label: labels.news.globalNews ?? "Tin Quốc tế" },
          ] as { key: Region; label: string }[]).map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setRegion(key)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${region === key
                ? "bg-white text-slate-900 shadow-sm"
                : "text-slate-500 hover:text-slate-700"
                }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {brief.data && (
        <FintechCard delay={0.05}>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
            <h3 className="card-title inline-flex items-center">
              <Flame className="w-4 h-4 mr-2 text-amber-500" />
              {labels.news.dailyBrief}
              <span className="ml-2 text-xs font-normal text-slate-500">
                {region === "vn" ? labels.news.vnBrief ?? "Việt Nam" : labels.news.globalBrief ?? "Toàn cầu"}
              </span>
            </h3>
          </div>
          {brief.data.top_articles.length > 0 ? (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              <div className="lg:col-span-2 space-y-3">
                {brief.data.top_articles.slice(0, 3).map((article) => (
                  <ArticleRow key={article.id} article={article} />
                ))}
              </div>
              <div>
                <h4 className="text-sm font-semibold text-slate-700 mb-3">{labels.news.keySymbols}</h4>
                {brief.data.key_symbols.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {brief.data.key_symbols.map((s) => (
                      <span key={s.symbol} className="px-2.5 py-1 rounded-lg bg-slate-100 text-slate-700 text-sm font-mono">
                        {s.symbol}
                        <span className="ml-1.5 text-xs text-slate-500">{s.mentions}</span>
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-slate-500">{labels.common.noData}</p>
                )}
              </div>
            </div>
          ) : (
            <p className="text-sm text-slate-500">Chưa có tin nổi bật trong khu vực này.</p>
          )}
        </FintechCard>
      )}

      <FintechCard delay={0.1}>
        <div className="flex flex-wrap gap-2 mb-4 border-b border-fintech-border pb-3">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const active = activeTab === tab.key;
            return (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-colors ${active ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-100"
                  }`}
              >
                <Icon className="w-4 h-4" />
                {tab.label}
              </button>
            );
          })}
        </div>

        {activeTab === "all" && (
          <div className="space-y-3 mb-4">
            <div className="flex flex-wrap gap-3">
              <div className="relative min-w-[200px] flex-[2]">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input
                  type="text"
                  className="input-fintech pl-9"
                  placeholder={labels.news.search}
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
              </div>
              <input
                type="text"
                className="input-fintech min-w-[140px] flex-1"
                placeholder={labels.news.filterBySymbol}
                value={symbolFilter}
                onChange={(e) => setSymbolFilter(e.target.value.toUpperCase())}
              />
              <select
                className="input-fintech min-w-[140px] flex-1"
                value={sentimentFilter}
                onChange={(e) => setSentimentFilter(e.target.value)}
              >
                <option value="">{labels.news.allSentiments}</option>
                <option value="positive">{labels.news.positive}</option>
                <option value="negative">{labels.news.negative}</option>
                <option value="neutral">{labels.news.neutral}</option>
              </select>
              <select
                className="input-fintech min-w-[140px] flex-1"
                value={impactFilter}
                onChange={(e) => setImpactFilter(e.target.value as ImpactOption)}
              >
                <option value="">{labels.news.allImpacts}</option>
                <option value="high">{labels.news.highImpact}</option>
                <option value="medium">{labels.news.mediumImpact}</option>
              </select>
            </div>
            <div className="flex flex-wrap gap-3">
              <input
                type="text"
                className="input-fintech min-w-[140px] flex-1"
                placeholder={labels.news.tagFilter}
                value={tagFilter}
                onChange={(e) => setTagFilter(e.target.value)}
              />
              <select
                className="input-fintech min-w-[160px] flex-1"
                value={sourceFilter}
                onChange={(e) => setSourceFilter(e.target.value)}
                disabled={sources.isLoading}
              >
                <option value="">{labels.news.allSources}</option>
                {sources.data
                  ?.filter((s) => s.region === region)
                  .map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                    </option>
                  ))}
              </select>
              <div className="relative min-w-[150px] flex-1">
                <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input
                  type="date"
                  className="input-fintech pl-9"
                  placeholder={labels.news.dateFrom}
                  value={dateFrom}
                  onChange={(e) => setDateFrom(e.target.value)}
                />
              </div>
              <div className="relative min-w-[150px] flex-1">
                <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input
                  type="date"
                  className="input-fintech pl-9"
                  placeholder={labels.news.dateTo}
                  value={dateTo}
                  onChange={(e) => setDateTo(e.target.value)}
                />
              </div>
              <div className="flex items-center gap-2">
                {aiStatus.data?.busy && (
                  <span className="inline-flex items-center gap-1.5 px-2 py-1.5 rounded-lg text-xs font-medium bg-amber-100 text-amber-700">
                    <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
                    {labels.news.aiBusy}
                  </span>
                )}
                <button
                  onClick={() => aiSummaryMutation.mutate()}
                  disabled={aiSummaryMutation.isPending || allNews.isLoading || isBusy || aiStatus.data?.busy}
                  className="btn-primary px-3 py-2.5 text-xs"
                >
                  {aiSummaryMutation.isPending ? (
                    <RefreshCw className="w-4 h-4 animate-spin" />
                  ) : (
                    <Sparkles className="w-4 h-4" />
                  )}
                  {labels.news.aiSummary}
                </button>
                <button
                  onClick={resetFilters}
                  className="btn-secondary px-3 py-2.5 text-xs"
                  title={labels.news.clearFilters}
                >
                  <Filter className="w-4 h-4" />
                  {labels.news.clearFilters}
                </button>
              </div>
            </div>

            {aiSummaryOpen && aiSummaryData && (
              <div className="p-4 rounded-xl border border-indigo-100 bg-indigo-50/60">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-sm font-semibold text-indigo-900 inline-flex items-center gap-2">
                    <Sparkles className="w-4 h-4" />
                    {labels.news.aiSummary}
                    <span className="text-xs font-normal text-indigo-600">
                      ({aiSummaryData.article_count} tin{aiSummaryData.used_ollama ? " · Ollama" : ""})
                    </span>
                    {aiSummaryData.personalized && (
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-indigo-200 text-indigo-800">
                        {labels.news.personalized}
                      </span>
                    )}
                  </h4>
                  <button
                    onClick={() => setAiSummaryOpen(false)}
                    className="p-1 rounded-lg text-indigo-400 hover:text-indigo-700 hover:bg-indigo-100 transition-colors"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
                <div className="text-sm text-indigo-900 whitespace-pre-wrap leading-relaxed">
                  {aiSummaryData.summary}
                </div>
              </div>
            )}
          </div>
        )}

        {isLoading ? (
          <div className="space-y-3">
            <Skeleton className="h-24" count={4} />
          </div>
        ) : activeTab === "feed" ? (
          feed.data?.items?.length ? (
            <div className="space-y-3">
              {feed.data.items.map((article) => (
                <ArticleRow key={article.id} article={article} />
              ))}
              <Pagination
                page={feedPage}
                pageSize={pageSize}
                total={feed.data?.total ?? 0}
                onPageChange={setFeedPage}
              />
            </div>
          ) : (
            <EmptyState title={labels.news.noNews} description="Thêm tài sản hoặc mã vào danh sách theo dõi để nhận tin cá nhân hóa." />
          )
        ) : activeTab === "all" ? (
          allNews.data?.items?.length ? (
            <div className="space-y-3">
              {allNews.data.items.map((article) => (
                <ArticleRow key={article.id} article={article} />
              ))}
              <Pagination
                page={page}
                pageSize={pageSize}
                total={allNews.data?.total ?? 0}
                onPageChange={setPage}
              />
            </div>
          ) : (
            <EmptyState
              title={region === "global" ? labels.news.noGlobalNews : labels.news.noNews}
              description="Nhấn Làm mới tin để thu thập tin tức từ các nguồn."
            />
          )
        ) : activeTab === "trending" ? (
          trending.data ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h4 className="text-sm font-semibold text-slate-700 mb-3">{labels.news.symbols}</h4>
                {trending.data.symbols.length > 0 ? (
                  <div className="space-y-2">
                    {trending.data.symbols.map((s) => (
                      <div
                        key={s.symbol}
                        className="flex items-center justify-between p-3 rounded-xl border border-fintech-border bg-white/60"
                      >
                        <span className="font-mono font-semibold text-slate-900">{s.symbol}</span>
                        <span className="text-sm text-slate-500">
                          {s.mentions} {labels.news.mentions}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-slate-500">{labels.common.noData}</p>
                )}
              </div>
              <div>
                <h4 className="text-sm font-semibold text-slate-700 mb-3">{labels.news.sentiment}</h4>
                <div className="space-y-2">
                  {Object.entries(trending.data.sentiment).map(([key, value]) => (
                    <div
                      key={key}
                      className="flex items-center justify-between p-3 rounded-xl border border-fintech-border bg-white/60"
                    >
                      <span>{labels.news[key as keyof typeof labels.news] ?? key}</span>
                      <span className="font-mono font-semibold text-slate-900">{value}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <EmptyState title={labels.common.noData} description="Chưa đủ dữ liệu tin tức để phân tích xu hướng." />
          )
        ) : activeTab === "watchlist" ? (
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <input
                type="text"
                className="input-fintech"
                placeholder={labels.news.symbol}
                value={newSymbol}
                onChange={(e) => setNewSymbol(e.target.value.toUpperCase())}
              />
              <input
                type="text"
                className="input-fintech"
                placeholder={labels.assets.name}
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
              />
              <button
                onClick={() => newSymbol && addWatchlistMutation.mutate({ symbol: newSymbol, name: newName })}
                disabled={!newSymbol || addWatchlistMutation.isPending}
                className="btn-primary"
              >
                {labels.news.addWatchlist}
              </button>
            </div>
            {watchlist.data?.length ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {watchlist.data.map((item) => (
                  <div
                    key={item.id}
                    className="flex items-center justify-between p-3 rounded-xl border border-fintech-border bg-white/60"
                  >
                    <div>
                      <div className="font-mono font-semibold text-slate-900">{item.symbol}</div>
                      {item.name && <div className="text-xs text-slate-500">{item.name}</div>}
                    </div>
                    <button
                      onClick={() => removeWatchlistMutation.mutate(item.symbol)}
                      className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-colors"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState title={labels.news.noWatchlist} description="Thêm mã cổ phiếu/quỹ bạn quan tâm để nhận tin cá nhân hóa." />
            )}
          </div>
        ) : activeTab === "alerts" ? (
          alerts.data?.length ? (
            <div className="space-y-3">
              {alerts.data.map((alert) => (
                <div
                  key={alert.id}
                  className={`p-4 rounded-xl border border-fintech-border ${alert.is_read ? "bg-white/40" : "bg-white/80"}`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        {alert.symbol && (
                          <span className="px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 font-mono text-xs">
                            {alert.symbol}
                          </span>
                        )}
                        <span className="text-xs text-slate-400">{new Date(alert.created_at).toLocaleString("vi-VN")}</span>
                      </div>
                      <h4 className={`font-display font-semibold ${alert.is_read ? "text-slate-500" : "text-slate-900"}`}>
                        {alert.title}
                      </h4>
                      <p className="text-sm text-slate-500 mt-1">{alert.message}</p>
                    </div>
                    {!alert.is_read && (
                      <button
                        onClick={() => markReadMutation.mutate(alert.id)}
                        className="btn-secondary text-xs"
                      >
                        {labels.news.markRead}
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState title={labels.news.noAlerts} description="Cảnh báo sẽ xuất hiện khi có tin quan trọng về mã trong danh mục hoặc watchlist." />
          )
        ) : null}
      </FintechCard>
    </div>
  );
}
