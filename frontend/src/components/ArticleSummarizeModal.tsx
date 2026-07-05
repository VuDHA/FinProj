import { useEffect, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import { ExternalLink, Loader2, Sparkles, X } from "lucide-react";
import { summarizeArticle, type Article, type ArticleSummarizeResponse } from "../api/news";
import { MarkdownRenderer } from "./MarkdownRenderer";
import { labels } from "../i18n/vi";

interface ArticleSummarizeModalProps {
  open: boolean;
  onClose: () => void;
  article: Article | null;
}

export function ArticleSummarizeModal({ open, onClose, article }: ArticleSummarizeModalProps) {
  const [displayArticle, setDisplayArticle] = useState<Article | null>(null);

  const mutation = useMutation<ArticleSummarizeResponse, Error, Article>({
    mutationFn: (a) =>
      summarizeArticle({
        url: a.url,
        title: a.title || undefined,
        language: a.language || undefined,
      }),
  });

  useEffect(() => {
    if (open && article) {
      setDisplayArticle(article);
    }
  }, [open, article]);

  useEffect(() => {
    if (!open) {
      mutation.reset();
      return;
    }
    if (article) {
      mutation.reset();
      mutation.mutate(article);
    }
  }, [open, article]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  const data = mutation.data;
  const isLoading = mutation.isPending;
  const error = mutation.error;

  return (
    <AnimatePresence>
      {open && displayArticle && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm"
            onClick={onClose}
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: 12 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 12 }}
            transition={{ duration: 0.2 }}
            className="relative flex flex-col w-full max-w-2xl max-h-[80vh] overflow-hidden rounded-2xl border border-slate-200/80 bg-white/95 shadow-2xl backdrop-blur-xl"
          >
            <div className="flex items-start justify-between gap-4 p-6 border-b border-slate-100">
              <div className="flex items-center gap-3 min-w-0">
                <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-br from-accent-violet to-accent-blue shrink-0">
                  <Sparkles className="w-5 h-5 text-white" />
                </div>
                <div className="min-w-0">
                  <h2 className="text-lg font-semibold text-slate-900 truncate">
                    {labels.news.articleSummary || "Tóm tắt bài viết"}
                  </h2>
                  <p className="text-sm text-slate-500 truncate">{displayArticle.title}</p>
                </div>
              </div>
              <button
                onClick={onClose}
                className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-colors shrink-0"
                aria-label={labels.common.close}
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-6">
              {isLoading ? (
                <div className="flex flex-col items-center justify-center gap-3 py-12 text-slate-500">
                  <Loader2 className="w-8 h-8 animate-spin text-accent-violet" />
                  <p className="text-sm">{labels.news.summarizing || "Đang tóm tắt bài viết..."}</p>
                </div>
              ) : error ? (
                <div className="rounded-xl border border-rose-100 bg-rose-50/80 p-4 text-sm text-rose-700">
                  {error.message || labels.news.summarizeError || "Không thể tóm tắt bài viết."}
                </div>
              ) : data ? (
                <div className="space-y-5">
                  {data.tags.length > 0 && (
                    <div className="flex flex-wrap gap-2">
                      {data.tags.map((tag) => (
                        <span
                          key={tag}
                          className="px-2.5 py-1 rounded-full bg-indigo-50 text-indigo-700 text-xs font-medium"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                  <div className="text-sm text-slate-800 leading-relaxed">
                    <MarkdownRenderer content={data.summary} />
                  </div>
                  {data.partial && (
                    <p className="text-xs text-amber-600 bg-amber-50 rounded-lg p-2">
                      {labels.news.summarizePartial ||
                        "Trang nguồn hạn chế truy cập; tóm tắt dựa trên tiêu đề/mô tả."}
                    </p>
                  )}
                  {!data.used_ai && (
                    <p className="text-xs text-slate-400 italic">
                      {labels.news.summarizeFallback || "Tóm tắt nhanh (AI không khả dụng)."}
                    </p>
                  )}
                </div>
              ) : null}
            </div>

            <div className="flex items-center justify-between gap-3 p-4 border-t border-slate-100 bg-slate-50/60">
              {data && (
                <a
                  href={data.source_url}
                  target="_blank"
                  rel="noreferrer"
                  className="btn-primary"
                >
                  <ExternalLink className="w-4 h-4" />
                  {labels.news.goToSource || "Xem nguồn"}
                </a>
              )}
              <div className="flex-1" />
              <button onClick={onClose} className="btn-secondary">
                {labels.common.close}
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
