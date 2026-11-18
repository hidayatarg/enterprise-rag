
import { apiRequest } from "./client";

import type { SearchRequest, SearchResponse } from "./types";

export const searchApi = {
    search(request: SearchRequest): Promise<SearchResponse> {
        return apiRequest<SearchResponse>(
            "/documents/search",
            {
                method: "POST",
                body: request,
            },
        );
    },
};
