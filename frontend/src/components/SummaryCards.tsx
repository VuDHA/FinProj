import {
  Landmark,
  PiggyBank,
  TrendingDown,
  TrendingUp,
  Wallet,
} from "lucide-react";
import { AnimatedNumber } from "./ui/AnimatedNumber";
import { FintechCard } from "./ui/FintechCard";
import { InfoTooltip } from "./InfoTooltip";
import { MiniSparkline } from "./ui/MiniSparkline";
import { TrendBadge } from "./ui/TrendBadge";
import { formatCurrency } from "../lib/utils";
import { labels } from "../i18n/vi";

function generateSparkline(base: number, points = 20, trend: "up" | "down" | "neutral" = "neutral") {
  const data: number[] = [];
  let current = base * 0.85;
  const multiplier = trend === "up" ? 1.015 : trend === "down" ? 0.985 : 1.0;
  for (let i = 0; i < points; i++) {
    const noise = (Math.random() - 0.48) * base * 0.04;
    current = current * multiplier + noise;
    data.push(Math.max(current, base * 0.1));
  }
  data[data.length - 1] = base;
  return data;
}

export function SummaryCards({
  total_value,
  total_cost,
  total_pnl,
  total_pnl_percent,
  stable_value,
  history,
}: {
  total_value: number;
  total_cost: number;
  total_pnl: number;
  total_pnl_percent: number;
  stable_value?: number;
  history?: Array<{ date: string; value: number; cost: number }>;
}) {
  const valueSparkline = history?.length
    ? history.map((h) => h.value)
    : generateSparkline(total_value, 24, "up");
  const costSparkline = history?.length
    ? history.map((h) => h.cost)
    : generateSparkline(total_cost, 24, "neutral");
  const pnlSparkline = history?.length
    ? history.map((h) => h.value - h.cost)
    : generateSparkline(Math.abs(total_pnl) || 1, 24, total_pnl >= 0 ? "up" : "down");

  const cards = [
    {
      label: labels.summary.totalValue,
      tooltip: labels.tooltips.totalValue,
      value: total_value,
      formatter: formatCurrency,
      icon: Wallet,
      color: "cyan" as const,
      trend: "up" as const,
      sparkline: valueSparkline,
      badge: total_pnl_percent,
    },
    {
      label: labels.summary.totalCost,
      tooltip: labels.tooltips.totalCost,
      value: total_cost,
      formatter: formatCurrency,
      icon: PiggyBank,
      color: "blue" as const,
      trend: "neutral" as const,
      sparkline: costSparkline,
    },
    {
      label: labels.summary.pnl,
      tooltip: labels.tooltips.pnl,
      value: total_pnl,
      formatter: formatCurrency,
      icon: total_pnl >= 0 ? TrendingUp : TrendingDown,
      color: total_pnl >= 0 ? ("emerald" as const) : ("rose" as const),
      trend: total_pnl >= 0 ? ("up" as const) : ("down" as const),
      sparkline: pnlSparkline,
      badge: total_pnl_percent,
    },
    ...(stable_value && stable_value > 0
      ? [
        {
          label: labels.summary.stableValue,
          tooltip: labels.tooltips.stableValue,
          value: stable_value,
          formatter: formatCurrency,
          icon: Landmark,
          color: "violet" as const,
          trend: "neutral" as const,
          sparkline: generateSparkline(stable_value, 24, "neutral"),
        },
      ]
      : []),
  ];

  const iconTone = {
    cyan: "bg-accent-cyan/10 text-accent-cyan ring-accent-cyan/20",
    blue: "bg-accent-blue/10 text-accent-blue ring-accent-blue/20",
    emerald: "bg-accent-emerald/10 text-accent-emerald ring-accent-emerald/20",
    rose: "bg-accent-rose/10 text-accent-rose ring-accent-rose/20",
    violet: "bg-accent-violet/10 text-accent-violet ring-accent-violet/20",
  };

  const gridCols = cards.length > 3 ? "md:grid-cols-4" : "md:grid-cols-3";

  return (
    <div className={`grid grid-cols-1 ${gridCols} gap-4`}>
      {cards.map((card, i) => {
        const Icon = card.icon;
        return (
          <FintechCard key={card.label} delay={i * 0.08} className="min-w-0 group hover:scale-125 hover:z-50 transition-transform duration-200 will-change-transform">
            <div className="flex items-start justify-between">
              <div className="space-y-1 min-w-0 overflow-hidden group-hover:overflow-visible">
                <span className="card-title inline-flex items-center">
                  {card.label}
                  <InfoTooltip content={card.tooltip} position="right" />
                </span>
                <div className="metric-value group-hover:overflow-visible">
                  <AnimatedNumber
                    value={card.value}
                    formatter={card.formatter}
                    duration={1400 + i * 200}
                    className="block truncate group-hover:overflow-visible group-hover:text-clip"
                  />
                </div>
                {card.badge !== undefined && (
                  <div className="pt-1">
                    <TrendBadge value={card.badge} />
                  </div>
                )}
              </div>
              <div className="flex flex-col items-end gap-3">
                <div
                  className={`p-2.5 rounded-xl ring-1 ring-inset ${iconTone[card.color]}`}
                >
                  <Icon className="w-5 h-5" />
                </div>
                <MiniSparkline
                  data={card.sparkline}
                  color={card.color}
                  width={110}
                  height={36}
                />
              </div>
            </div>
          </FintechCard>
        );
      })}
    </div>
  );
}
