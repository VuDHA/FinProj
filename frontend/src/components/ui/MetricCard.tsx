import { FintechCard } from "./FintechCard";
import { AnimatedNumber } from "./AnimatedNumber";
import { InfoTooltip } from "../InfoTooltip";
import type { ReactNode } from "react";

interface MetricCardProps {
  label: ReactNode;
  tooltip?: string;
  value: number | string;
  formatter?: (n: number) => string;
  valueClassName?: string;
  delay?: number;
  children?: ReactNode;
}

export function MetricCard({
  label,
  tooltip,
  value,
  formatter,
  valueClassName = "",
  delay,
  children,
}: MetricCardProps) {
  return (
    <FintechCard
      delay={delay}
      className="min-w-0 group hover:scale-125 hover:z-50 transition-transform duration-200 will-change-transform"
    >
      <div className="space-y-1 min-w-0 overflow-hidden group-hover:overflow-visible">
        <div className="card-title mb-1 inline-flex items-center">
          {label}
          {tooltip && <InfoTooltip content={tooltip} />}
        </div>
        <div className={`metric-value group-hover:overflow-visible ${valueClassName}`}>
          {typeof value === "number" && formatter ? (
            <AnimatedNumber
              value={value}
              formatter={formatter}
              duration={1000}
              className="block truncate group-hover:overflow-visible group-hover:text-clip"
            />
          ) : (
            <span className="block truncate group-hover:overflow-visible group-hover:text-clip">
              {value}
            </span>
          )}
        </div>
        {children}
      </div>
    </FintechCard>
  );
}
