import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Bell,
  Flame,
  Newspaper,
  RefreshCw,
  Search,
  Star,
  TrendingUp,
  UserCircle,
  X,
} from "lucide-react";
import {
  addWatchlist,
  getAlerts,
  getDailyBrief,
  getFeed,
  getNews,
  getTrending,
  getWatchlist,
  markAlertRead,
  refreshNews,
  removeWatchlist,
} from "../api/news";
import { ErrorMessage } from "../components/ErrorMessage";
import { EmptyState } from "../components/EmptyState";
import { FintechCard } from "../components/ui/FintechCard";
import { SectionHeader } from "../components/ui/SectionHeader";
import { Skeleton } from "../components/ui/Skeleton";
import { useToast } from "../contexts/ToastContext";
import { labels } from "../i18n/vi";

type Tab = "feed" | "all" | "trending" | "watchlist" | "alerts";

const tabs: { key: Tab; label: string; icon: typeof Newspaper }[] = [
  { key: "feed", label: labels.news.feed, icon: UserCircle },
  { key: "all", label: labels.news.all, icon: Newspaper },
  { key: "trending", label: labels.news.trending, icon: TrendingUp },
  { key: "watchlist", label: labels.news.watchlist, icon: Star },
  { key: "alerts", label: labels.news.alerts, icon: Bell },
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
            <span className="text-slate-400">
              {article.published_at
                ? new Date(article.published_at).toLocaleString("vi-VN")
                : labels.common.noData}
            </span>
          </div>
        </div>
        <div className="flex flex-col items-end gap-1.5">
          <span className={`px-2 py-1 rounded-full text-xs font-medium ${sentimentClass(article.sentiment_label)}`}>
            {labels.news[article.sentiment_label as keyof typeof labels.news] ?? labels.news.neutral}
          </span>
          <span className={`px-2 py-1 rounded-full text-xs font-medium ${impactClass(article.impact_label)}`}>
            {labels.news[article.impact_label as keyof typeof labels.news] ?? labels.news.low}
          </span>
        </div>
      </div>
    </a>
  );
}

export function News() {
  const qc = useQueryClient();
  const { showToast } = useToast();
  const [activeTab, setActiveTab] = useState<Tab>("feed");
  const [search, setSearch] = useState("");
  const [symbolFilter, setSymbolFilter] = useState("");
  const [sentimentFilter, setSentimentFilter] = useState("");
  const [newSymbol, setNewSymbol] = useState("");
  const [newName, setNewName] = useState("");

  const refresh = useMutation({
    mutationFn: () => refreshNews(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["news"] });
      qc.invalidateQueries({ queryKey: ["news-feed"] });
      qc.invalidateQueries({ queryKey: ["news-trending"] });
      qc.invalidateQueries({ queryKey: ["news-brief"] });
      qc.invalidateQueries({ queryKey: ["news-alerts"] });
      showToast("Đã làm mới tin tức", "success");
    },
    onError: (error: any) => {
      showToast(error?.message || "Không thể làm mới tin", "error");
    },
  });

  const allNews = useQuery({
    queryKey: ["news", search, symbolFilter, sentimentFilter],
    queryFn: () =>
      getNews({
        search: search || undefined,
        symbol: symbolFilter || undefined,
        sentiment: sentimentFilter || undefined,
        limit: 50,
      }),
    enabled: activeTab === "all",
  });

  const feed = useQuery({
    queryKey: ["news-feed"],
    queryFn: () => getFeed(),
    enabled: activeTab === "feed",
  });

  const trending = useQuery({
    queryKey: ["news-trending"],
    queryFn: () => getTrending(),
    enabled: activeTab === "trending",
  });

  const brief = useQuery({
    queryKey: ["news-brief"],
    queryFn: () => getDailyBrief(),
  });

  const alerts = useQuery({
    queryKey: ["news-alerts"],
    queryFn: () => getAlerts(),
    enabled: activeTab === "alerts",
  });

  const watchlist = useQuery({
    queryKey: ["news-watchlist"],
    queryFn: () => getWatchlist(),
    enabled: activeTab === "watchlist" || activeTab === "feed",
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
    refresh.error ||
    null;

  const retry = () => {
    if (activeTab === "all") allNews.refetch();
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
          <button onClick={() => refresh.mutate()} disabled={refresh.isPending} className="btn-primary">
            <RefreshCw className={`w-4 h-4 ${refresh.isPending ? "animate-spin" : ""}`} />
            {refresh.isPending ? labels.news.refreshing : labels.news.refresh}
          </button>
        </div>
      </SectionHeader>

      {brief.data && brief.data.top_articles.length > 0 && (
        <FintechCard delay={0.05}>
          <div className="flex items-center justify-between mb-4">
            <h3 className="card-title inline-flex items-center">
              <Flame className="w-4 h-4 mr-2 text-amber-500" />
              {labels.news.dailyBrief}
            </h3>
          </div>
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
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mb-4">
            <div className="relative md:col-span-2">
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
              className="input-fintech"
              placeholder={labels.news.filterBySymbol}
              value={symbolFilter}
              onChange={(e) => setSymbolFilter(e.target.value.toUpperCase())}
            />
            <select
              className="input-fintech"
              value={sentimentFilter}
              onChange={(e) => setSentimentFilter(e.target.value)}
            >
              <option value="">{labels.news.allSentiments}</option>
              <option value="positive">{labels.news.positive}</option>
              <option value="negative">{labels.news.negative}</option>
              <option value="neutral">{labels.news.neutral}</option>
            </select>
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
            </div>
          ) : (
            <EmptyState title={labels.news.noNews} description="Nhấn Làm mới tin để thu thập tin tức từ các nguồn." />
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
