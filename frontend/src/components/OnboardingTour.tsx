import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronLeft, ChevronRight, X } from "lucide-react";

export interface TourStep {
  target: string;
  title: string;
  description: string;
}

interface OnboardingTourProps {
  steps: TourStep[];
  onComplete: () => void;
  onSkip: () => void;
}

export function OnboardingTour({ steps, onComplete, onSkip }: OnboardingTourProps) {
  const [current, setCurrent] = useState(0);
  const [rect, setRect] = useState<DOMRect | null>(null);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    if (current >= steps.length) {
      onComplete();
      return;
    }
    const target = steps[current].target;
    const el = document.querySelector(`[data-tour="${target}"]`) as HTMLElement | null;
    if (el) {
      setRect(el.getBoundingClientRect());
      setNotFound(false);
    } else {
      setNotFound(true);
      const timer = setTimeout(() => {
        if (current < steps.length - 1) {
          setCurrent((c) => c + 1);
        } else {
          onComplete();
        }
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [current, steps, onComplete]);

  if (!steps.length) return null;
  const step = steps[current];
  const isFirst = current === 0;
  const isLast = current === steps.length - 1;

  const next = () => {
    if (isLast) onComplete();
    else setCurrent((c) => c + 1);
  };

  const prev = () => setCurrent((c) => Math.max(0, c - 1));

  return (
    <div className="fixed inset-0 z-[60] overflow-hidden">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-slate-900/40 transition-opacity" />

      {rect && !notFound && (
        <>
          {/* Highlight ring */}
          <motion.div
            layoutId="tour-highlight"
            className="absolute rounded-xl border-2 border-accent-blue shadow-[0_0_0_9999px_rgba(15,23,42,0.45)]"
            style={{
              top: rect.top - 6,
              left: rect.left - 6,
              width: rect.width + 12,
              height: rect.height + 12,
            }}
          />

          {/* Tooltip card */}
          <AnimatePresence mode="wait">
            <motion.div
              key={step.target}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ duration: 0.2 }}
              className="absolute min-w-[18rem] max-w-xs rounded-2xl border border-slate-200/80 bg-white/95 p-5 shadow-2xl backdrop-blur-xl"
              style={{
                top: rect.bottom + 16,
                left: Math.min(rect.left, Math.max(16, typeof window !== "undefined" ? window.innerWidth - 320 : 320)),
              }}
            >
              <div className="flex items-start justify-between gap-3 mb-3">
                <h4 className="text-base font-semibold text-slate-900">{step.title}</h4>
                <button
                  onClick={onSkip}
                  className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-colors"
                  aria-label="Close tour"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
              <p className="text-sm text-slate-600 leading-relaxed mb-5">{step.description}</p>
              <div className="flex items-center justify-between">
                <div className="flex gap-1">
                  {steps.map((_, idx) => (
                    <span
                      key={idx}
                      className={`block h-1.5 rounded-full transition-all ${idx === current ? "w-4 bg-accent-blue" : "w-1.5 bg-slate-200"
                        }`}
                    />
                  ))}
                </div>
                <div className="flex items-center gap-2">
                  {!isFirst && (
                    <button
                      onClick={prev}
                      className="inline-flex items-center rounded-lg px-2.5 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-100 transition-colors"
                    >
                      <ChevronLeft className="w-4 h-4 mr-0.5" />
                      Back
                    </button>
                  )}
                  <button
                    onClick={next}
                    className="inline-flex items-center rounded-lg bg-gradient-to-r from-accent-blue to-accent-violet px-3 py-1.5 text-xs font-semibold text-white shadow-md hover:shadow-lg transition-all"
                  >
                    {isLast ? "Finish" : "Next"}
                    {!isLast && <ChevronRight className="w-4 h-4 ml-0.5" />}
                  </button>
                </div>
              </div>
            </motion.div>
          </AnimatePresence>
        </>
      )}
    </div>
  );
}
