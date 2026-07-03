import API from "./client";

export interface Asset {
  id: number;
  symbol: string;
  name: string;
  type: string;
  exchange?: string | null;
  currency?: string;
  source?: string | null;
  is_active: boolean;
}

export interface AssetCreate {
  symbol?: string;
  name: string;
  type: string;
  exchange?: string;
  currency?: string;
  source?: string | null;
  manual_value?: number;
}

export async function getAssets(): Promise<Asset[]> {
  const { data } = await API.get("/assets/");
  return data;
}

export async function createAsset(payload: AssetCreate): Promise<Asset> {
  const { data } = await API.post("/assets/", payload);
  return data;
}

export async function deleteAsset(id: number): Promise<void> {
  await API.delete(`/assets/${id}`);
}
