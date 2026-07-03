import API from "./client";

export interface SmartImportPreview {
  filename: string;
  sheet_names: string[] | null;
  sheet: string | null;
  headers: string[];
  sample_rows: Record<string, string>[];
  row_count: number;
  suggested_mapping: Record<string, string | null>;
}

export interface SmartImportPayload {
  import_type: "assets" | "transactions";
  mapping: Record<string, string | null>;
  sheet?: string | null;
}

export interface SmartImportResult {
  created: number;
  skipped: number;
  errors: string[];
}

export async function previewSmartImport(
  file: File,
  importType: "assets" | "transactions",
  sheet?: string | null
): Promise<SmartImportPreview> {
  const form = new FormData();
  form.append("file", file);
  form.append("import_type", importType);
  if (sheet) {
    form.append("sheet", sheet);
  }
  const { data } = await API.post("/import-export/smart-preview", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function runSmartImport(
  file: File,
  payload: SmartImportPayload
): Promise<SmartImportResult> {
  const form = new FormData();
  form.append("file", file);
  form.append("payload", JSON.stringify(payload));
  const { data } = await API.post("/import-export/smart-import", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export interface CsvImportResult {
  created: number;
  skipped: number;
  errors: string[];
}

export async function importAssets(file: File): Promise<CsvImportResult> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await API.post("/import-export/import/assets", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function importTransactions(file: File): Promise<CsvImportResult> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await API.post("/import-export/import/transactions", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export function exportAssetsUrl(): string {
  return "/api/v1/import-export/export/assets";
}

export function exportTransactionsUrl(): string {
  return "/api/v1/import-export/export/transactions";
}
