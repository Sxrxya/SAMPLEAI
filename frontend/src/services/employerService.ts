import { apiClient } from "./apiClient";

export const employerService = {
  getCompany: () => apiClient.get("/employer/company"),
  updateCompany: (payload: unknown) =>
    apiClient.patch("/employer/company", payload),
  createJob: (payload: unknown) => apiClient.post("/employer/jobs", payload),
  getJobs: (params: { page?: number; page_size?: number; status?: string } = {}) =>
    apiClient.get("/employer/jobs", { params }),
  updateJob: (jobId: string, payload: unknown) =>
    apiClient.patch(`/employer/jobs/${jobId}`, payload),
  quickMatch: (payload: { title: string; description: string; location?: string; top_k?: number }) =>
    apiClient.post<{ job_id: string; title: string; location: string | null; items: any[]; total: number }>(
      "/employer/jobs/quick-match",
      payload
    ),
  getJobMatches: (jobId: string, topK: number = 5) =>
    apiClient.get<{ job_id: string; job_title: string; location: string | null; items: any[]; total: number }>(
      `/recruiter/jobs/${jobId}/matches?top_k=${topK}`
    ),
  getJobDetails: (jobId: string) =>
    apiClient.get(`/employer/jobs/${jobId}/description`),
};
