import { apiClient } from "./apiClient";

export const resumeService = {
  upload(file: File, onProgress?: (percent: number) => void) {
    const body = new FormData();
    body.append("file", file);
    return apiClient.post("/candidate/resumes", body, {
      onUploadProgress: (event) => {
        if (event.total)
          onProgress?.(Math.round((event.loaded * 100) / event.total));
      },
    });
  },
  getExtractedInformation: (resumeId: string) =>
    apiClient.get(`/candidate/resumes/${resumeId}/extracted`),
  reviewExtractedInformation: (resumeId: string, payload: unknown) =>
    apiClient.put(`/candidate/resumes/${resumeId}/extracted`, payload),
  updateConsent: (resumeId: string, consent: boolean) =>
    apiClient.patch(`/candidate/resumes/${resumeId}/consent`, { consent }),
};
