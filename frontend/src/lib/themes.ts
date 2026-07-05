export type ThemeKey =
  | "clean-slate"
  | "command-center"
  | "eco-logistics"
  | "high-contrast"
  | "espresso-cream"
  | "sky-blue";

export interface Theme {
  key: ThemeKey;
  name: string;
  description: string;
  chartColors: string[];
}

export const DEFAULT_THEME: ThemeKey = "clean-slate";
export const THEME_STORAGE_KEY = "wealth-theme";

export const THEMES: Theme[] = [
  {
    key: "clean-slate",
    name: "Clean Slate",
    description: "Giao diện mặc định hiện tại — sáng, hiện đại, xanh dương tím.",
    chartColors: ["#3B82F6", "#8B5CF6", "#22D3EE", "#34D399", "#FB7185", "#FBBF24"],
  },
  {
    key: "command-center",
    name: "Command Center",
    description: "Phong cách trung tâm điều khiển — tối, cao tương phản, xanh cyan.",
    chartColors: ["#2DD4BF", "#00F0FF", "#A78BFA", "#34D399", "#F87171", "#FBBF24"],
  },
  {
    key: "eco-logistics",
    name: "Eco-Logistics",
    description: "Phong cách sinh thái — xanh lá, tự nhiên, năng động.",
    chartColors: ["#10B981", "#84CC16", "#22C55E", "#2DD4BF", "#F97316", "#EAB308"],
  },
  {
    key: "high-contrast",
    name: "High-Contrast Analytics",
    description: "Phân tích độ tương phản cao — đen trắng, màu sắc rõ ràng.",
    chartColors: ["#2563EB", "#7C3AED", "#0891B2", "#059669", "#DC2626", "#D97706"],
  },
  {
    key: "espresso-cream",
    name: "Espresso & Cream",
    description: "Phong cách cà phê sữa — ấm áp, kem nâu, tinh tế.",
    chartColors: ["#92400E", "#D97706", "#C2410C", "#65A30D", "#B91C1C", "#F59E0B"],
  },
  {
    key: "sky-blue",
    name: "Sky Blue",
    description: "Phong cách trời xanh — nhẹ nhàng, tươi sáng, dễ chịu.",
    chartColors: ["#0EA5E9", "#2563EB", "#6366F1", "#14B8A6", "#F43F5E", "#F59E0B"],
  },
];

export const THEME_KEYS = THEMES.map((t) => t.key);

export function getThemeByKey(key: string): Theme | undefined {
  return THEMES.find((t) => t.key === key);
}

export function isValidThemeKey(key: string): key is ThemeKey {
  return THEME_KEYS.includes(key as ThemeKey);
}
