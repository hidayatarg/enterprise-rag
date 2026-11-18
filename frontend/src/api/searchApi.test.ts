
import {
    afterEach,
    describe,
    expect,
    it,
    vi,
} from "vitest";

import { searchApi } from "./searchApi";

afterEach(() => {
    vi.unstubAllGlobals();
});

describe("searchApi", () => {
    it("sends the correct semantic search request", async () => {
        const mockResponse = {
            question: "How long do refunds take?",
            results: [
                {
                    content: "Approved refunds are processed within 5 business days.",
                    filename: "sample-policy.txt",
                    page_number: null,
                    chunk_index: 0,
                    distance: 0.08,
                    similarity: 0.92,
                },
            ],
        };

        const fetchMock = vi.fn().mockResolvedValue(
            new Response(
                JSON.stringify(mockResponse),
                {
                    status: 200,
                    headers: {
                        "Content-Type": "application/json",
                    },
                },
            ),
        );

        vi.stubGlobal("fetch", fetchMock);

        const request = {
            document_id: "18e3b4ed-fcc3-4163-b647-93647b94c9c8",
            question: "How long do refunds take?",
            top_k: 5,
        };

        const result = await searchApi.search(request);

        expect(fetchMock).toHaveBeenCalledWith(
            "/api/v1/documents/search",
            expect.objectContaining({
                method: "POST",
                body: JSON.stringify(request),
            }),
        );

        expect(result.results).toHaveLength(1);
        expect(result.results[0].similarity).toBe(0.92);
    });

    it("handles an empty search result", async () => {
        vi.stubGlobal(
            "fetch",
            vi.fn().mockResolvedValue(
                new Response(
                    JSON.stringify({
                        question: "Unknown policy?",
                        results: [],
                    }),
                    { status: 200 },
                ),
            ),
        );

        const result = await searchApi.search({
            document_id: "18e3b4ed-fcc3-4163-b647-93647b94c9c8",
            question: "Unknown policy?",
            top_k: 5,
            
        });

        expect(result.results).toEqual([]);
    });
});
