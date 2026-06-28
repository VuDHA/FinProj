import axios from "axios";

const API = axios.create({
  baseURL: "/api/v1",
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
    } else if (!error.response) {
      error.message = "Khong ket noi duoc den may chu. Vui long kiem tra backend.";
    }
    return Promise.reject(error);
  }
);

export default API;
