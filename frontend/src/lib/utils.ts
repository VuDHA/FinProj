import { formatCurrency, formatNumber, formatPercent } from "../i18n/vi";

export { formatCurrency, formatNumber, formatPercent };

export const chartTooltipStyle = {
    background: "var(--surface-elevated)",
    border: "1px solid var(--fintech-border)",
    borderRadius: "12px",
    color: "var(--text-primary)",
};

export const DEFAULT_DATE_FORMAT = "dd/mm/yyyy";
export const DATE_FORMAT_OPTIONS = ["dd/mm/yyyy", "mm/dd/yyyy", "yyyy-mm-dd", "dd-mm-yyyy"];

/**
 * Format an ISO date string (YYYY-MM-DD) according to the given format token.
 * Supported tokens: dd/mm/yyyy, mm/dd/yyyy, yyyy-mm-dd, dd-mm-yyyy.
 * Falls back to the raw value when parsing fails so the UI never breaks.
 */
export function formatDate(iso: string | null | undefined, fmt: string = DEFAULT_DATE_FORMAT): string {
  if (!iso) return "";
  const parts = iso.split("T")[0].split("-");
  if (parts.length !== 3) return iso;
  const [y, m, d] = parts;
  switch (fmt) {
    case "mm/dd/yyyy": return `${m}/${d}/${y}`;
    case "yyyy-mm-dd": return `${y}-${m}-${d}`;
    case "dd-mm-yyyy": return `${d}-${m}-${y}`;
    case "dd/mm/yyyy":
    default: return `${d}/${m}/${y}`;
  }
}

/**
 * Short (day/month) label derived from the configured format, used for chart
 * axis labels where the year would be redundant.
 */
export function formatDateShort(iso: string | null | undefined, fmt: string = DEFAULT_DATE_FORMAT): string {
  if (!iso) return "";
  const parts = iso.split("T")[0].split("-");
  if (parts.length !== 3) return iso;
  const [, m, d] = parts;
  switch (fmt) {
    case "mm/dd/yyyy": return `${m}/${d}`;
    case "dd-mm-yyyy": return `${d}-${m}`;
    case "dd/mm/yyyy":
    default: return `${d}/${m}`;
  }
}
