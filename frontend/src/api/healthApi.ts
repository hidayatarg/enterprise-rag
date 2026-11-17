
import { apiRequest } from "./client";
import type { HealthResponse } from "./types";

export const healthApi = {
  getStatus(): Promise<HealthResponse> {
    return apiRequest<HealthResponse>("/health");
  },
};
