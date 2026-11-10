import { apiClient } from "./apiClient";

export const recruiterService = {
  getDashboard: () => apiClient.get("/recruiter/dashboard"),
  getApplicants: (
    jobId: string,
    params: { page?: number; page_size?: number; status?: string },
  ) => apiClient.get(`/recruiter/jobs/${jobId}/applicants`, { params }),
  getCandidate: (candidateId: string) =>
    apiClient.get(`/recruiter/candidates/${candidateId}`),
  updateApplicationStatus: (applicationId: string, status: string) =>
    apiClient.patch(`/recruiter/applications/${applicationId}/status`, {
      status,
    }),
  createInterview: (payload: unknown) =>
    apiClient.post("/recruiter/interviews", payload),
};
