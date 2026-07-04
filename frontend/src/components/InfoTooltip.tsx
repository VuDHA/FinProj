import { useState, useRef, useLayoutEffect } from "react";
import { createPortal } from "react-dom";
import { Info } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

type TooltipPosition = "top" | "bottom" | "left" | "right";

interface InfoTooltipProps {
  content: string;
  title?: string;
  className?: string;
  position?: TooltipPosition;
}

interface Rect {
  left: number;
  top: number;
  width: number;
  height: number;
  right: number;
  bottom: number;
}

const GAP = 8;
const TOOLTIP_WIDTH = 224;

function computeStyle(position: TooltipPosition, rect: Rect) {
  const vw = typeof window !== "undefined" ? window.innerWidth : 1024;
  const vh = typeof window !== "undefined" ? window.innerHeight : 768;

  let left = 0;
  let top = 0;
  let arrowLeft = 0;
  let arrowTop = 0;

  const centerX = rect.left + rect.width / 2;
  const centerY = rect.top + rect.height / 2;

  // Flip left/right to the opposite side if it would overflow the viewport.
  let finalPosition = position;
  if (position === "right" && rect.right + GAP + TOOLTIP_WIDTH > vw) {
    finalPosition = "left";
  } else if (position === "left" && rect.left - GAP - TOOLTIP_WIDTH < 0) {
    finalPosition = "right";
  }

  switch (finalPosition) {
    case "top": {
      top = rect.top - GAP;
      left = centerX;
      arrowTop = top + 1;
      arrowLeft = centerX;
      break;
    }
    case "bottom": {
      top = rect.bottom + GAP;
      left = centerX;
      arrowTop = top - 5;
      arrowLeft = centerX;
      break;
    }
    case "left": {
      left = rect.left - GAP;
      top = centerY;
      arrowLeft = left + 1;
      arrowTop = centerY;
      break;
    }
    case "right": {
      left = rect.right + GAP;
      top = centerY;
      arrowLeft = left - 5;
      arrowTop = centerY;
      break;
    }
  }

  // Keep inside viewport horizontally
  if (finalPosition === "top" || finalPosition === "bottom") {
    left = Math.max(TOOLTIP_WIDTH / 2 + 8, Math.min(vw - TOOLTIP_WIDTH / 2 - 8, left));
  }
  if (finalPosition === "left" || finalPosition === "right") {
    // Clamp left so the tooltip body stays within the viewport.
    left = Math.max(8, Math.min(vw - TOOLTIP_WIDTH - 8, left));
    top = Math.max(40, Math.min(vh - 80, top));
  }

  return {
    position: finalPosition,
    tooltip: finalPosition === "top" || finalPosition === "bottom"
      ? { left, top, transform: "translate(-50%, -100%)" }
      : { left, top, transform: "translate(0, -50%)" },
    arrow: { left: arrowLeft, top: arrowTop },
  };
}

export function InfoTooltip({ content, title, className = "", position = "top" }: InfoTooltipProps) {
  const [open, setOpen] = useState(false);
  const [rect, setRect] = useState<Rect | null>(null);
  const triggerRef = useRef<HTMLSpanElement>(null);

  useLayoutEffect(() => {
    if (!open || !triggerRef.current) return;
    const update = () => {
      const r = triggerRef.current?.getBoundingClientRect();
      if (r) setRect({ left: r.left, top: r.top, width: r.width, height: r.height, right: r.right, bottom: r.bottom });
    };
    update();
    window.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    return () => {
      window.removeEventListener("scroll", update);
      window.removeEventListener("resize", update);
    };
  }, [open]);

  const style = rect ? computeStyle(position, rect) : null;
  const finalPosition = style?.position || position;

  return (
    <span
      ref={triggerRef}
      className={`relative inline-flex align-middle ml-1.5 ${className}`}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onClick={() => setOpen((v) => !v)}
      role="button"
      aria-label={title ? `${title}: ${content}` : content}
    >
      <Info className="w-4 h-4 text-slate-400 hover:text-accent-blue cursor-help transition-colors" />
      {open &&
        createPortal(
          <AnimatePresence>
            <motion.div
              initial={{ opacity: 0, y: finalPosition === "top" ? 4 : finalPosition === "bottom" ? -4 : 0, x: finalPosition === "left" ? 4 : finalPosition === "right" ? -4 : 0 }}
              animate={{ opacity: 1, y: 0, x: 0 }}
              exit={{ opacity: 0, y: finalPosition === "top" ? 4 : finalPosition === "bottom" ? -4 : 0, x: finalPosition === "left" ? 4 : finalPosition === "right" ? -4 : 0 }}
              transition={{ duration: 0.15 }}
              className="fixed z-[9999] w-56 rounded-xl border border-slate-200/80 bg-white/95 p-3 text-xs text-slate-600 shadow-xl backdrop-blur-md pointer-events-none"
              style={style?.tooltip}
            >
              {title && <div className="font-semibold text-slate-900 mb-1">{title}</div>}
              {content}
              <span
                className="fixed z-[9999] w-2 h-2 bg-white/95 border-l border-t border-slate-200/80 rotate-45 pointer-events-none"
                style={style?.arrow}
              />
            </motion.div>
          </AnimatePresence>,
          document.body
        )}
    </span>
  );
}
