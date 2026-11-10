import { apiClient } from "./apiClient";

export const adminService = {
  getDashboard: () => apiClient.get("/admin/dashboard"),
  getUsers: (params: {
    role?: string;
    page?: number;
    page_size?: number;
    search?: string;
  }) => apiClient.get("/admin/users", { params }),
  getVerificationQueue: (params: { page?: number; page_size?: number }) =>
    apiClient.get("/admin/verifications", { params }),
  getProcessingHealth: () => apiClient.get("/admin/processing/health"),
  getAuditEvents: (params: {
    page?: number;
    page_size?: number;
    actor_id?: string;
  }) => apiClient.get("/admin/audit-events", { params }),
};
