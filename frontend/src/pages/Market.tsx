import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { Bot, RefreshCw } from "lucide-react";
import { usePersistentState } from "../hooks/usePersistentState";
import API from "../api/client";
import { getMarketInsight } from "../api/ai";
import { AiGenerateButton } from "../components/AiGenerateButton";
import { AiInsightCard } from "../components/AiInsightCard";
import { ErrorMessage } from "../components/ErrorMessage";
import { FormattedNumberInput } from "../components/FormattedNumberInput";
import { InfoTooltip } from "../components/InfoTooltip";
import SymbolDetailModal from "../components/SymbolDetailModal";
import { FintechCard } from "../components/ui/FintechCard";
import { SectionHeader } from "../components/ui/SectionHeader";
import { TrendBadge } from "../components/ui/TrendBadge";
import { useAiInsight } from "../hooks/useAiInsight";
import { labels } from "../i18n/vi";
import { formatCurrency, formatNumber } from "../lib/utils";


export function Market() {
  const WATCHLIST_SYMBOLS =
    "VCB,VHM,VIC,FPT,GAS,HPG,MBB,MSN,MWG,PLX,SSI,TCB,VIB,VPB,E1VFVN30,FUEVFVND,FUESSVFL";

  const [activeTab, setActiveTab] = usePersistentState<"STOCK" | "FUND">("market.activeTab", "STOCK");
  const [search, setSearch] = usePersistentState("market.search", "");
  const [fundType, setFundType] = usePersistentState("market.fundType", "all");
  const [exchangeFilter, setExchangeFilter] = usePersistentState("market.exchangeFilter", "all");
  const [changeFilter, setChangeFilter] = usePersistentState("market.changeFilter", "all");
  const [minPrice, setMinPrice] = usePersistentState("market.minPrice", "");
  const [maxPrice, setMaxPrice] = usePersistentState("market.maxPrice", "");
  const [sortBy, setSortBy] = usePersistentState("market.sortBy", "symbol");
  const [page, setPage] = usePersistentState("market.page", 1);
  const [selectedSymbol, setSelectedSymbol] = usePersistentState<{
    symbol: string;
    name: string;
    type: string;
    exchange: string;
  } | null>("market.selectedSymbol", null);
  const PAGE_SIZE = 20;

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
      return data as Array<{ symbol: string; name: string; exchange: string; type: string; fund_type?: string }>;
    },
  });

  const fundTypes = useMemo(() => {
    const types = new Set<string>();
    allSymbols.data?.forEach((item) => {
      if (item.type === "FUND" && item.fund_type) {
        types.add(item.fund_type);
      }
    });
    return Array.from(types).sort();
  }, [allSymbols.data]);

  const exchanges = useMemo(() => {
    const exs = new Set<string>();
    allSymbols.data?.forEach((item) => {
      if (item.type === activeTab && item.exchange) {
        exs.add(item.exchange);
      }
    });
    return Array.from(exs).sort();
  }, [allSymbols.data, activeTab]);

  const filteredSymbols =
    allSymbols.data?.filter((item) => {
      if (item.type !== activeTab) return false;
      if (activeTab === "FUND" && fundType && fundType !== "all" && item.fund_type !== fundType) {
        return false;
      }
      if (exchangeFilter && exchangeFilter !== "all" && item.exchange !== exchangeFilter) {
        return false;
      }
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

  const quotesReady = !!pageQuotes.data;

  const displaySymbols = useMemo(() => {
    const min = parseFloat(minPrice);
    const max = parseFloat(maxPrice);
    const filterByPrice = !isNaN(min) || !isNaN(max);
    const filterByChange = changeFilter !== "all";

    let list = [...pageSymbols];

    if (quotesReady && (filterByPrice || filterByChange)) {
      list = list.filter((item) => {
        const q = quoteMap[item.symbol];
        if (!q) return false;
        if (filterByChange) {
          if (changeFilter === "up" && q.change_percent <= 0) return false;
          if (changeFilter === "down" && q.change_percent >= 0) return false;
        }
        if (!isNaN(min) && q.price < min) return false;
        if (!isNaN(max) && q.price > max) return false;
        return true;
      });
    }

    if (sortBy === "changePercent") {
      list.sort((a, b) => {
        const ca = quoteMap[a.symbol]?.change_percent ?? -Infinity;
        const cb = quoteMap[b.symbol]?.change_percent ?? -Infinity;
        if (cb !== ca) return cb - ca;
        return a.symbol.localeCompare(b.symbol);
      });
    } else if (sortBy === "name") {
      list.sort((a, b) => a.name.localeCompare(b.name));
    } else if (sortBy === "exchange") {
      list.sort((a, b) => a.exchange.localeCompare(b.exchange) || a.symbol.localeCompare(b.symbol));
    } else {
      list.sort((a, b) => a.symbol.localeCompare(b.symbol));
    }
    return list;
  }, [pageSymbols, sortBy, quoteMap, changeFilter, minPrice, maxPrice, quotesReady]);

  const portfolio = useQuery({
    queryKey: ["portfolio"],
    queryFn: async () => (await API.get("/portfolio/")).data,
  });

  const stockFundItems =
    portfolio.data?.items?.filter((item: any) => ["STOCK", "FUND", "ETF"].includes(item.type)) || [];
  const stockFundTotal = stockFundItems.reduce((sum: number, item: any) => sum + (item.current_value || 0), 0);

  const marketInsight = useAiInsight({
    taskName: "market_insight",
    fetcher: getMarketInsight,
  });

  const hasActiveFilters =
    search.trim() !== "" ||
    fundType !== "all" ||
    exchangeFilter !== "all" ||
    changeFilter !== "all" ||
    minPrice !== "" ||
    maxPrice !== "" ||
    sortBy !== "symbol";

  const clearFilters = () => {
    setSearch("");
    setFundType("all");
    setExchangeFilter("all");
    setChangeFilter("all");
    setMinPrice("");
    setMaxPrice("");
    setSortBy("symbol");
    setPage(1);
  };

  return (
    <div className="space-y-6">
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
          <span className="value-text text-sm text-slate-600 min-w-0" title={portfolio.isLoading ? "" : formatCurrency(stockFundTotal)}>
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
                    <td className="value-cell" title={formatNumber(item.quantity, 4)}>{formatNumber(item.quantity, 4)}</td>
                    <td className="value-cell" title={formatCurrency(item.latest_price)}>{formatCurrency(item.latest_price)}</td>
                    <td className="value-cell text-slate-900" title={formatCurrency(item.current_value)}>{formatCurrency(item.current_value)}</td>
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

      <FintechCard delay={0.08}>
        <div className="flex items-center justify-between mb-3">
          <h3 className="card-title inline-flex items-center gap-2">
            <Bot className="w-4 h-4 text-indigo-500" />
            Phân tích AI thị trường
          </h3>
          <AiGenerateButton
            label="Phân tích"
            onClick={() => marketInsight.generate()}
            loading={marketInsight.loading}
          />
        </div>
        <AiInsightCard
          data={marketInsight.data}
          loading={marketInsight.loading}
          error={marketInsight.error}
          onClose={marketInsight.clear}
        />
      </FintechCard>

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
                    setFundType("all");
                    setExchangeFilter("all");
                    setChangeFilter("all");
                    setMinPrice("");
                    setMaxPrice("");
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
            {exchanges.length > 0 && (
              <select
                className="input-fintech md:w-44"
                value={exchangeFilter}
                onChange={(e) => {
                  setExchangeFilter(e.target.value);
                  setPage(1);
                }}
              >
                <option value="all">{labels.market.allExchanges}</option>
                {exchanges.map((ex) => (
                  <option key={ex} value={ex}>
                    {ex}
                  </option>
                ))}
              </select>
            )}
            {activeTab === "FUND" && fundTypes.length > 0 && (
              <select
                className="input-fintech md:w-56"
                value={fundType}
                onChange={(e) => {
                  setFundType(e.target.value);
                  setPage(1);
                }}
              >
                <option value="all">{labels.market.allFundTypes}</option>
                {fundTypes.map((type) => (
                  <option key={type} value={type}>
                    {type}
                  </option>
                ))}
              </select>
            )}
            <select
              className="input-fintech md:w-48"
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
            >
              <option value="symbol">{labels.market.sortBySymbol}</option>
              <option value="name">{labels.market.sortByName}</option>
              <option value="exchange">{labels.market.sortByExchange}</option>
              <option value="changePercent">{labels.market.sortByChangePercent}</option>
            </select>
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
              {hasActiveFilters && (
                <button
                  onClick={clearFilters}
                  className="btn-secondary text-slate-600"
                >
                  {labels.market.clearFilters}
                </button>
              )}
            </div>
          </div>

          <div className="flex flex-col md:flex-row gap-3 mb-4">
            <select
              className="input-fintech md:w-48"
              value={changeFilter}
              onChange={(e) => setChangeFilter(e.target.value)}
              disabled={!quotesReady}
            >
              <option value="all">{labels.market.allChanges}</option>
              <option value="up">{labels.market.gainers}</option>
              <option value="down">{labels.market.losers}</option>
            </select>
            <FormattedNumberInput
              mode="currency"
              decimals={0}
              min={0}
              className="input-fintech md:w-48"
              placeholder={labels.market.minPrice}
              value={minPrice}
              onChange={(value) => {
                setMinPrice(value);
                setPage(1);
              }}
              disabled={!quotesReady}
            />
            <FormattedNumberInput
              mode="currency"
              decimals={0}
              min={0}
              className="input-fintech md:w-48"
              placeholder={labels.market.maxPrice}
              value={maxPrice}
              onChange={(value) => {
                setMaxPrice(value);
                setPage(1);
              }}
              disabled={!quotesReady}
            />
            <span className="text-xs text-slate-500 self-center">
              {labels.market.priceRangeHint}
            </span>
          </div>

          {allSymbols.isLoading ? (
            <div className="text-slate-500 py-4">{labels.common.loading}</div>
          ) : displaySymbols.length > 0 ? (
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
                  {displaySymbols.map((item) => {
                    const q = quoteMap[item.symbol];
                    return (
                      <tr
                        key={item.symbol}
                        onClick={() => setSelectedSymbol(item)}
                        className="cursor-pointer hover:bg-slate-50 transition-colors"
                      >
                        <td className="font-display font-semibold text-slate-900 whitespace-nowrap">{item.symbol}</td>
                        <td className="text-sm text-slate-500 max-w-[120px] md:max-w-xs truncate">{item.name}</td>
                        <td className="text-xs text-slate-500 whitespace-nowrap">{item.exchange}</td>
                        <td className="value-cell" title={q ? formatCurrency(q.price) : ""}>{q ? formatCurrency(q.price) : "—"}</td>
                        <td
                          className={`value-cell ${q && q.change >= 0
                            ? "text-accent-emerald"
                            : q && q.change < 0
                              ? "text-accent-rose"
                              : ""
                            }`}
                          title={q ? formatCurrency(q.change) : ""}
                        >
                          {q ? formatCurrency(q.change) : "—"}
                        </td>
                        <td className="text-right whitespace-nowrap">{q ? <TrendBadge value={q.change_percent} /> : "—"}</td>
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
                        <td className="font-medium text-slate-900 whitespace-nowrap">{item.source}</td>
                        <td className="value-cell" title={formatCurrency(item.buy)}>{formatCurrency(item.buy)}</td>
                        <td className="value-cell" title={formatCurrency(item.sell)}>{formatCurrency(item.sell)}</td>
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
                        <td className="font-medium text-slate-900 whitespace-nowrap">{item.currency}</td>
                        <td className="value-cell" title={formatCurrency(item.buy)}>{formatCurrency(item.buy)}</td>
                        <td className="value-cell" title={formatCurrency(item.transfer)}>{formatCurrency(item.transfer)}</td>
                        <td className="value-cell" title={formatCurrency(item.sell)}>{formatCurrency(item.sell)}</td>
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
