import { Sparkles } from "lucide-react";
import { useAiQueue } from "../contexts/AiQueueContext";

interface AiGenerateButtonProps {
  onClick: () => void;
  loading?: boolean;
  label?: string;
  disabled?: boolean;
  size?: "sm" | "md";
}

export function AiGenerateButton({
  onClick,
  loading,
  label = "Phân tích AI",
  disabled,
  size = "md",
}: AiGenerateButtonProps) {
  const { isBusy, cooldownSeconds } = useAiQueue();
  const isLocked = loading || isBusy || cooldownSeconds > 0 || disabled;

  const sizeClasses =
    size === "sm"
      ? "text-xs px-2.5 py-1.5 gap-1.5"
      : "text-sm px-3 py-2 gap-2";

  return (
    <button
      onClick={onClick}
      disabled={isLocked}
      className={`inline-flex items-center rounded-lg font-medium transition-all ${sizeClasses} ${
        isLocked
          ? "bg-slate-200 text-slate-500 cursor-not-allowed"
          : "bg-gradient-to-r from-indigo-500 to-violet-500 text-white hover:from-indigo-600 hover:to-violet-600 shadow-sm"
      }`}
    >
      <Sparkles className={`${size === "sm" ? "w-3.5 h-3.5" : "w-4 h-4"} ${loading ? "animate-pulse" : ""}`} />
      {cooldownSeconds > 0 ? `Đợi ${cooldownSeconds}s` : label}
    </button>
  );
}
