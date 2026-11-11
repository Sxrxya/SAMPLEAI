import { apiClient } from "./apiClient";

export const applicationService = {
  list: (params: { page?: number; page_size?: number; status?: string } = {}) =>
    apiClient.get("/candidate/applications", { params }),
  get: (applicationId: string) =>
    apiClient.get(`/candidate/applications/${applicationId}`),
  withdraw: (applicationId: string) =>
    apiClient.post(`/candidate/applications/${applicationId}/withdraw`),
  apply: (jobId: string, resumeVersionId: string) =>
    apiClient.post(`/candidate/jobs/${jobId}/applications`, {
      resume_version_id: resumeVersionId,
      consent_to_recruiter_sharing: true,
    }),
};
