import { TrendingDown, TrendingUp } from "lucide-react";
import { formatPercent } from "../../lib/utils";

interface TrendBadgeProps {
  value: number;
  className?: string;
  showIcon?: boolean;
}

export function TrendBadge({ value, className = "", showIcon = true }: TrendBadgeProps) {
  const positive = value >= 0;
  return (
    <span className={`inline-flex items-center gap-1 ${positive ? "badge-gain" : "badge-loss"} ${className}`}>
      {showIcon &&
        (positive ? (
          <TrendingUp className="w-3 h-3" />
        ) : (
          <TrendingDown className="w-3 h-3" />
        ))}
      {formatPercent(value)}
    </span>
  );
}
