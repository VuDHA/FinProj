import axios from "axios";

const API = axios.create({
  baseURL: "/api/v1",
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
  },
});

API.interceptors.response.use(
  (response) => response,
  (error) => {
    const detail = error.response?.data?.detail;
    if (detail) {
      error.message = detail;
    } else if (error.code === "ECONNABORTED" || error.code === "ETIMEDOUT") {
      error.message = "Yeu cau qua thoi gian. Vui long thu lai.";
    } else if (!error.response) {
      error.message = "Khong ket noi duoc den may chu. Vui long kiem tra backend.";
    }
    return Promise.reject(error);
  }
);

export default API;
