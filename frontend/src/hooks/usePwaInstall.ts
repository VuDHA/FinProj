import { useCallback, useEffect, useRef, useState } from "react";

type Platform = "ios" | "android" | "desktop" | "unknown";

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

export interface UsePwaInstallReturn {
  /** Whether the browser has fired `beforeinstallprompt` and the app is installable. */
  canInstall: boolean;
  /** Whether the app is already installed (standalone mode or after `appinstalled`). */
  installed: boolean;
  /** Triggers the native install prompt. Returns the user's choice or null if unavailable. */
  promptInstall: () => Promise<"accepted" | "dismissed" | null>;
  /** Detected platform via userAgent. */
  platform: Platform;
  /** iOS Safari does not support `beforeinstallprompt`; show manual instructions instead. */
  iosInstructions: boolean;
}

function detectPlatform(): Platform {
  if (typeof navigator === "undefined") return "unknown";
  const ua = navigator.userAgent.toLowerCase();
  if (/iphone|ipad|ipod/.test(ua)) return "ios";
  if (/android/.test(ua)) return "android";
  if (/windows|macintosh|linux/.test(ua)) return "desktop";
  return "unknown";
}

function isStandalone(): boolean {
  if (typeof window === "undefined") return false;
  return (
    window.matchMedia?.("(display-mode: standalone)").matches ||
    // iOS Safari standalone indicator
    (window.navigator as unknown as { standalone?: boolean }).standalone === true
  );
}

/**
 * Hook that tracks PWA installability and exposes helpers to trigger the
 * native install prompt. On iOS (where `beforeinstallprompt` never fires),
 * `iosInstructions` is true so the UI can show manual steps instead.
 */
export function usePwaInstall(): UsePwaInstallReturn {
  const deferredPromptRef = useRef<BeforeInstallPromptEvent | null>(null);
  const [canInstall, setCanInstall] = useState(false);
  const [installed, setInstalled] = useState(() => isStandalone());
  const platform = useRef<Platform>(detectPlatform()).current;

  useEffect(() => {
    const handleBeforeInstallPrompt = (e: Event) => {
      e.preventDefault();
      deferredPromptRef.current = e as BeforeInstallPromptEvent;
      setCanInstall(true);
    };

    const handleAppInstalled = () => {
      deferredPromptRef.current = null;
      setCanInstall(false);
      setInstalled(true);
    };

    window.addEventListener("beforeinstallprompt", handleBeforeInstallPrompt);
    window.addEventListener("appinstalled", handleAppInstalled);

    return () => {
      window.removeEventListener("beforeinstallprompt", handleBeforeInstallPrompt);
      window.removeEventListener("appinstalled", handleAppInstalled);
    };
  }, []);

  const promptInstall = useCallback(async (): Promise<
    "accepted" | "dismissed" | null
  > => {
    const deferred = deferredPromptRef.current;
    if (!deferred) return null;
    await deferred.prompt();
    const choice = await deferred.userChoice;
    deferredPromptRef.current = null;
    setCanInstall(false);
    if (choice.outcome === "accepted") {
      setInstalled(true);
    }
    return choice.outcome;
  }, []);

  return {
    canInstall,
    installed,
    promptInstall,
    platform,
    iosInstructions: platform === "ios",
  };
}
