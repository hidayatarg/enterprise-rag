import { apiRequest } from "./client";
import type { UploadResponse } from "./types";

export const documentsApi = {
  upload(file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append("file", file);

    return apiRequest<UploadResponse>("/documents/upload", {
      method: "POST",
      body: formData,
    });
  },
};
