import axios, { AxiosInstance } from "axios";
import { clearAdminSession, getAdminToken } from "./auth";

function createClient(): AxiosInstance {
  const client = axios.create({ baseURL: "" });
  client.interceptors.request.use((config) => {
    const token = getAdminToken();
    if (token) {
      config.headers = config.headers ?? {};
      (config.headers as Record<string, string>)["Authorization"] = `Bearer ${token}`;
    }
    return config;
  });
  client.interceptors.response.use(
    (r) => r,
    (err) => {
      if (err.response?.status === 401) clearAdminSession();
      return Promise.reject(err);
    }
  );
  return client;
}

export const api = createClient();
