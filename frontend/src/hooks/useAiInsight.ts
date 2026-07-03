import { useState } from "react";
import { useAiQueue } from "../contexts/AiQueueContext";
import { useToast } from "../contexts/ToastContext";
import { AIInsightResponse } from "../api/ai";

interface UseAiInsightOptions<T> {
  taskName: string;
  fetcher: () => Promise<T>;
  onSuccess?: (data: T) => void;
}

export function useAiInsight<T = AIInsightResponse>({ taskName, fetcher, onSuccess }: UseAiInsightOptions<T>) {
  const { runAi, setCooldown } = useAiQueue();
  const { showToast } = useToast();
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generate = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await runAi(taskName, fetcher);
      setData(result);
      if (onSuccess) onSuccess(result);
      return result;
    } catch (err: any) {
      const message = err?.response?.data?.detail?.message || err?.message || "Không thể tạo phân tích AI";
      const cooldown = err?.response?.data?.detail?.cooldown_seconds;
      if (cooldown) {
        setCooldown(cooldown);
      }
      setError(message);
      showToast(message, "error");
      return null;
    } finally {
      setLoading(false);
    }
  };

  const clear = () => {
    setData(null);
    setError(null);
  };

  return { data, loading, error, generate, clear };
}
