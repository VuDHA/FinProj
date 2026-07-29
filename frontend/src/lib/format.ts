/**
 * Intl-based Vietnamese formatting utilities.
 * All functions handle null/undefined gracefully by returning "—".
 */

const viNumberFormat = new Intl.NumberFormat("vi-VN");
const viCurrencyFormat = new Intl.NumberFormat("vi-VN", {
  style: "currency",
  currency: "VND",
  maximumFractionDigits: 0,
});
const viDateFormat = new Intl.DateTimeFormat("vi-VN", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
});
const viDateTimeFormat = new Intl.DateTimeFormat("vi-VN", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

const EMPTY = "—";

/**
 * Format a number as Vietnamese Đồng (VND) currency.
 * Returns "—" for null/undefined/NaN.
 */
export function formatCurrency(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return EMPTY;
  }
  return viCurrencyFormat.format(value);
}

/**
 * Format a number with Vietnamese locale grouping.
 * Optionally specify the number of decimal places.
 * Returns "—" for null/undefined/NaN.
 */
export function formatNumber(
  value: number | null | undefined,
  decimals?: number
): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return EMPTY;
  }
  if (decimals !== undefined) {
    return new Intl.NumberFormat("vi-VN", {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    }).format(value);
  }
  return viNumberFormat.format(value);
}

/**
 * Format a date (string or Date) as dd/MM/yyyy (Vietnamese locale).
 * Returns "—" for null/undefined/invalid dates.
 */
export function formatDate(date: string | Date | null | undefined): string {
  if (date === null || date === undefined) {
    return EMPTY;
  }
  const parsed = date instanceof Date ? date : new Date(date);
  if (Number.isNaN(parsed.getTime())) {
    return EMPTY;
  }
  return viDateFormat.format(parsed);
}

/**
 * Format a date (string or Date) as dd/MM/yyyy HH:mm (Vietnamese locale).
 * Returns "—" for null/undefined/invalid dates.
 */
export function formatDateTime(date: string | Date | null | undefined): string {
  if (date === null || date === undefined) {
    return EMPTY;
  }
  const parsed = date instanceof Date ? date : new Date(date);
  if (Number.isNaN(parsed.getTime())) {
    return EMPTY;
  }
  return viDateTimeFormat.format(parsed);
}

/**
 * Format a value as a percentage with Vietnamese locale.
 * The value is assumed to already be in percent (e.g. 12.5 => "12,5%").
 * Optionally specify the number of decimal places (default 2).
 * Returns "—" for null/undefined/NaN.
 */
export function formatPercent(
  value: number | null | undefined,
  decimals: number = 2
): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return EMPTY;
  }
  return (
    new Intl.NumberFormat("vi-VN", {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    }).format(value) + "%"
  );
}
