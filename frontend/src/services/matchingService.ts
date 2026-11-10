import { apiClient } from "./apiClient";

export type MatchQuery = { page?: number; page_size?: number; sort?: string };

export const matchingService = {
  getResults: (jobId: string, params: MatchQuery = {}) =>
    apiClient.get(`/recruiter/jobs/${jobId}/matches`, { params }),
  getEvidence: (jobId: string, candidateId: string) =>
    apiClient.get(`/recruiter/jobs/${jobId}/matches/${candidateId}/evidence`),
  compare: (jobId: string, candidateIds: string[]) =>
    apiClient.post(`/recruiter/jobs/${jobId}/matches/compare`, {
      candidate_ids: candidateIds,
    }),
};
