const APP_PREFIX = "wealthvn_";
export const CACHE_VERSION = 2;

const noopStorage: Storage = {
  getItem: () => null,
  setItem: () => undefined,
  removeItem: () => undefined,
  key: () => null,
  length: 0,
  clear: () => undefined,
};

function getStorage() {
  return typeof window !== "undefined" && window.localStorage ? window.localStorage : null;
}

export function getLocalStorage(): Storage {
  return getStorage() ?? noopStorage;
}

export function getItem<T>(key: string, fallback: T): T {
  try {
    const raw = getStorage()?.getItem(`${APP_PREFIX}${key}`);
    if (raw == null) return fallback;
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

export function setItem(key: string, value: unknown): void {
  try {
    getStorage()?.setItem(`${APP_PREFIX}${key}`, JSON.stringify(value));
  } catch {
    // ignore quota / private mode errors
  }
}

export function removeItem(key: string): void {
  try {
    getStorage()?.removeItem(`${APP_PREFIX}${key}`);
  } catch {
    // ignore
  }
}

export function clearAppStorage(): void {
  try {
    const storage = getStorage();
    if (!storage) return;
    for (let i = storage.length - 1; i >= 0; i--) {
      const k = storage.key(i);
      if (k?.startsWith(APP_PREFIX)) storage.removeItem(k);
    }
  } catch {
    // ignore
  }
}

export function checkStorageVersion(): void {
  const v = getItem<number>("version", 0);
  if (v !== CACHE_VERSION) {
    clearAppStorage();
    setItem("version", CACHE_VERSION);
  }
}
