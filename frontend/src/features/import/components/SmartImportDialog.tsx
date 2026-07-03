import { useMutation } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { FileSpreadsheet, Loader2, Upload } from "lucide-react";
import {
  previewSmartImport,
  runSmartImport,
  type SmartImportPayload,
  type SmartImportPreview,
} from "../../../api/import";
import { useAiQueue } from "../../../contexts/AiQueueContext";
import { useToast } from "../../../contexts/ToastContext";
import { labels } from "../../../i18n/vi";
import { FintechCard } from "../../../components/ui/FintechCard";

const TARGET_FIELDS: Record<"assets" | "transactions", string[]> = {
  assets: ["symbol", "name", "type", "exchange", "currency", "value"],
  transactions: ["symbol", "type", "quantity", "price", "fee", "date", "notes"],
};

interface SmartImportDialogProps {
  importType: "assets" | "transactions";
  onClose: () => void;
  onSuccess: () => void;
}

export function SmartImportDialog({ importType, onClose, onSuccess }: SmartImportDialogProps) {
  const { showToast } = useToast();
  const { isBusy, runAi } = useAiQueue();
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<SmartImportPreview | null>(null);
  const [mapping, setMapping] = useState<Record<string, string | null>>({});
  const [sheet, setSheet] = useState<string | null>(null);

  const targetFields = TARGET_FIELDS[importType];

  const previewMutation = useMutation({
    mutationFn: (previewSheet: string | null) => {
      if (!file) throw new Error(labels.errors.noFileSelected);
      return runAi("smart_import_preview", () => previewSmartImport(file, importType, previewSheet));
    },
    onSuccess: (data) => {
      setPreview(data);
      setMapping(data.suggested_mapping);
      if (data.sheet) {
        setSheet(data.sheet);
      }
    },
    onError: (error: any) => {
      showToast(error?.message || "Không thể đọc file", "error");
    },
  });

  const importMutation = useMutation({
    mutationFn: () => {
      if (!file) throw new Error(labels.errors.noFileSelected);
      const payload: SmartImportPayload = {
        import_type: importType,
        mapping,
        sheet: sheet ?? null,
      };
      return runAi("smart_import", () => runSmartImport(file, payload));
    },
    onSuccess: (data) => {
      showToast(
        `Đã nhập ${data.created} dòng, bỏ qua ${data.skipped} dòng.`,
        data.errors.length > 0 ? "warning" : "success"
      );
      onSuccess();
      onClose();
    },
    onError: (error: any) => {
      showToast(error?.message || "Không thể nhập dữ liệu", "error");
    },
  });

  const requiredTargets = useMemo(() => {
    return importType === "assets" ? ["symbol", "name", "type"] : ["symbol", "type", "quantity", "price", "date"];
  }, [importType]);

  const mappedTargets = useMemo(
    () => new Set(Object.values(mapping).filter(Boolean)),
    [mapping]
  );
  const missingTargets = requiredTargets.filter((t) => !mappedTargets.has(t));

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0] ?? null;
    setFile(selected);
    setPreview(null);
    setMapping({});
    setSheet(null);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <FintechCard className="w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-slate-900 inline-flex items-center gap-2">
            <FileSpreadsheet className="w-5 h-5 text-indigo-600" />
            {importType === "assets" ? labels.importExport.smartImportAssets : labels.importExport.smartImportTransactions}
          </h3>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-700"
          >
            ✕
          </button>
        </div>

        <div className="space-y-4">
          <div className="border-2 border-dashed border-slate-200 rounded-xl p-6 text-center hover:border-indigo-300 transition-colors">
            <input
              id="smart-import-file"
              type="file"
              accept=".csv,.xlsx,.zip"
              className="hidden"
              onChange={handleFileChange}
            />
            <label
              htmlFor="smart-import-file"
              className="cursor-pointer inline-flex flex-col items-center gap-2 text-slate-600"
            >
              <Upload className="w-8 h-8 text-slate-400" />
              <span className="text-sm">
                {file ? file.name : labels.importExport.chooseFile}
              </span>
              <span className="text-xs text-slate-400">
                .csv, .xlsx, .zip (tối đa 10MB)
              </span>
            </label>
          </div>

          {preview?.sheet_names && preview.sheet_names.length > 1 && (
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1">
                {labels.importExport.sheet}
              </label>
              <select
                className="input-fintech w-full"
                value={sheet ?? ""}
                onChange={(e) => {
                  const newSheet = e.target.value || null;
                  setSheet(newSheet);
                  previewMutation.mutate(newSheet);
                }}
              >
                {preview.sheet_names.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>
          )}

          <button
            onClick={() => previewMutation.mutate(sheet)}
            disabled={!file || previewMutation.isPending || isBusy}
            className="btn-primary w-full"
          >
            {previewMutation.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <FileSpreadsheet className="w-4 h-4" />
            )}
            {labels.importExport.preview}
          </button>

          {preview && (
            <>
              <div className="text-sm text-slate-600">
                {labels.importExport.rowCount}: {preview.row_count}
              </div>

              <div className="space-y-2">
                <h4 className="text-sm font-semibold text-slate-900">
                  {labels.importExport.mapping}
                </h4>
                {preview.headers.map((header) => (
                  <div key={header} className="grid grid-cols-2 gap-2 items-center">
                    <span className="text-sm text-slate-700 truncate" title={header}>
                      {header}
                    </span>
                    <select
                      className="input-fintech text-sm"
                      value={mapping[header] ?? ""}
                      onChange={(e) =>
                        setMapping({ ...mapping, [header]: e.target.value || null })
                      }
                    >
                      <option value="">{labels.importExport.ignore}</option>
                      {targetFields.map((field) => (
                        <option key={field} value={field}>
                          {labels.csvFields[field as keyof typeof labels.csvFields] ?? field}
                        </option>
                      ))}
                    </select>
                  </div>
                ))}
              </div>

              {missingTargets.length > 0 && (
                <div className="text-sm text-amber-600">
                  {labels.importExport.missing}:{" "}
                  {missingTargets
                    .map((t) => labels.csvFields[t as keyof typeof labels.csvFields] ?? t)
                    .join(", ")}
                </div>
              )}

              <button
                onClick={() => importMutation.mutate()}
                disabled={
                  importMutation.isPending ||
                  missingTargets.length > 0 ||
                  isBusy
                }
                className="btn-primary w-full"
              >
                {importMutation.isPending ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Upload className="w-4 h-4" />
                )}
                {labels.importExport.import}
              </button>
            </>
          )}
        </div>
      </FintechCard>
    </div>
  );
}
