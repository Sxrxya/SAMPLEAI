import { create } from "zustand";
import { apiClient } from "../services/apiClient";
import { tokenStore } from "../services/tokenStore";
import type { Role } from "../types";

export type UserSession = {
  id: string;
  email: string;
  display_name: string;
  role: Role;
};

type SessionState = {
  user: UserSession | null;
  role: Role | null;
  isLoading: boolean;
  signIn: (userOrRole: UserSession | Role) => void;
  signOut: () => Promise<void>;
  checkSession: () => Promise<UserSession | null>;
};

const SESSION_KEY = "tandem_user_session";

function getStoredSession(): UserSession | null {
  try {
    const raw = localStorage.getItem(SESSION_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

const initialUser = getStoredSession();

export const useSessionStore = create<SessionState>((set) => ({
  user: initialUser,
  role: initialUser?.role || null,
  isLoading: false,

  signIn: (userOrRole: UserSession | Role) => {
    const user: UserSession =
      typeof userOrRole === "string"
        ? {
            id: `demo-${userOrRole}`,
            email: `${userOrRole}@tandem.test`,
            display_name:
              userOrRole === "recruiter"
                ? "Demo Recruiter"
                : userOrRole === "candidate"
                ? "Demo Candidate"
                : "Demo Admin",
            role: userOrRole,
          }
        : userOrRole;
    try {
      localStorage.setItem(SESSION_KEY, JSON.stringify(user));
    } catch {
      // ignore storage error
    }
    set({ user, role: user.role });
  },

  signOut: async () => {
    try {
      await apiClient.post("/auth/logout");
    } catch {
      // ignore network error on logout
    } finally {
      tokenStore.set(null);
      try {
        localStorage.removeItem(SESSION_KEY);
      } catch {
        // ignore
      }
      set({ user: null, role: null });
    }
  },

  checkSession: async () => {
    const token = tokenStore.get();
    if (!token) {
      set({ user: null, role: null });
      return null;
    }
    set({ isLoading: true });
    try {
      const { data } = await apiClient.get<UserSession>("/auth/session");
      const user: UserSession = {
        id: data.id,
        email: data.email,
        display_name: data.display_name,
        role: data.role,
      };
      localStorage.setItem(SESSION_KEY, JSON.stringify(user));
      set({ user, role: user.role, isLoading: false });
      return user;
    } catch {
      tokenStore.set(null);
      localStorage.removeItem(SESSION_KEY);
      set({ user: null, role: null, isLoading: false });
      return null;
    }
  },
}));
