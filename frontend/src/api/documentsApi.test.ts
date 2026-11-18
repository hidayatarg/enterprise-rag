import { afterEach, describe, expect, it, vi } from "vitest";

import { documentsApi } from "./documentsApi";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("documentsApi", () => {
  it("uploads a document using multipart form data", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          document_id: "test-document-id",
          filename: "policy.txt",
          chunks_created: 2,
        }),
        {
          status: 200,
          headers: {
            "Content-Type": "application/json",
          },
        },
      ),
    );

    vi.stubGlobal("fetch", fetchMock);

    const file = new File(["Refund policy"], "policy.txt", {
      type: "text/plain",
    });

    const result = await documentsApi.upload(file);

    expect(result.filename).toBe("policy.txt");
    expect(result.chunks_created).toBe(2);

    const [url, options] = fetchMock.mock.calls[0];

    expect(url).toBe("/api/v1/documents/upload");
    expect(options.method).toBe("POST");
    expect(options.body).toBeInstanceOf(FormData);

    const formData = options.body as FormData;

    expect(formData.get("file")).toBe(file);

    const headers = options.headers as Headers;

    expect(headers.has("Content-Type")).toBe(false);
  });

  it("lists indexed documents", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            documents: [],
            total: 0,
          }),
          { status: 200 },
        ),
      ),
    );

    const response = await documentsApi.getAll();

    expect(response.documents).toEqual([]);
    expect(response.total).toBe(0);
  });

  it("deletes a document", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          document_id: "test-id",
          deleted: true,
        }),
        { status: 200 },
      ),
    );

    vi.stubGlobal("fetch", fetchMock);

    const response = await documentsApi.delete("test-id");

    expect(response.deleted).toBe(true);

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/documents/test-id",
      expect.objectContaining({
        method: "DELETE",
      }),
    );
  });
});
