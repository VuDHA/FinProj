import {
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
}: {
  total_value: number;
  total_cost: number;
  total_pnl: number;
  total_pnl_percent: number;
}) {
  const cards = [
    {
      label: labels.summary.totalValue,
      tooltip: labels.tooltips.totalValue,
      value: total_value,
      formatter: formatCurrency,
      icon: Wallet,
      color: "cyan" as const,
      trend: "up" as const,
      sparkline: generateSparkline(total_value, 24, "up"),
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
      sparkline: generateSparkline(total_cost, 24, "neutral"),
    },
    {
      label: labels.summary.pnl,
      tooltip: labels.tooltips.pnl,
      value: total_pnl,
      formatter: formatCurrency,
      icon: total_pnl >= 0 ? TrendingUp : TrendingDown,
      color: total_pnl >= 0 ? ("emerald" as const) : ("rose" as const),
      trend: total_pnl >= 0 ? ("up" as const) : ("down" as const),
      sparkline: generateSparkline(Math.abs(total_pnl) || 1, 24, total_pnl >= 0 ? "up" : "down"),
      badge: total_pnl_percent,
    },
  ];

  const iconTone = {
    cyan: "bg-accent-cyan/10 text-accent-cyan ring-accent-cyan/20",
    blue: "bg-accent-blue/10 text-accent-blue ring-accent-blue/20",
    emerald: "bg-accent-emerald/10 text-accent-emerald ring-accent-emerald/20",
    rose: "bg-accent-rose/10 text-accent-rose ring-accent-rose/20",
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {cards.map((card, i) => {
        const Icon = card.icon;
        return (
          <FintechCard key={card.label} delay={i * 0.08}>
            <div className="flex items-start justify-between">
              <div className="space-y-1">
                <span className="card-title inline-flex items-center">
                  {card.label}
                  <InfoTooltip content={card.tooltip} position="right" />
                </span>
                <div className="metric-value">
                  <AnimatedNumber
                    value={card.value}
                    formatter={card.formatter}
                    duration={1400 + i * 200}
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
