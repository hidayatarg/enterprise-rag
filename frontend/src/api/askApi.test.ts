import { afterEach, describe, expect, it, vi } from "vitest";

import { askApi } from "./askApi";
import type { AskRequest, AskResponse } from "./types";

const request: AskRequest = {
  document_id: "18e3b4ed-fcc3-4163-b647-93647b94c9c8",
  question: "How long do approved refunds take?",
  top_k: 5,
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("askApi", () => {
  it("posts a question and returns the answer with its sources", async () => {
    const response: AskResponse = {
      question: request.question,
      answer: "Approved refunds take 5 business days. [1]",
      context_found: true,
      sources: [
        {
          reference: 1,
          filename: "sample-policy.txt",
          page_number: 1,
          chunk_index: 0,
          similarity: 0.65,
        },
      ],
    };
    const fetchMock = vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify(response), { status: 200 }),
      );
    vi.stubGlobal("fetch", fetchMock);

    await expect(askApi.ask(request)).resolves.toEqual(response);

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/documents/ask",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify(request),
      }),
    );
  });

  it("preserves an abstention when context was found", async () => {
    const unsupportedRequest = {
      ...request,
      question: "Which bank processes refunds?",
    };
    const response: AskResponse = {
      question: unsupportedRequest.question,
      answer: "I could not find this information in the provided document.",
      context_found: true,
      sources: [],
    };
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response(JSON.stringify(response), { status: 200 }),
        ),
    );

    await expect(askApi.ask(unsupportedRequest)).resolves.toEqual(response);
  });
});
