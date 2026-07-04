import {
  Area,
  AreaChart,
  ResponsiveContainer,
  Tooltip,
  YAxis,
} from "recharts";

interface MiniSparklineProps {
  data: number[];
  width?: number;
  height?: number;
  color?: "emerald" | "rose" | "cyan" | "blue" | "amber" | "violet";
  showArea?: boolean;
}

const colorMap = {
  emerald: { stroke: "#34D399", fill: "rgba(52, 211, 153, 0.15)" },
  rose: { stroke: "#FB7185", fill: "rgba(251, 113, 133, 0.15)" },
  cyan: { stroke: "#22D3EE", fill: "rgba(34, 211, 238, 0.15)" },
  blue: { stroke: "#3B82F6", fill: "rgba(59, 130, 246, 0.15)" },
  amber: { stroke: "#FBBF24", fill: "rgba(251, 191, 36, 0.15)" },
  violet: { stroke: "#A78BFA", fill: "rgba(167, 139, 250, 0.15)" },
};

export function MiniSparkline({
  data,
  width = 120,
  height = 40,
  color = "cyan",
  showArea = true,
}: MiniSparklineProps) {
  const chartData = data.map((value, i) => ({ i, value }));
  const colors = colorMap[color];

  if (data.length < 2) {
    return (
      <div
        style={{ width, height }}
        className="flex items-center justify-center text-xs text-slate-400"
      >
        -
      </div>
    );
  }

  return (
    <div style={{ width, height }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chartData}>
          <defs>
            <linearGradient id={`spark-${color}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={colors.stroke} stopOpacity={0.35} />
              <stop offset="100%" stopColor={colors.stroke} stopOpacity={0} />
            </linearGradient>
          </defs>
          <YAxis domain={["dataMin", "dataMax"]} hide />
          <Tooltip
            content={({ active, payload }) => {
              if (active && payload?.length) {
                return (
                  <div className="rounded-lg border border-fintech-border bg-white/90 px-2 py-1 text-xs text-slate-800 backdrop-blur-md">
                    {payload[0].value?.toLocaleString("vi-VN")}
                  </div>
                );
              }
              return null;
            }}
          />
          <Area
            type="monotone"
            dataKey="value"
            stroke={colors.stroke}
            strokeWidth={2}
            fill={showArea ? `url(#spark-${color})` : "transparent"}
            dot={false}
            activeDot={{ r: 3, strokeWidth: 0, fill: colors.stroke }}
            animationDuration={1200}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
