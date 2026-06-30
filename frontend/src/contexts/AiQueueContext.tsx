import {
  createContext,
  ReactNode,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
} from "react";
import { labels } from "../i18n/vi";

interface AiQueueState {
  isBusy: boolean;
  currentTask: string | null;
}

interface AiQueueContextValue extends AiQueueState {
  runAi: <T>(taskName: string, fn: () => Promise<T>) => Promise<T>;
}

const AiQueueContext = createContext<AiQueueContextValue | null>(null);

export function AiQueueProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AiQueueState>({
    isBusy: false,
    currentTask: null,
  });
  const busyRef = useRef(false);

  const runAi = useCallback(async <T,>(taskName: string, fn: () => Promise<T>): Promise<T> => {
    if (busyRef.current) {
      throw new Error("AI đang bận. Vui lòng đợi tác vụ AI hiện tại hoàn thành.");
    }
    busyRef.current = true;
    setState({ isBusy: true, currentTask: taskName });
    try {
      return await fn();
    } finally {
      busyRef.current = false;
      setState({ isBusy: false, currentTask: null });
    }
  }, []);

  const value = useMemo(
    () => ({
      ...state,
      runAi,
    }),
    [state, runAi]
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
