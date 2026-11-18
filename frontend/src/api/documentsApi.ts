import { apiRequest } from "./client";

import type {
  UploadResponse,
  DocumentListResponse,
  DocumentDeleteResponse,
} from "./types";

export const documentsApi = {
  upload(file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append("file", file);

    return apiRequest<UploadResponse>("/documents/upload", {
      method: "POST",
      body: formData,
    });
  },

  getAll(): Promise<DocumentListResponse> {
    return apiRequest<DocumentListResponse>("/documents");
  },

  delete(documentId: string): Promise<DocumentDeleteResponse> {
    return apiRequest<DocumentDeleteResponse>(
      `/documents/${encodeURIComponent(documentId)}`,
      {
        method: "DELETE",
      },
    );
  },
};
