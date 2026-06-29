import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { LineChart as LineChartIcon, RefreshCw } from "lucide-react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import API from "../api/client";
import { ErrorMessage } from "../components/ErrorMessage";
import { InfoTooltip } from "../components/InfoTooltip";
import SymbolDetailModal from "../components/SymbolDetailModal";
import { AnimatedNumber } from "../components/ui/AnimatedNumber";
import { FintechCard } from "../components/ui/FintechCard";
import { MiniSparkline } from "../components/ui/MiniSparkline";
import { SectionHeader } from "../components/ui/SectionHeader";
import { TrendBadge } from "../components/ui/TrendBadge";
import { labels } from "../i18n/vi";
import { chartTooltipStyle, formatCurrency, formatNumber } from "../lib/utils";


export function Market() {
  const today = new Date().toISOString().split("T")[0];
  const oneMonthAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split("T")[0];

  const WATCHLIST_SYMBOLS =
    "VCB,VHM,VIC,FPT,GAS,HPG,MBB,MSN,MWG,PLX,SSI,TCB,VIB,VPB,E1VFVN30,FUEVFVND,FUESSVFL";

  const [assetId, setAssetId] = useState("");
  const [start, setStart] = useState(oneMonthAgo);
  const [end, setEnd] = useState(today);

  const [activeTab, setActiveTab] = useState<"STOCK" | "FUND">("STOCK");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [selectedSymbol, setSelectedSymbol] = useState<{
    symbol: string;
    name: string;
    type: string;
    exchange: string;
  } | null>(null);
  const PAGE_SIZE = 20;

  const assets = useQuery({
    queryKey: ["assets"],
    queryFn: async () => {
      const { data } = await API.get("/assets/");
      return data;
    },
  });

  const history = useQuery({
    queryKey: ["price-history", assetId, start, end],
    queryFn: async () => {
      if (!assetId) return [];
      const { data } = await API.get(`/prices/history/${assetId}`, {
        params: { start, end },
      });
      return data as Array<{ date: string; price: number }>;
    },
    enabled: !!assetId,
  });

  const goldFx = useQuery({
    queryKey: ["gold-fx"],
    queryFn: async () => {
      const { data } = await API.get("/gold-fx/");
      return data;
    },
  });

  const marketWatchlist = useQuery({
    queryKey: ["market-watchlist"],
    queryFn: async () => {
      const { data } = await API.get("/prices/quote", {
        params: { symbols: WATCHLIST_SYMBOLS },
      });
      return data as Array<{
        symbol: string;
        price: number;
        change: number;
        change_percent: number;
        date: string;
      }>;
    },
  });

  const allSymbols = useQuery({
    queryKey: ["market-symbols", activeTab],
    queryFn: async () => {
      const endpoint = activeTab === "STOCK" ? "/prices/stocks" : "/prices/funds";
      const { data } = await API.get(endpoint);
      return data as Array<{ symbol: string; name: string; exchange: string; type: string }>;
    },
  });

  const filteredSymbols =
    allSymbols.data?.filter((item) => {
      if (item.type !== activeTab) return false;
      const q = search.trim().toLowerCase();
      if (!q) return true;
      return item.symbol.toLowerCase().includes(q) || item.name.toLowerCase().includes(q);
    }) || [];

  const totalPages = Math.max(1, Math.ceil(filteredSymbols.length / PAGE_SIZE));
  const pageSymbols = filteredSymbols.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  const pageSymbolsStr = pageSymbols.map((s) => s.symbol).join(",");

  const pageQuotes = useQuery({
    queryKey: ["market-quotes", pageSymbolsStr, activeTab],
    queryFn: async () => {
      const { data } = await API.get("/prices/quote", {
        params: { symbols: pageSymbolsStr, asset_type: activeTab },
      });
      return data as Array<{
        symbol: string;
        price: number;
        change: number;
        change_percent: number;
        date: string;
      }>;
    },
    enabled: !!pageSymbolsStr,
  });

  const quoteMap = Object.fromEntries(pageQuotes.data?.map((q) => [q.symbol, q]) || []);

  const portfolio = useQuery({
    queryKey: ["portfolio"],
    queryFn: async () => (await API.get("/portfolio/")).data,
  });

  const selectedAsset = assets.data?.find((a: any) => a.id === Number(assetId));

  const stockFundItems =
    portfolio.data?.items?.filter((item: any) => ["STOCK", "FUND", "ETF"].includes(item.type)) || [];
  const stockFundTotal = stockFundItems.reduce((sum: number, item: any) => sum + (item.current_value || 0), 0);
  const latest = history.data?.[history.data.length - 1];
  const previous = history.data?.[history.data.length - 2] ?? latest;

  const change = latest && previous ? latest.price - previous.price : 0;
  const changePercent = previous && previous.price ? (change / previous.price) * 100 : 0;
  const high = history.data?.length ? Math.max(...history.data.map((d) => d.price)) : 0;
  const low = history.data?.length ? Math.min(...history.data.map((d) => d.price)) : 0;

  const miniSparkline = history.data?.length
    ? history.data.map((d) => d.price)
    : [];

  return (
    <div className="space-y-6">
      {assets.isError && <ErrorMessage error={assets.error} retry={() => assets.refetch()} />}
      {history.isError && <ErrorMessage error={history.error} retry={() => history.refetch()} />}
      {goldFx.isError && <ErrorMessage error={goldFx.error} retry={() => goldFx.refetch()} />}
      {marketWatchlist.isError && <ErrorMessage error={marketWatchlist.error} retry={() => marketWatchlist.refetch()} />}
      {allSymbols.isError && <ErrorMessage error={allSymbols.error} retry={() => allSymbols.refetch()} />}
      {pageQuotes.isError && <ErrorMessage error={pageQuotes.error} retry={() => pageQuotes.refetch()} />}
      {portfolio.isError && <ErrorMessage error={portfolio.error} retry={() => portfolio.refetch()} />}

      <SectionHeader title={labels.market.title} />

      <FintechCard delay={0.05}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="card-title inline-flex items-center">
            {labels.market.watchlist}
            <InfoTooltip content={labels.tooltips.marketWatchlist} />
          </h3>
          <span className="text-sm font-mono text-slate-600">
            {labels.market.totalValue}: {portfolio.isLoading ? "..." : formatCurrency(stockFundTotal)}
          </span>
        </div>
        {portfolio.isLoading ? (
          <div className="text-slate-500 py-4">{labels.common.loading}</div>
        ) : stockFundItems.length > 0 ? (
          <div className="overflow-x-auto scrollbar-thin">
            <table className="table-fintech">
              <thead>
                <tr>
                  <th className="text-left">
                    {labels.dashboard.symbol}
                    <InfoTooltip content={labels.tooltips.assetSymbol} />
                  </th>
                  <th className="text-left">
                    {labels.market.type}
                    <InfoTooltip content={labels.tooltips.assetType} />
                  </th>
                  <th className="text-right">
                    {labels.dashboard.quantity}
                    <InfoTooltip content={labels.tooltips.transactionQuantity} />
                  </th>
                  <th className="text-right">
                    {labels.dashboard.price}
                    <InfoTooltip content={labels.tooltips.transactionPrice} />
                  </th>
                  <th className="text-right">
                    {labels.dashboard.value}
                    <InfoTooltip content={labels.tooltips.totalValue} />
                  </th>
                  <th className="text-right">
                    {labels.dashboard.pnl}
                    <InfoTooltip content={labels.tooltips.pnl} />
                  </th>
                </tr>
              </thead>
              <tbody>
                {stockFundItems.map((item: any) => (
                  <tr key={item.asset_id}>
                    <td>
                      <div className="font-display font-semibold text-slate-900">{item.symbol}</div>
                      <div className="text-xs text-slate-500">{item.name}</div>
                    </td>
                    <td className="text-xs text-slate-500">
                      {labels.assetTypes[item.type as keyof typeof labels.assetTypes] ?? item.type}
                    </td>
                    <td className="text-right font-mono">{formatNumber(item.quantity, 4)}</td>
                    <td className="text-right font-mono">{formatCurrency(item.latest_price)}</td>
                    <td className="text-right font-mono text-slate-900">{formatCurrency(item.current_value)}</td>
                    <td className="text-right">
                      <TrendBadge value={(item.pnl / (item.current_value - item.pnl || 1)) * 100} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-slate-500 py-4">{labels.market.noStockFund}</div>
        )}
      </FintechCard>

      <FintechCard delay={0.1}>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 items-end">
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1.5 uppercase tracking-wider">
              {labels.market.selectAsset}
              <InfoTooltip content={labels.tooltips.marketSelectAsset} />
            </label>
            <select className="input-fintech" value={assetId} onChange={(e) => setAssetId(e.target.value)}>
              <option value="">{labels.market.selectAsset}</option>
              {assets.data?.map((a: any) => (
                <option key={a.id} value={a.id}>
                  {a.symbol} — {a.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1.5 uppercase tracking-wider">
              {labels.market.startDate}
              <InfoTooltip content={labels.tooltips.marketDateRange} />
            </label>
            <input
              type="date"
              className="input-fintech"
              value={start}
              onChange={(e) => setStart(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1.5 uppercase tracking-wider">
              {labels.market.endDate}
              <InfoTooltip content={labels.tooltips.marketDateRange} />
            </label>
            <input
              type="date"
              className="input-fintech"
              value={end}
              onChange={(e) => setEnd(e.target.value)}
            />
          </div>
          <button
            onClick={() => history.refetch()}
            disabled={!assetId || history.isFetching}
            className="btn-primary"
          >
            <LineChartIcon className="w-4 h-4" />
            {history.isFetching ? labels.market.loading : labels.market.load}
          </button>
        </div>
      </FintechCard>

      {selectedAsset && latest && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <FintechCard delay={0.15}>
            <div className="card-title mb-1 inline-flex items-center">
              {labels.market.currentPrice}
              <InfoTooltip content={labels.tooltips.transactionPrice} />
            </div>
            <div className="metric-value">
              <AnimatedNumber value={latest.price} formatter={formatCurrency} />
            </div>
            <div className="mt-2">
              <TrendBadge value={changePercent} />
            </div>
          </FintechCard>
          <FintechCard delay={0.2}>
            <div className="card-title mb-1 inline-flex items-center">
              {labels.market.change}
              <InfoTooltip content={labels.tooltips.marketWatchlist} />
            </div>
            <div className={`metric-value ${changePercent >= 0 ? "text-accent-emerald" : "text-accent-rose"}`}>
              {formatCurrency(change)}
            </div>
            <div className="mt-2 text-xs text-slate-500">{labels.market.vsPrevious}</div>
          </FintechCard>
          <FintechCard delay={0.25}>
            <div className="card-title mb-1 inline-flex items-center">
              {labels.market.high}
              <InfoTooltip content={labels.tooltips.marketWatchlist} />
            </div>
            <div className="metric-value text-accent-cyan">{formatCurrency(high)}</div>
          </FintechCard>
          <FintechCard delay={0.3}>
            <div className="card-title mb-1 inline-flex items-center">
              {labels.market.low}
              <InfoTooltip content={labels.tooltips.marketWatchlist} />
            </div>
            <div className="metric-value text-accent-amber">{formatCurrency(low)}</div>
          </FintechCard>
        </div>
      )}

      {history.data && history.data.length > 0 && (
        <FintechCard delay={0.35}>
          <div className="flex items-center justify-between mb-4">
            <h3 className="card-title inline-flex items-center">
              {selectedAsset?.symbol} — {labels.market.priceHistory}
              <InfoTooltip content={labels.tooltips.marketDateRange} />
            </h3>
            <MiniSparkline data={miniSparkline} color={changePercent >= 0 ? "emerald" : "rose"} width={140} height={36} />
          </div>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={history.data}>
                <defs>
                  <linearGradient id="marketGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={changePercent >= 0 ? "#34D399" : "#FB7185"} stopOpacity={0.3} />
                    <stop offset="100%" stopColor={changePercent >= 0 ? "#34D399" : "#FB7185"} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.1)" vertical={false} />
                <XAxis dataKey="date" tick={{ fill: "#64748b", fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tickFormatter={(v) => formatCurrency(v)} tick={{ fill: "#64748b", fontSize: 11 }} axisLine={false} tickLine={false} width={80} />
                <Tooltip contentStyle={chartTooltipStyle} formatter={(v) => [formatCurrency(v as number), labels.market.priceHistory]} />
                <Area
                  type="monotone"
                  dataKey="price"
                  stroke={changePercent >= 0 ? "#34D399" : "#FB7185"}
                  strokeWidth={2.5}
                  fill="url(#marketGradient)"
                  dot={false}
                  activeDot={{ r: 5, stroke: "#ffffff", strokeWidth: 2 }}
                  animationDuration={1200}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </FintechCard>
      )}

      {history.data && history.data.length === 0 && !history.isFetching && assetId && (
        <div className="text-slate-500">{labels.market.noData}</div>
      )}

      {/* <FintechCard delay={0.12}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="card-title">{labels.market.marketWatchlist}</h3>
          <button onClick={() => marketWatchlist.refetch()} className="btn-secondary">
            <RefreshCw className={`w-4 h-4 ${marketWatchlist.isFetching ? "animate-spin" : ""}`} />
            {labels.settings.refresh}
          </button>
        </div>
        {marketWatchlist.isLoading ? (
          <div className="text-slate-500 py-4">{labels.common.loading}</div>
        ) : marketWatchlist.data && marketWatchlist.data.length > 0 ? (
          <div className="overflow-x-auto scrollbar-thin">
            <table className="table-fintech">
              <thead>
                <tr>
                  <th className="text-left">{labels.market.symbol}</th>
                  <th className="text-right">{labels.market.price}</th>
                  <th className="text-right">{labels.market.change}</th>
                  <th className="text-right">{labels.market.marketChangePercent}</th>
                  <th className="text-right">{labels.market.marketDataDate}</th>
                </tr>
              </thead>
              <tbody>
                {marketWatchlist.data.map((item) => (
                  <tr key={item.symbol}>
                    <td className="font-display font-semibold text-slate-900">{item.symbol}</td>
                    <td className="text-right font-mono">{formatCurrency(item.price)}</td>
                    <td
                      className={`text-right font-mono ${item.change >= 0 ? "text-accent-emerald" : "text-accent-rose"
                        }`}
                    >
                      {formatCurrency(item.change)}
                    </td>
                    <td className="text-right">
                      <TrendBadge value={item.change_percent} />
                    </td>
                    <td className="text-right text-xs text-slate-500">{item.date}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-slate-500 py-4">{labels.market.noData}</div>
        )}
      </FintechCard> */}

      {allSymbols.data && (
        <FintechCard delay={0.15}>
          <div className="flex items-center justify-between mb-4">
            <h3 className="card-title inline-flex items-center">
              {labels.market.marketSymbolsTitle}
              <InfoTooltip content={labels.tooltips.marketWatchlist} />
            </h3>
            <div className="text-sm text-slate-500">
              {filteredSymbols.length} {labels.assets.symbol}
            </div>
          </div>

          <div className="flex flex-col md:flex-row gap-3 mb-4">
            <div className="flex bg-slate-100 rounded-lg p-1 w-full md:w-auto">
              {(["STOCK", "FUND"] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => {
                    setActiveTab(tab);
                    setPage(1);
                  }}
                  className={`flex-1 md:flex-none px-4 py-1.5 text-sm font-medium rounded-md transition-colors ${activeTab === tab
                    ? "bg-white text-slate-900 shadow-sm"
                    : "text-slate-500 hover:text-slate-900"
                    }`}
                >
                  {tab === "STOCK" ? labels.market.stocks : labels.market.funds}
                </button>
              ))}
            </div>
            <input
              type="text"
              placeholder={labels.market.searchPlaceholder}
              className="input-fintech flex-1"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
            />
            <div className="flex items-center gap-2">
              <InfoTooltip content={labels.tooltips.refreshPrices} />
              <button
                onClick={() => pageQuotes.refetch()}
                disabled={pageQuotes.isFetching || pageSymbols.length === 0}
                className="btn-secondary"
              >
                <RefreshCw className={`w-4 h-4 ${pageQuotes.isFetching ? "animate-spin" : ""}`} />
                {labels.market.loadPrice}
              </button>
            </div>
          </div>

          {allSymbols.isLoading ? (
            <div className="text-slate-500 py-4">{labels.common.loading}</div>
          ) : pageSymbols.length > 0 ? (
            <div className="overflow-x-auto scrollbar-thin">
              <table className="table-fintech">
                <thead>
                  <tr>
                    <th className="text-left">
                      {labels.market.symbol}
                      <InfoTooltip content={labels.tooltips.assetSymbol} />
                    </th>
                    <th className="text-left">
                      {labels.assets.name}
                      <InfoTooltip content={labels.tooltips.assetName} />
                    </th>
                    <th className="text-left">
                      {labels.market.exchange}
                      <InfoTooltip content={labels.tooltips.assetExchange} />
                    </th>
                    <th className="text-right">
                      {labels.market.price}
                      <InfoTooltip content={labels.tooltips.transactionPrice} />
                    </th>
                    <th className="text-right">
                      {labels.market.change}
                      <InfoTooltip content={labels.tooltips.marketWatchlist} />
                    </th>
                    <th className="text-right">
                      {labels.market.marketChangePercent}
                      <InfoTooltip content={labels.tooltips.marketWatchlist} />
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {pageSymbols.map((item) => {
                    const q = quoteMap[item.symbol];
                    return (
                      <tr
                        key={item.symbol}
                        onClick={() => setSelectedSymbol(item)}
                        className="cursor-pointer hover:bg-slate-50 transition-colors"
                      >
                        <td className="font-display font-semibold text-slate-900">{item.symbol}</td>
                        <td className="text-sm text-slate-500 max-w-xs truncate">{item.name}</td>
                        <td className="text-xs text-slate-500">{item.exchange}</td>
                        <td className="text-right font-mono">{q ? formatCurrency(q.price) : "—"}</td>
                        <td
                          className={`text-right font-mono ${q && q.change >= 0
                            ? "text-accent-emerald"
                            : q && q.change < 0
                              ? "text-accent-rose"
                              : ""
                            }`}
                        >
                          {q ? formatCurrency(q.change) : "—"}
                        </td>
                        <td className="text-right">{q ? <TrendBadge value={q.change_percent} /> : "—"}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-slate-500 py-4">{labels.common.noData}</div>
          )}

          {totalPages > 1 && (
            <div className="flex items-center justify-between mt-4">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="btn-secondary disabled:opacity-50"
              >
                {labels.market.previous}
              </button>
              <span className="text-sm text-slate-500">
                {labels.market.page} {page} / {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="btn-secondary disabled:opacity-50"
              >
                {labels.market.next}
              </button>
            </div>
          )}
        </FintechCard>
      )}

      {goldFx.data && (
        <FintechCard delay={0.4}>
          <div className="flex items-center justify-between mb-4">
            <h3 className="card-title inline-flex items-center">
              {labels.market.goldFx}
              <InfoTooltip content={labels.tooltips.settingsGoldFx} />
            </h3>
            <button
              onClick={() => goldFx.refetch()}
              className="btn-secondary"
            >
              <RefreshCw className={`w-4 h-4 ${goldFx.isFetching ? "animate-spin" : ""}`} />
              {labels.settings.refresh}
            </button>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div>
              <h4 className="font-display font-semibold text-slate-900 mb-3">{labels.settings.gold}</h4>
              <div className="overflow-x-auto scrollbar-thin">
                <table className="table-fintech">
                  <thead>
                    <tr>
                      <th>
                        {labels.settings.source}
                        <InfoTooltip content={labels.tooltips.sourceDefault} />
                      </th>
                      <th className="text-right">
                        {labels.settings.buy}
                        <InfoTooltip content={labels.tooltips.settingsGoldFx} />
                      </th>
                      <th className="text-right">
                        {labels.settings.sell}
                        <InfoTooltip content={labels.tooltips.settingsGoldFx} />
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {goldFx.data.gold?.map((item: any, idx: number) => (
                      <tr key={idx}>
                        <td className="font-medium text-slate-900">{item.source}</td>
                        <td className="text-right font-mono">{formatCurrency(item.buy)}</td>
                        <td className="text-right font-mono">{formatCurrency(item.sell)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
            <div>
              <h4 className="font-display font-semibold text-slate-900 mb-3">{labels.settings.fx}</h4>
              <div className="overflow-x-auto scrollbar-thin">
                <table className="table-fintech">
                  <thead>
                    <tr>
                      <th>
                        {labels.settings.currency}
                        <InfoTooltip content={labels.tooltips.assetCurrency} />
                      </th>
                      <th className="text-right">
                        {labels.settings.buy}
                        <InfoTooltip content={labels.tooltips.settingsGoldFx} />
                      </th>
                      <th className="text-right">
                        {labels.settings.transfer}
                        <InfoTooltip content={labels.tooltips.settingsGoldFx} />
                      </th>
                      <th className="text-right">
                        {labels.settings.sell}
                        <InfoTooltip content={labels.tooltips.settingsGoldFx} />
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {goldFx.data.fx?.slice(0, 10).map((item: any, idx: number) => (
                      <tr key={idx}>
                        <td className="font-medium text-slate-900">{item.currency}</td>
                        <td className="text-right font-mono">{formatCurrency(item.buy)}</td>
                        <td className="text-right font-mono">{formatCurrency(item.transfer)}</td>
                        <td className="text-right font-mono">{formatCurrency(item.sell)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </FintechCard>
      )}

      {selectedSymbol && (
        <SymbolDetailModal
          symbol={selectedSymbol.symbol}
          name={selectedSymbol.name}
          type={selectedSymbol.type}
          exchange={selectedSymbol.exchange}
          onClose={() => setSelectedSymbol(null)}
        />
      )}
    </div>
  );
}
