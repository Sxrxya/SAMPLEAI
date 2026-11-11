import { apiClient } from "./apiClient";

export type MatchQuery = { page?: number; page_size?: number; sort?: string; refresh?: boolean };

export const matchingService = {
  getResults: (jobId: string, params: MatchQuery = {}) =>
    apiClient.get(`/recruiter/jobs/${jobId}/matches`, { params }),
  getEvidence: (jobId: string, candidateId: string) =>
    apiClient.get(`/recruiter/jobs/${jobId}/matches/${candidateId}/evidence`),
  compare: (jobId: string, candidateIds: string[]) =>
    apiClient.post(`/recruiter/jobs/${jobId}/matches/compare`, {
      candidate_ids: candidateIds,
    }),
  runMatch: (jobId: string, top_k: number = 5) =>
    apiClient.post(`/recruiter/jobs/${jobId}/matches/run?top_k=${top_k}`),
  quickMatch: (payload: {
    title: string;
    description: string;
    location?: string;
    top_k?: number;
  }) => apiClient.post("/employer/jobs/quick-match", payload),
};
