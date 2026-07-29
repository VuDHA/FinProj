import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Download, Share, X } from "lucide-react";
import { usePwaInstall } from "../hooks/usePwaInstall";
import { labels } from "../i18n/vi";

const DISMISS_KEY = "pwa-install-dismissed";

export function PwaInstallPrompt() {
  const { canInstall, promptInstall, installed, iosInstructions } = usePwaInstall();
  const [dismissed, setDismissed] = useState(() => {
    try {
      return localStorage.getItem(DISMISS_KEY) === "true";
    } catch {
      return false;
    }
  });

  const shouldShow =
    !installed && !dismissed && (canInstall || iosInstructions);

  const handleDismiss = () => {
    try {
      localStorage.setItem(DISMISS_KEY, "true");
    } catch {
      // ignore storage errors
    }
    setDismissed(true);
  };

  const handleInstall = async () => {
    const outcome = await promptInstall();
    if (outcome === "accepted") {
      handleDismiss();
    }
  };

  return (
    <AnimatePresence>
      {shouldShow && (
        <motion.div
          initial={{ opacity: 0, y: -16 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -16 }}
          transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
          className="mb-4 rounded-xl border border-accent-blue/20 bg-gradient-to-r from-accent-blue/[0.08] to-accent-violet/[0.08] backdrop-blur-sm px-4 py-3"
        >
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-gradient-to-br from-accent-blue to-accent-violet text-theme-inverse shrink-0">
              {iosInstructions ? (
                <Share className="w-4 h-4" />
              ) : (
                <Download className="w-4 h-4" />
              )}
            </div>

            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold text-theme">
                {labels.pwa.installTitle}
              </p>
              <p className="text-xs text-theme-muted leading-snug">
                {iosInstructions ? labels.pwa.iosInstructions : labels.pwa.installDescription}
              </p>
            </div>

            <div className="flex items-center gap-2 shrink-0">
              {!iosInstructions && (
                <button
                  onClick={handleInstall}
                  className="rounded-lg bg-gradient-to-r from-accent-blue to-accent-violet px-3 py-1.5 text-xs font-semibold text-theme-inverse transition-opacity hover:opacity-90"
                >
                  {labels.pwa.installButton}
                </button>
              )}
              <button
                onClick={handleDismiss}
                className="rounded-lg px-2 py-1.5 text-xs font-medium text-theme-muted transition-colors hover:text-theme"
              >
                {labels.pwa.laterButton}
              </button>
              <button
                onClick={handleDismiss}
                className="p-1 rounded-md text-theme-muted hover:text-theme transition-colors"
                aria-label={labels.pwa.laterButton}
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
