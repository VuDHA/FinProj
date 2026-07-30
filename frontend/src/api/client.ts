import axios from "axios";
import { labels } from "../i18n/vi";

const baseURL = import.meta.env.DEV
  ? "/api/v1"
  : "http://127.0.0.1:8000/api/v1";

export { baseURL as API_BASE_URL };

const API = axios.create({
  baseURL,
  timeout: 30000,
});

export function extractDetailMessage(detail: any): string | null {
  if (!detail) return null;
  if (typeof detail === "string") return detail;
  if (typeof detail === "object") {
    if (detail.message) return detail.message;
    if (detail.msg) return detail.msg;
    return JSON.stringify(detail);
  }
  return String(detail);
}

API.interceptors.response.use(
  (response) => response,
  (error) => {
    const detail = error.response?.data?.detail;
    const message = extractDetailMessage(detail);
    if (message) {
      error.message = message;
    } else if (error.code === "ECONNABORTED" || error.code === "ETIMEDOUT") {
      error.message = labels.errors.timeout;
    } else if (!error.response) {
      error.message = labels.errors.networkError;
    }
    return Promise.reject(error);
  }
);

export default API;
