import {
  createContext,
  ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { labels } from "../i18n/vi";

interface AiQueueState {
  isBusy: boolean;
  currentTask: string | null;
  cooldownSeconds: number;
}

interface AiQueueContextValue extends AiQueueState {
  runAi: <T>(taskName: string, fn: () => Promise<T>) => Promise<T>;
  setCooldown: (seconds: number) => void;
}

const AiQueueContext = createContext<AiQueueContextValue | null>(null);

export function AiQueueProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AiQueueState>({
    isBusy: false,
    currentTask: null,
    cooldownSeconds: 0,
  });
  const busyRef = useRef(false);
  const cooldownRef = useRef<number>(0);

  const setCooldown = useCallback((seconds: number) => {
    const rounded = Math.max(0, Math.ceil(seconds));
    cooldownRef.current = rounded;
    setState((prev) => ({ ...prev, cooldownSeconds: rounded }));
  }, []);

  useEffect(() => {
    if (state.cooldownSeconds <= 0) return;
    const timer = setInterval(() => {
      const next = Math.max(0, cooldownRef.current - 1);
      cooldownRef.current = next;
      setState((prev) => ({ ...prev, cooldownSeconds: next }));
      if (next <= 0) {
        clearInterval(timer);
      }
    }, 1000);
    return () => clearInterval(timer);
  }, [state.cooldownSeconds]);

  const runAi = useCallback(async <T,>(taskName: string, fn: () => Promise<T>): Promise<T> => {
    if (busyRef.current) {
      throw new Error("AI đang xử lý tác vụ khác. Vui lòng đợi.");
    }
    if (cooldownRef.current > 0) {
      throw new Error(`AI đang giới hạn tốc độ. Vui lòng đợi ${cooldownRef.current}s.`);
    }
    busyRef.current = true;
    setState((prev) => ({ ...prev, isBusy: true, currentTask: taskName }));
    try {
      return await fn();
    } finally {
      busyRef.current = false;
      setState((prev) => ({ ...prev, isBusy: false, currentTask: null }));
    }
  }, []);

  const value = useMemo(
    () => ({
      ...state,
      runAi,
      setCooldown,
    }),
    [state, runAi, setCooldown]
  );

  return (
    <AiQueueContext.Provider value={value}>
      {children}
    </AiQueueContext.Provider>
  );
}

export function useAiQueue(): AiQueueContextValue {
  const ctx = useContext(AiQueueContext);
  if (!ctx) {
    throw new Error(labels.errors.useAiQueueContext);
  }
  return ctx;
}
