import { ReactNode } from "react";
import { FintechCard } from "./ui/FintechCard";

interface EmptyStateProps {
  /** Optional icon node (lucide-react icon recommended) */
  icon?: ReactNode;
  /** Short, positively-framed title in Vietnamese */
  title: string;
  /** Supporting description */
  description?: string;
  /** Label for the call-to-action button */
  actionLabel?: string;
  /** Callback fired when the CTA button is clicked */
  onAction?: () => void;
  /** Backward-compatible custom action node (takes precedence over actionLabel/onAction) */
  action?: ReactNode;
  /** Animation delay (seconds) */
  delay?: number;
}

/**
 * Reusable empty-state panel with positive framing and a clear CTA.
 * Uses the app's glass-card / FintechCard styling for consistency.
 */
export function EmptyState({
  icon,
  title,
  description,
  actionLabel,
  onAction,
  action,
  delay = 0.1,
}: EmptyStateProps) {
  return (
    <FintechCard delay={delay} hover={false}>
      <div className="flex flex-col items-center justify-center py-10 px-4 text-center">
        {icon && (
          <div className="mb-4 flex items-center justify-center w-14 h-14 rounded-2xl bg-accent-blue/10 text-accent-blue ring-1 ring-inset ring-accent-blue/20">
            {icon}
          </div>
        )}
        <h3 className="text-lg font-semibold text-slate-800 mb-1.5">{title}</h3>
        {description && (
          <p className="text-sm text-slate-500 max-w-md mb-5 leading-relaxed">
            {description}
          </p>
        )}
        {action ? (
          <div className="flex items-center gap-3">{action}</div>
        ) : actionLabel && onAction ? (
          <button onClick={onAction} className="btn-primary">
            {actionLabel}
          </button>
        ) : null}
      </div>
    </FintechCard>
  );
}
