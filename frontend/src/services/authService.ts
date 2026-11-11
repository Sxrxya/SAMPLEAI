import { apiClient } from "./apiClient";
import { tokenStore } from "./tokenStore";

export type Credentials = { email: string; password: string };
export type AuthResponse = {
  access_token: string;
  token_type: "bearer";
  role: "candidate" | "recruiter" | "admin";
};

export const authService = {
  async login(credentials: Credentials) {
    const { data } = await apiClient.post<AuthResponse>(
      "/auth/login",
      credentials,
    );
    tokenStore.set(data.access_token);
    return data;
  },
  async logout() {
    try {
      await apiClient.post("/auth/logout");
    } finally {
      tokenStore.set(null);
    }
  },
  async register(payload: {
    display_name: string;
    email: string;
    password: string;
  }) {
    const { data } = await apiClient.post<any>("/auth/register", payload);
    if (data?.access_token) {
      tokenStore.set(data.access_token);
    }
    return data;
  },
};
