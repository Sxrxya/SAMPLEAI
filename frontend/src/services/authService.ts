import { apiClient } from "./apiClient";
import { tokenStore } from "./tokenStore";
import type { Role } from "../types";

export type Credentials = { email: string; password: string };

export type UserResponse = {
  id: string;
  email: string;
  display_name: string;
  role: Role;
};

export type TokenResponse = {
  access_token: string;
  token_type: "bearer";
  expires_at: string;
  user: UserResponse;
};

export const authService = {
  async login(credentials: Credentials): Promise<TokenResponse> {
    const { data } = await apiClient.post<TokenResponse>(
      "/auth/login",
      credentials,
    );
    tokenStore.set(data.access_token);
    return data;
  },

  async logout(): Promise<void> {
    try {
      await apiClient.post("/auth/logout");
    } finally {
      tokenStore.set(null);
    }
  },

  async registerCandidate(payload: {
    display_name: string;
    email: string;
    password: string;
  }): Promise<TokenResponse> {
    const { data } = await apiClient.post<TokenResponse>("/auth/register", payload);
    if (data?.access_token) {
      tokenStore.set(data.access_token);
    }
    return data;
  },

  async registerRecruiter(payload: {
    display_name: string;
    email: string;
    password: string;
    organization_name: string;
  }): Promise<TokenResponse> {
    const { data } = await apiClient.post<TokenResponse>("/auth/register/recruiter", payload);
    if (data?.access_token) {
      tokenStore.set(data.access_token);
    }
    return data;
  },

  // Backwards compatibility alias
  async register(payload: {
    display_name: string;
    email: string;
    password: string;
  }): Promise<TokenResponse> {
    return this.registerCandidate(payload);
  },

  async getSession(): Promise<UserResponse> {
    const { data } = await apiClient.get<UserResponse>("/auth/session");
    return data;
  },
};
