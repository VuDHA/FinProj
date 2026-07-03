import API from "./client";

export interface AssetTypeConfig {
  label: string;
  fields: string[];
  marketPrice: boolean;
}

export type AssetTypeMap = Record<string, AssetTypeConfig>;

export interface AssetTypePayload {
  types: AssetTypeMap;
}

export interface AllocationTarget {
  type: string;
  target_percent: number;
}

export interface Setting {
  key: string;
  value: string;
}

export interface EnvConfigItem {
  key: string;
  value: string;
  type: string;
  requires_restart?: boolean;
  description: string;
}

export interface SourceInfo {
  code: string;
  name: string;
  description: string;
  supports_history: boolean;
  supports_listing: boolean;
}

export async function getAssetTypes(): Promise<AssetTypeMap> {
  const { data } = await API.get<AssetTypePayload>("/settings/asset-types");
  return data.types;
}

export async function saveAssetTypes(payload: AssetTypeMap): Promise<AssetTypeMap> {
  const { data } = await API.post<AssetTypePayload>("/settings/asset-types", { types: payload });
  return data.types;
}

export async function getAllocationTargets(): Promise<AllocationTarget[]> {
  const { data } = await API.get("/settings/allocation-targets/");
  return data;
}

export async function saveAllocationTargets(
  payload: AllocationTarget[]
): Promise<AllocationTarget[]> {
  const { data } = await API.post("/settings/allocation-targets/", payload);
  return data;
}

export async function getEnvConfig(): Promise<EnvConfigItem[]> {
  const { data } = await API.get("/settings/env-config");
  return data;
}

export async function saveEnvConfig(payload: Record<string, string>): Promise<EnvConfigItem[]> {
  const { data } = await API.post("/settings/env-config", payload);
  return data;
}

export async function getSourcesForType(assetType: string): Promise<SourceInfo[]> {
  const { data } = await API.get(`/settings/sources/${assetType}`);
  return data;
}

export async function getDefaultSources(): Promise<Record<string, string>> {
  const { data } = await API.get("/settings/default-sources");
  return data;
}

export async function saveDefaultSources(
  payload: Record<string, string>
): Promise<Record<string, string>> {
  const { data } = await API.post("/settings/default-sources", payload);
  return data;
}

export async function getSettings(): Promise<Setting[]> {
  const { data } = await API.get("/settings/");
  return data;
}

export async function saveSetting(payload: Setting): Promise<Setting> {
  const { data } = await API.post("/settings/", payload);
  return data;
}

export async function getSetting(key: string): Promise<Setting> {
  const { data } = await API.get(`/settings/${key}`);
  return data;
}
