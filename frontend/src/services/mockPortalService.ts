import {
  activitySeries,
  demoJobs,
  demoMatches,
  demoRows,
  metricSets,
} from "../mocks/data";
import type { Role } from "../types";

export const mockPortalService = {
  getMetrics: (role: Role) => metricSets[role],
  getRows: (role: Role) => demoRows[role],
  getMatches: () => demoMatches,
  getJobs: () => demoJobs,
  getActivity: () => activitySeries,
};
