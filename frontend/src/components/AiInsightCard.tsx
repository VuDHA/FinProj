import { AlertTriangle, Bot, Lightbulb, Loader2 } from "lucide-react";

export interface AiInsightData {
  overall: string;
  details: string;
  suggestions: string[];
  used_ollama?: boolean;
}

interface AiInsightCardProps {
  data?: AiInsightData | null;
  loading?: boolean;
  error?: string | null;
  onClose?: () => void;
}

export function AiInsightCard({ data, loading, error, onClose }: AiInsightCardProps) {
  if (loading) {
    return (
      <div className="rounded-xl border border-indigo-100 bg-indigo-50/50 p-4 flex items-center gap-3">
        <Loader2 className="w-5 h-5 text-indigo-500 animate-spin" />
        <span className="text-sm text-indigo-700">AI đang phân tích, vui lòng đợi...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-rose-100 bg-rose-50 p-4 flex items-start gap-3">
        <AlertTriangle className="w-5 h-5 text-rose-500 shrink-0 mt-0.5" />
        <div className="flex-1">
          <p className="text-sm font-medium text-rose-800">Không thể tạo phân tích</p>
          <p className="text-sm text-rose-600 mt-1">{error}</p>
        </div>
        {onClose && (
          <button onClick={onClose} className="text-rose-400 hover:text-rose-600 text-sm">
            Đóng
          </button>
        )}
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="rounded-xl border border-indigo-100 bg-gradient-to-br from-indigo-50/80 to-white p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Bot className="w-5 h-5 text-indigo-500" />
          <h4 className="text-sm font-semibold text-indigo-900">Phân tích AI</h4>
          {data.used_ollama && (
            <span className="text-xs text-slate-500 bg-slate-100 px-2 py-0.5 rounded">
              local
            </span>
          )}
        </div>
        {onClose && (
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 text-sm">
            Đóng
          </button>
        )}
      </div>

      {data.overall && (
        <div>
          <p className="text-sm font-medium text-slate-900 mb-1">Tổng quan</p>
          <p className="text-sm text-slate-700 leading-relaxed">{data.overall}</p>
        </div>
      )}

      {data.details && (
        <div>
          <p className="text-sm font-medium text-slate-900 mb-1">Chi tiết</p>
          <p className="text-sm text-slate-700 leading-relaxed whitespace-pre-line">{data.details}</p>
        </div>
      )}

      {data.suggestions && data.suggestions.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-2">
            <Lightbulb className="w-4 h-4 text-amber-500" />
            <p className="text-sm font-medium text-slate-900">Gợi ý hành động</p>
          </div>
          <ul className="space-y-1.5">
            {data.suggestions.map((s, i) => (
              <li key={i} className="text-sm text-slate-700 flex items-start gap-2">
                <span className="text-indigo-500 shrink-0">•</span>
                {s}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
