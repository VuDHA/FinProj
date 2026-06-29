import { useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, BookOpen, HelpCircle } from "lucide-react";
import { labels } from "../i18n/vi";

interface HelpModalProps {
  open: boolean;
  onClose: () => void;
}

export function HelpModal({ open, onClose }: HelpModalProps) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open && (
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
            className="relative w-full max-w-2xl max-h-[80vh] overflow-y-auto rounded-2xl border border-slate-200/80 bg-white/95 p-6 shadow-2xl backdrop-blur-xl"
          >
            <div className="flex items-start justify-between gap-4 mb-6">
              <div className="flex items-center gap-3">
                <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-br from-accent-blue to-accent-violet">
                  <BookOpen className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h2 className="text-lg font-semibold text-slate-900">{labels.guide.title}</h2>
                  <p className="text-sm text-slate-500">{labels.guide.subtitle}</p>
                </div>
              </div>
              <button
                onClick={onClose}
                className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-colors"
                aria-label={labels.common.close}
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4">
              {labels.guide.sections.map((section, idx) => (
                <div
                  key={idx}
                  className="rounded-xl border border-fintech-border bg-surface-elevated/50 p-4"
                >
                  <div className="flex items-center gap-2 mb-2">
                    <HelpCircle className="w-4 h-4 text-accent-blue" />
                    <h3 className="font-semibold text-slate-900">{section.title}</h3>
                  </div>
                  <p className="text-sm text-slate-600 leading-relaxed">{section.description}</p>
                </div>
              ))}
            </div>

            <div className="mt-6 flex justify-end">
              <button onClick={onClose} className="btn-primary">
                {labels.common.close}
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
