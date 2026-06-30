import { motion } from "framer-motion";
import { CheckCircle, AlertCircle, X, Info } from "lucide-react";

export type ToastType = "success" | "error" | "info";

interface ToastProps {
  id: string;
  message: string;
  type: ToastType;
  onClose: () => void;
}

const config: Record<ToastType, { icon: typeof CheckCircle; color: string; border: string; bg: string }> = {
  success: {
    icon: CheckCircle,
    color: "text-emerald-600",
    border: "border-emerald-200",
    bg: "bg-emerald-50",
  },
  error: {
    icon: AlertCircle,
    color: "text-rose-600",
    border: "border-rose-200",
    bg: "bg-rose-50",
  },
  info: {
    icon: Info,
    color: "text-blue-600",
    border: "border-blue-200",
    bg: "bg-blue-50",
  },
};

export function Toast({ message, type, onClose }: ToastProps) {
  const { icon: Icon, color, border, bg } = config[type];

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 16, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, x: 24, scale: 0.95 }}
      transition={{ duration: 0.2 }}
      className={`flex items-center gap-3 min-w-[260px] max-w-[360px] rounded-xl border ${border} ${bg} p-3 shadow-lg shadow-slate-900/10 backdrop-blur-md`}
    >
      <Icon className={`w-5 h-5 flex-shrink-0 ${color}`} />
      <p className="flex-1 text-sm font-medium text-slate-800">{message}</p>
      <button
        onClick={onClose}
        className="p-1 rounded-md text-slate-400 hover:text-slate-600 hover:bg-slate-200/50 transition-colors"
        aria-label="Đóng"
      >
        <X className="w-4 h-4" />
      </button>
    </motion.div>
  );
}
