import { apiClient } from "./apiClient";

export const notificationService = {
  list: (params: {
    page?: number;
    page_size?: number;
    unread_only?: boolean;
  }) => apiClient.get("/notifications", { params }),
  markRead: (notificationId: string) =>
    apiClient.patch(`/notifications/${notificationId}/read`),
};
