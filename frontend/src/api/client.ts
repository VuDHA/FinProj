import axios from "axios";
import { labels } from "../i18n/vi";

const API = axios.create({
  baseURL: "/api/v1",
  timeout: 30000,
});

API.interceptors.response.use(
  (response) => response,
  (error) => {
    const detail = error.response?.data?.detail;
    if (detail) {
      error.message = detail;
    } else if (error.code === "ECONNABORTED" || error.code === "ETIMEDOUT") {
      error.message = labels.errors.timeout;
    } else if (!error.response) {
      error.message = labels.errors.networkError;
    }
    return Promise.reject(error);
  }
);

export default API;
