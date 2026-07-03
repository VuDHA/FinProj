import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient } from "@tanstack/react-query";
import { PersistQueryClientProvider } from "@tanstack/react-query-persist-client";
import { createSyncStoragePersister } from "@tanstack/query-sync-storage-persister";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { AiQueueProvider } from "./contexts/AiQueueContext";
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
  maxAge: Infinity,
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <PersistQueryClientProvider
      client={queryClient}
      persistOptions={{
        persister,
        dehydrateOptions: { shouldDehydrateQuery: () => true },
      }}
    >
      <BrowserRouter>
        <AiQueueProvider>
          <ToastProvider>
            <App />
          </ToastProvider>
        </AiQueueProvider>
      </BrowserRouter>
    </PersistQueryClientProvider>
  </React.StrictMode>
);
