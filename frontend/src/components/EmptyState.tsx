import { ReactNode } from "react";
import { FintechCard } from "./ui/FintechCard";

interface EmptyStateProps {
  title: string;
  description: string;
  action?: ReactNode;
  delay?: number;
}

export function EmptyState({ title, description, action, delay = 0.1 }: EmptyStateProps) {
  return (
    <FintechCard delay={delay}>
      <div className="flex flex-col items-center justify-center py-10 text-center">
        <h3 className="text-lg font-semibold text-slate-800 mb-1">{title}</h3>
        <p className="text-sm text-slate-500 max-w-md mb-4">{description}</p>
        {action && <div className="flex items-center gap-3">{action}</div>}
      </div>
    </FintechCard>
  );
}
