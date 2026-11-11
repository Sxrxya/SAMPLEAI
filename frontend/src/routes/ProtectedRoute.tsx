import { Navigate, useParams } from "react-router-dom";
import { tokenStore } from "../services/tokenStore";
import { useSessionStore } from "../store/session";
import type { Role } from "../types";

const roles: Role[] = ["candidate", "recruiter", "admin"];

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { role } = useParams<{ role: string }>();
  const activeRole = useSessionStore((state) => state.role);
  const token = tokenStore.get();

  if (!role || !roles.includes(role as Role)) {
    return <Navigate to="/" replace />;
  }

  // If no auth token, redirect to login
  if (!token) {
    return <Navigate to={`/login/${role}`} replace />;
  }

  // Prevent URL role manipulation: candidate cannot access /portal/recruiter/*, recruiter cannot access /portal/candidate/*
  if (activeRole && activeRole !== role) {
    return <Navigate to={`/portal/${activeRole}/overview`} replace />;
  }

  return children;
}
