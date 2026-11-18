import { apiRequest } from "./client";
import type { AskRequest, AskResponse } from "./types";

export const askApi = {
  ask(request: AskRequest): Promise<AskResponse> {
    return apiRequest<AskResponse>("/documents/ask", {
      method: "POST",
      body: request,
    });
  },
};
