
import {
  afterEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import { apiRequest, ApiError } from "./client";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("apiRequest", () => {
  it("returns parsed JSON on success", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({ status: "ok" }),
        {
          status: 200,
          headers: {
            "Content-Type": "application/json",
          },
        },
      ),
    );

    vi.stubGlobal("fetch", fetchMock);

    const result = await apiRequest<{ status: string }>(
      "/health",
    );

    expect(result.status).toBe("ok");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/health",
      expect.any(Object),
    );
  });

  it("throws ApiError for HTTP failures", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            detail: "Document not found",
          }),
          { status: 404 },
        ),
      ),
    );

    await expect(
      apiRequest("/documents/missing"),
    ).rejects.toMatchObject({
      name: "ApiError",
      status: 404,
      message: "Document not found",
    });
  });

  it("handles connection failures", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(
        new TypeError("Failed to fetch"),
      ),
    );

    await expect(
      apiRequest("/health"),
    ).rejects.toBeInstanceOf(ApiError);
  });

  it("sends JSON request bodies", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({ success: true }),
        { status: 200 },
      ),
    );

    vi.stubGlobal("fetch", fetchMock);

    await apiRequest("/test", {
      method: "POST",
      body: { question: "Hello" },
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/test",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          question: "Hello",
        }),
      }),
    );
  });
});
