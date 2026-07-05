import React, { useEffect, useRef, useState } from "react";

interface FormattedNumberInputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "onChange" | "type" | "value" | "inputMode"> {
  value: string | number;
  onChange: (value: string) => void;
  mode?: "currency" | "percent" | "number";
  decimals?: number;
  placeholder?: string;
}

function parseRawValue(value: string, _mode: "currency" | "percent" | "number", decimals: number): string {
  const cleaned = value.replace(/,/g, "").replace(/%/g, "");
  const regex = new RegExp(`^\\d*\\.?\\d{0,${decimals}}$`);
  const match = cleaned.match(regex);
  return match ? match[0] : cleaned.replace(/[^\d.]/g, "").replace(/\.(?=.*\.)/g, "");
}

function formatDisplayValue(rawValue: string, mode: "currency" | "percent" | "number", decimals: number): string {
  if (rawValue === "" || rawValue === undefined || rawValue === null) return "";
  const hasTrailingDot = rawValue.endsWith(".");
  const numeric = parseFloat(rawValue);
  if (Number.isNaN(numeric)) return "";
  const formatted = new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 0,
    maximumFractionDigits: decimals,
  }).format(numeric);
  if (mode === "percent") {
    return hasTrailingDot ? `${formatted}.%` : `${formatted}%`;
  }
  return hasTrailingDot ? `${formatted}.` : formatted;
}

function countRealChars(value: string): number {
  return (value.match(/[\d.]/g) || []).length;
}

function restoreCursorPosition(formatted: string, realCharsBefore: number): number {
  let counted = 0;
  for (let i = 0; i < formatted.length; i++) {
    if (/[\d.]/.test(formatted[i])) {
      counted++;
    }
    if (counted >= realCharsBefore) {
      return i + 1;
    }
  }
  return formatted.length;
}

export function FormattedNumberInput({
  value,
  onChange,
  mode = "number",
  decimals = 2,
  placeholder,
  className,
  ...props
}: FormattedNumberInputProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [displayValue, setDisplayValue] = useState(() =>
    formatDisplayValue(String(value ?? ""), mode, decimals)
  );

  useEffect(() => {
    setDisplayValue(formatDisplayValue(String(value ?? ""), mode, decimals));
  }, [value, mode, decimals]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const input = e.target;
    const raw = input.value;
    const selectionStart = input.selectionStart || 0;
    const realCharsBefore = countRealChars(raw.slice(0, selectionStart));

    const parsed = parseRawValue(raw, mode, decimals);
    const formatted = formatDisplayValue(parsed, mode, decimals);
    const newCursor = restoreCursorPosition(formatted, realCharsBefore);

    setDisplayValue(formatted);
    onChange(parsed);

    requestAnimationFrame(() => {
      const el = inputRef.current;
      if (el) {
        el.setSelectionRange(newCursor, newCursor);
      }
    });
  };

  return (
    <input
      ref={inputRef}
      type="text"
      inputMode={mode === "percent" ? "decimal" : "numeric"}
      placeholder={placeholder}
      className={className}
      value={displayValue}
      onChange={handleChange}
      {...props}
    />
  );
}
