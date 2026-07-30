import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Check, RefreshCw, Save, Server } from "lucide-react";
import API, { extractDetailMessage } from "../api/client";
import { ErrorMessage } from "../components/ErrorMessage";
import { FintechCard } from "../components/ui/FintechCard";
import { SectionHeader } from "../components/ui/SectionHeader";
import { Skeleton } from "../components/ui/Skeleton";
import { useToast } from "../contexts/ToastContext";
import { usePersistentState } from "../hooks/usePersistentState";
import { labels } from "../i18n/vi";

type EnvType = "str" | "int" | "bool" | "list";

interface EnvItem {
  key: string;
  value: string;
  type: EnvType;
  requires_restart: boolean;
  description: string;
}

interface EnvGroup {
  title: string;
  keys: string[];
}

const GROUPS: EnvGroup[] = [
  { title: labels.envConfig.groupCore, keys: ["DATABASE_URL", "API_PREFIX", "CORS_ORIGINS"] },
  { title: labels.envConfig.groupScheduler, keys: ["SCHEDULER_HOUR", "SCHEDULER_MINUTE"] },
  {
    title: labels.envConfig.groupNewsScheduler,
    keys: [
      "NEWS_SCHEDULER_ENABLED",
      "NEWS_VN_MARKET_INTERVAL_MINUTES",
      "NEWS_VN_OFF_HOURS_INTERVAL_MINUTES",
      "NEWS_GLOBAL_INTERVAL_MINUTES",
    ],
  },
  {
    title: labels.envConfig.groupOllama, keys: [
      "OLLAMA_ENABLED", "OLLAMA_BASE_URL", "OLLAMA_MODEL", "OLLAMA_TIMEOUT", "OLLAMA_MAX_TAGS",
      "OLLAMA_AI_QUEUE_TIMEOUT_SECONDS", "OLLAMA_EMBEDDING_ENABLED", "OLLAMA_EMBEDDING_MODEL", "OLLAMA_EMBEDDING_DIMENSION",
    ]
  },
];

export function EnvConfig() {
  const qc = useQueryClient();
  const { showToast } = useToast();
  const [values, setValues] = usePersistentState<Record<string, string>>("envConfig.values", {});
  const [savedKey, setSavedKey] = useState<string | null>(null);

  const query = useQuery<EnvItem[]>({
    queryKey: ["env-config"],
    queryFn: async () => (await API.get("/settings/env-config")).data,
  });

  const save = useMutation({
    mutationFn: async (payload: Record<string, string>) => {
      const response = await API.post("/settings/env-config", payload);
      return response.data as { changed: EnvItem[]; requires_restart: boolean };
    },
    onSuccess: (data, variables) => {
      qc.invalidateQueries({ queryKey: ["env-config"] });
      const keys = Object.keys(variables);
      if (keys.length === 1) {
        setSavedKey(keys[0]);
        setTimeout(() => setSavedKey(null), 2000);
      }
      showToast(
        data.requires_restart
          ? "Đã lưu. Một số thay đổi cần khởi động lại backend để áp dụng."
          : "Đã lưu cấu hình môi trường",
        data.requires_restart ? "warning" : "success"
      );
    },
    onError: (error: any) => {
      showToast(extractDetailMessage(error?.response?.data?.detail) || "Không thể lưu cấu hình môi trường", "error");
    },
  });

  const getValue = (item: EnvItem) => {
    if (values[item.key] !== undefined) return values[item.key];
    return item.value ?? "";
  };

  const handleSaveKey = (key: string) => {
    save.mutate({ [key]: values[key] ?? "" });
  };

  const handleSaveAll = () => {
    if (!query.data) return;
    const payload: Record<string, string> = {};
    for (const item of query.data) {
      payload[item.key] = getValue(item);
    }
    save.mutate(payload);
  };

  const renderInput = (item: EnvItem) => {
    const value = getValue(item);
    if (item.type === "bool") {
      return (
        <select
          className="input-fintech"
          value={value.toLowerCase()}
          onChange={(e) => setValues({ ...values, [item.key]: e.target.value })}
        >
          <option value="true">{labels.common.yes}</option>
          <option value="false">{labels.common.no}</option>
        </select>
      );
    }
    if (item.type === "int") {
      return (
        <input
          type="number"
          className="input-fintech"
          value={value}
          onChange={(e) => setValues({ ...values, [item.key]: e.target.value })}
        />
      );
    }
    return (
      <input
        type="text"
        className="input-fintech"
        value={value}
        onChange={(e) => setValues({ ...values, [item.key]: e.target.value })}
      />
    );
  };

  const renderItems = (keys: string[]) => {
    if (!query.data) return null;
    const items = query.data.filter((i) => keys.includes(i.key));
    return (
      <div className="space-y-3">
        {items.map((item) => (
          <div key={item.key} className="grid grid-cols-1 md:grid-cols-12 gap-3 items-start">
            <div className="md:col-span-3">
              <label className="text-sm font-medium text-slate-700">{item.key}</label>
              <p className="text-xs text-slate-500 mt-0.5">{item.description}</p>
            </div>
            <div className="md:col-span-7">{renderInput(item)}</div>
            <div className="md:col-span-2 flex items-center gap-2">
              <button
                onClick={() => handleSaveKey(item.key)}
                disabled={save.isPending}
                className="btn-primary w-full"
              >
                {save.isPending ? (
                  labels.common.saving
                ) : savedKey === item.key ? (
                  <>
                    <Check className="w-4 h-4" />
                    {labels.common.saved}
                  </>
                ) : (
                  <>
                    <Save className="w-4 h-4" />
                    {labels.common.save}
                  </>
                )}
              </button>
              {item.requires_restart && (
                <span
                  className="shrink-0 inline-flex items-center justify-center w-6 h-6 rounded-full bg-amber-100 text-amber-600"
                  title={labels.envConfig.requiresRestart}
                >
                  <Server className="w-3.5 h-3.5" />
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {query.isError && <ErrorMessage error={query.error} retry={() => query.refetch()} />}
      {save.isError && <ErrorMessage error={save.error} retry={() => save.reset()} />}

      <SectionHeader title={labels.envConfig.title} />

      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-500">{labels.envConfig.description}</p>
        <div className="flex gap-2">
          <button
            onClick={() => qc.invalidateQueries({ queryKey: ["env-config"] })}
            className="btn-secondary"
          >
            <RefreshCw className={`w-4 h-4 ${query.isFetching ? "animate-spin" : ""}`} />
            {labels.common.refresh}
          </button>
          <button
            onClick={handleSaveAll}
            disabled={save.isPending || !query.data}
            className="btn-primary"
          >
            <Save className="w-4 h-4" />
            {save.isPending ? labels.common.saving : labels.envConfig.saveAll}
          </button>
        </div>
      </div>

      {query.isLoading ? (
        <Skeleton className="h-96" />
      ) : (
        GROUPS.map((group, idx) => (
          <FintechCard key={group.title} delay={idx * 0.05}>
            <h3 className="card-title mb-4">{group.title}</h3>
            {renderItems(group.keys)}
          </FintechCard>
        ))
      )}
    </div>
  );
}
