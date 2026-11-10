import { apiClient } from "./apiClient";

export const candidateService = {
  getProfile: () => apiClient.get("/candidate/profile"),
  updateProfile: (payload: unknown) =>
    apiClient.patch("/candidate/profile", payload),
  getResumeStatus: () => apiClient.get("/candidate/resumes/status"),
  getJobs: (params: {
    page?: number;
    page_size?: number;
    search?: string;
    location?: string;
  }) => apiClient.get("/candidate/jobs", { params }),
  getApplications: (params: { page?: number; page_size?: number }) =>
    apiClient.get("/candidate/applications", { params }),
  submitApplication: (
    jobId: string,
    payload: { resume_id: string; consent: boolean },
  ) => apiClient.post(`/candidate/jobs/${jobId}/applications`, payload),
};
