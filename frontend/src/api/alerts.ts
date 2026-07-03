import API from "./client";

export interface PriceAlert {
  id: number;
  asset_id: number;
  symbol?: string | null;
  name?: string | null;
  type: "STOP_LOSS" | "TAKE_PROFIT";
  value_type: "VALUE" | "PERCENT";
  value: number;
  reference_price?: number | null;
  is_active: boolean;
  created_at?: string | null;
  resolved_at?: string | null;
}

export interface PriceAlertNotification {
  id: number;
  asset_id: number;
  symbol: string;
  name: string;
  type: "STOP_LOSS" | "TAKE_PROFIT";
  value_type: "VALUE" | "PERCENT";
  value: number;
  reference_price?: number | null;
  current_price: number;
  message: string;
}

export interface CreatePriceAlertRequest {
  asset_id: number;
  type: "STOP_LOSS" | "TAKE_PROFIT";
  value_type: "VALUE" | "PERCENT";
  value: number;
}

export async function getAlerts(): Promise<PriceAlert[]> {
  const { data } = await API.get("/alerts/");
  return data;
}

export async function getNotifications(): Promise<PriceAlertNotification[]> {
  const { data } = await API.get("/alerts/notifications");
  return data;
}

export async function createAlert(payload: CreatePriceAlertRequest): Promise<PriceAlert> {
  const { data } = await API.post("/alerts/", payload);
  return data;
}

export async function deleteAlert(id: number): Promise<void> {
  await API.delete(`/alerts/${id}`);
}

export async function resolveAlert(id: number): Promise<PriceAlert> {
  const { data } = await API.post(`/alerts/${id}/resolve`);
  return data;
}
