import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient } from "@tanstack/react-query";
import { PersistQueryClientProvider } from "@tanstack/react-query-persist-client";
import { createSyncStoragePersister } from "@tanstack/query-sync-storage-persister";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { AiQueueProvider } from "./contexts/AiQueueContext";
import { ThemeProvider } from "./contexts/ThemeContext";
import { ToastProvider } from "./contexts/ToastContext";
import { checkStorageVersion, getLocalStorage } from "./lib/storage";
import "./index.css";

checkStorageVersion();

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 0,
    },
  },
});

const persister = createSyncStoragePersister({
  storage: getLocalStorage(),
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <PersistQueryClientProvider
      client={queryClient}
      persistOptions={{
        persister,
        maxAge: Infinity,
        dehydrateOptions: { shouldDehydrateQuery: () => true },
      }}
    >
      <BrowserRouter>
        <ThemeProvider>
          <AiQueueProvider>
            <ToastProvider>
              <App />
            </ToastProvider>
          </AiQueueProvider>
        </ThemeProvider>
      </BrowserRouter>
    </PersistQueryClientProvider>
  </React.StrictMode>
);
