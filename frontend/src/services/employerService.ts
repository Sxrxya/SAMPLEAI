import { apiClient } from "./apiClient";

export const employerService = {
  getCompany: () => apiClient.get("/employer/company"),
  updateCompany: (payload: unknown) =>
    apiClient.patch("/employer/company", payload),
  createJob: (payload: unknown) => apiClient.post("/employer/jobs", payload),
  getJobs: (params: { page?: number; page_size?: number; status?: string }) =>
    apiClient.get("/employer/jobs", { params }),
  updateJob: (jobId: string, payload: unknown) =>
    apiClient.patch(`/employer/jobs/${jobId}`, payload),
};
