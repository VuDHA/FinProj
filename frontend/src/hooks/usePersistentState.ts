import { useCallback, useState } from "react";
import { getItem, setItem } from "../lib/storage";

export function usePersistentState<T>(key: string, initialValue: T) {
  const [value, setValue] = useState<T>(() => getItem(key, initialValue));

  const setPersistentValue = useCallback(
    (next: T | ((prev: T) => T)) => {
      setValue((prev) => {
        const resolved = typeof next === "function" ? (next as (prev: T) => T)(prev) : next;
        setItem(key, resolved);
        return resolved;
      });
    },
    [key]
  );

  return [value, setPersistentValue] as const;
}
