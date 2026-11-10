import { create } from "zustand";
import type { Role } from "../types";

type SessionState = {
  role: Role | null;
  signIn: (role: Role) => void;
  signOut: () => void;
};

export const useSessionStore = create<SessionState>((set) => ({
  role: null,
  signIn: (role) => set({ role }),
  signOut: () => set({ role: null }),
}));
