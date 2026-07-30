import { useQuery } from "@tanstack/react-query";
import { KeyRound } from "lucide-react";
import { Link } from "react-router-dom";
import { getAiStatus } from "../api/news";
import { usePersistentState } from "../hooks/usePersistentState";
import { labels } from "../i18n/vi";

export function ApiKeyBanner() {
  const { data } = useQuery({
    queryKey: ["ai-status-onboarding"],
    queryFn: getAiStatus,
    refetchInterval: false,
    staleTime: 60_000,
  });

  const [dismissed, setDismissed] = usePersistentState<boolean>(
    "onboarding-api-key-dismissed",
    false
  );

  if (dismissed) return null;
  if (!(data?.ai_provider === "gemini" && data?.gemini_configured === false)) {
    return null;
  }

  return (
    <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-amber-200 backdrop-blur-md">
      <div className="flex items-start gap-3">
        <KeyRound className="w-5 h-5 mt-0.5 flex-shrink-0" />
        <div className="flex-1">
          <p className="font-semibold text-sm">{labels.onboarding.apiKeyTitle}</p>
          <p className="text-sm opacity-90">{labels.onboarding.apiKeyMessage}</p>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <Link
            to="/env-config"
            className="px-3 py-1.5 text-sm font-medium rounded-lg border border-amber-500/30 bg-surface-elevated/70 hover:bg-amber-500/10 transition-colors"
          >
            {labels.onboarding.apiKeyAction}
          </Link>
          <button
            onClick={() => setDismissed(true)}
            className="px-3 py-1.5 text-sm font-medium rounded-lg border border-amber-500/30 bg-surface-elevated/70 hover:bg-amber-500/10 transition-colors"
          >
            {labels.onboarding.dismiss}
          </button>
        </div>
      </div>
    </div>
  );
}
