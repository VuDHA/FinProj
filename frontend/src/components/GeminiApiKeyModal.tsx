import { useState } from "react";
import { motion } from "framer-motion";
import { KeyRound } from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import API, { extractDetailMessage } from "../api/client";
import { labels } from "../i18n/vi";
import { useToast } from "../contexts/ToastContext";

interface GeminiApiKeyModalProps {
  onSave: () => void;
  onSkip: () => void;
}

export function GeminiApiKeyModal({ onSave, onSkip }: GeminiApiKeyModalProps) {
  const [value, setValue] = useState("");
  const { showToast } = useToast();

  const saveMutation = useMutation({
    mutationFn: async (payload: { GEMINI_API_KEY: string }) => {
      const { data } = await API.post("/settings/env-config", payload);
      return data;
    },
    onSuccess: () => {
      showToast(labels.onboarding.apiKeySaved, "success");
      onSave();
    },
    onError: (error: any) => {
      showToast(
        extractDetailMessage(error?.response?.data?.detail) ||
          labels.onboarding.apiKeySaveError,
        "error"
      );
    },
  });

  const handleSave = () => {
    if (!value.trim() || saveMutation.isPending) return;
    saveMutation.mutate({ GEMINI_API_KEY: value.trim() });
  };

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.92 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
        className="w-full max-w-md rounded-2xl border border-fintech-border bg-surface-elevated p-6 shadow-2xl"
      >
        <div className="flex flex-col items-center text-center mb-5">
          <div className="relative flex items-center justify-center w-14 h-14 rounded-full bg-gradient-to-br from-accent-blue to-accent-violet shadow-lg shadow-accent-blue/30 mb-4">
            <KeyRound className="w-7 h-7 text-theme-inverse" />
            <div className="absolute inset-0 rounded-full bg-accent-cyan/20 blur-md" />
          </div>
          <h2 className="font-display font-bold text-xl text-theme tracking-tight">
            {labels.onboarding.apiKeyModalTitle}
          </h2>
          <p className="mt-2 text-sm text-theme-muted leading-relaxed">
            {labels.onboarding.apiKeyModalSubtitle}
          </p>
        </div>

        <div className="space-y-3">
          <input
            type="password"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder={labels.onboarding.apiKeyModalPlaceholder}
            className="w-full rounded-xl border border-fintech-border bg-surface-card px-4 py-2.5 text-sm text-theme placeholder:text-theme-muted focus:outline-none focus:ring-2 focus:ring-accent-blue/40 transition"
            autoComplete="off"
            spellCheck={false}
          />

          <a
            href={labels.onboarding.apiKeyModalHelpUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-block text-xs font-medium text-accent-blue hover:underline"
          >
            {labels.onboarding.apiKeyModalHelp}
          </a>
        </div>

        <div className="flex gap-3 mt-6">
          <button
            onClick={onSkip}
            className="flex-1 rounded-xl border border-fintech-border px-4 py-2.5 text-sm font-medium text-theme-muted hover:bg-surface-card transition-colors"
          >
            {labels.onboarding.apiKeyModalSkip}
          </button>
          <button
            onClick={handleSave}
            disabled={!value.trim() || saveMutation.isPending}
            className="flex-1 rounded-xl bg-gradient-to-r from-accent-blue to-accent-violet px-4 py-2.5 text-sm font-semibold text-theme-inverse shadow-lg shadow-accent-blue/30 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed hover:opacity-90"
          >
            {labels.onboarding.apiKeyModalSave}
          </button>
        </div>
      </motion.div>
    </div>
  );
}
