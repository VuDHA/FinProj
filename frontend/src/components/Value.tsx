interface ValueProps {
  value: number | string | null | undefined;
  formatter?: (n: number) => string;
  className?: string;
  fallback?: string;
}

export function Value({ value, formatter, className = "", fallback = "—" }: ValueProps) {
  if (value === null || value === undefined) {
    return <span className={className}>{fallback}</span>;
  }

  const text = typeof value === "number" && formatter ? formatter(value) : String(value);

  return (
    <span className={className} title={text}>
      {text}
    </span>
  );
}
