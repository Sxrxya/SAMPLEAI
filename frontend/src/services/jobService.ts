import { apiClient } from "./apiClient";

export const jobService = {
  getDescription: (jobId: string) =>
    apiClient.get(`/employer/jobs/${jobId}/description`),
  reviewDescription: (jobId: string, payload: unknown) =>
    apiClient.put(`/employer/jobs/${jobId}/description`, payload),
  uploadDescription: (jobId: string, file: File) => {
    const body = new FormData();
    body.append("file", file);
    return apiClient.post(`/employer/jobs/${jobId}/description/upload`, body);
  },
};
