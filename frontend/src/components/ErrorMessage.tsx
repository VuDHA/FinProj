import { AlertCircle } from "lucide-react";
import { labels } from "../i18n/vi";

export function ErrorMessage({ error, retry }: { error: Error | null; retry?: () => void }) {
  if (!error) return null;
  const message = (error as any)?.response?.data?.detail || error.message || labels.common.error;
  return (
    <div className="rounded-xl border border-accent-rose/30 bg-accent-rose/10 p-4 text-accent-rose backdrop-blur-md">
      <div className="flex items-start gap-3">
        <AlertCircle className="w-5 h-5 mt-0.5 flex-shrink-0" />
        <div className="flex-1">
          <p className="font-semibold text-sm">{labels.common.error}</p>
          <p className="text-sm opacity-90">{message}</p>
        </div>
        {retry && (
          <button
            onClick={retry}
            className="px-3 py-1.5 text-sm font-medium rounded-lg border border-accent-rose/30 bg-white/60 hover:bg-accent-rose/10 transition-colors"
          >
            {labels.common.retry}
          </button>
        )}
      </div>
    </div>
  );
}
