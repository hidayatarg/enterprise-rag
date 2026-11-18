// TypeScript interfaces provide compile-time checking, not runtime validation.
// If FastAPI changes its response shape, TypeScript won't automatically detect
// that at runtime. We'll add contract validation
export interface HealthResponse {
  status: string;
}

export interface UploadResponse {
  document_id: string;
  filename: string;
  chunks_created: number;
  status: string;
}

export interface SearchRequest {
  document_id: string;
  question: string;
  top_k?: number;
}

export interface SearchResult {
  content: string;
  filename: string;
  page_number: number | null; // pdf file may contain multiple pages
  chunk_index: number;
  distance: number;
  similarity: number;
}

export interface SearchResponse {
  question: string;
  results: SearchResult[];
}

export interface AskRequest {
  document_id: string;
  question: string;
  top_k?: number;
}

export interface CitationSource {
  reference: number;
  filename: string;
  page_number: number;
  chunk_index: number;
  similarity: number;
}

export interface AskResponse {
  question: string;
  answer: string;
  context_found: boolean;
  sources: CitationSource[];
}

export interface DocumentListItem {
  id: string;
  filename: string;
  content_type: string;
  created_at: string;
  chunk_count: number;
}

export interface DocumentListResponse {
  documents: DocumentListItem[];
  total: number;
}

export interface DocumentDeleteResponse {
  document_id: string;
  deleted: boolean;
}
