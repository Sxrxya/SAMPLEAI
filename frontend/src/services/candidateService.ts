import { apiClient } from "./apiClient";

export const candidateService = {
  getProfile: () => apiClient.get("/candidate/profile"),
  updateProfile: (payload: unknown) =>
    apiClient.patch("/candidate/profile", payload),
  getResumeStatus: (versionId: string) => apiClient.get(`/candidate/resumes/${versionId}/status`),
  uploadResume: (formData: FormData) =>
    apiClient.post("/candidate/resumes", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    }),
  getExtracted: (versionId: string) =>
    apiClient.get(`/candidate/resumes/${versionId}/extracted`),
  reviewExtracted: (
    versionId: string,
    payload: { confirmed: boolean; extraction: unknown },
  ) => apiClient.put(`/candidate/resumes/${versionId}/extracted`, payload),
  updateSharingConsent: (versionId: string, payload: { consent: boolean }) =>
    apiClient.patch(`/candidate/resumes/${versionId}/consent`, payload),
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
