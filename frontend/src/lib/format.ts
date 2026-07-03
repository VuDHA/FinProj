export function formatCurrency(
  n: number,
  currency: string = "VND",
  maximumFractionDigits: number = 2,
): string {
  return new Intl.NumberFormat("vi-VN", {
    style: "currency",
    currency,
    maximumFractionDigits,
  }).format(n);
}

export function formatNumber(n: number, fractionDigits: number = 2): string {
  return new Intl.NumberFormat("vi-VN", {
    maximumFractionDigits: fractionDigits,
  }).format(n);
}

export function formatPercent(n: number, fractionDigits: number = 2): string {
  return `${n >= 0 ? "+" : ""}${n.toFixed(fractionDigits)}%`;
}
