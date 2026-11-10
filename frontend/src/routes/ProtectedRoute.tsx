import { Navigate, useParams } from "react-router-dom";
import { useSessionStore } from "../store/session";
import type { Role } from "../types";

const roles: Role[] = ["candidate", "recruiter", "admin"];

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { role } = useParams<{ role: string }>();
  const activeRole = useSessionStore((state) => state.role);

  if (!role || !roles.includes(role as Role))
    return <Navigate to="/" replace />;
  if (activeRole !== role) return <Navigate to={`/login/${role}`} replace />;
  return children;
}
