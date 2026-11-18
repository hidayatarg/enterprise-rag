
import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import {
    Search,
    FileText,
    Loader2,
    AlertCircle,
    RefreshCw,
} from "lucide-react";

import { documentsApi } from "../api/documentsApi";
import { searchApi } from "../api/searchApi";

import type {
    DocumentListItem,
    SearchResponse,
} from "../api/types";

export function SearchPage() {
    const [documents, setDocuments] = useState<DocumentListItem[]>([]);
    const [documentsLoading, setDocumentsLoading] = useState(true);
    const [documentsError, setDocumentsError] = useState<string | null>(null);

    const [documentId, setDocumentId] = useState("");
    const [question, setQuestion] = useState("");
    const [topK, setTopK] = useState(5);

    const [searching, setSearching] = useState(false);
    const [searchError, setSearchError] = useState<string | null>(null);
    const [response, setResponse] = useState<SearchResponse | null>(null);

    const [refreshKey, setRefreshKey] = useState(0);

    useEffect(() => {
        let active = true;

        async function loadDocuments() {
            try {
                const result = await documentsApi.getAll();

                if (!active) return;

                setDocuments(result.documents);
                setDocumentsError(null);
                setDocumentId((current) =>
                    result.documents.some((doc) => doc.id === current)
                        ? current
                        : result.documents[0]?.id ?? "",
                );
            } catch (err) {
                if (!active) return;

                setDocumentsError(
                    err instanceof Error
                        ? err.message
                        : "Unable to load documents.",
                );
            } finally {
                if (active) {
                    setDocumentsLoading(false);
                }
            }
        }

        void loadDocuments();

        return () => {
            active = false;
        };
    }, [refreshKey]);

    async function handleSearch(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();

        if (!documentId || !question.trim() || searching) return;

        setSearching(true);
        setSearchError(null);
        setResponse(null);

        try {
            const result = await searchApi.search({
                document_id: documentId,
                question: question.trim(),
                top_k: topK,
            });

            setResponse(result);
        } catch (err) {
            setSearchError(
                err instanceof Error
                    ? err.message
                    : "Semantic search failed.",
            );
        } finally {
            setSearching(false);
        }
    }

    function handleRefresh() {
        setDocumentsLoading(true);
        setRefreshKey((current) => current + 1);
    }

    return (
        <div className="mx-auto max-w-5xl space-y-8">
            <div>
                <h1 className="text-2xl font-bold text-slate-900">
                    Semantic Search
                </h1>

                <p className="mt-2 text-slate-600">
                    Search indexed documents using natural-language questions
                    and vector similarity.
                </p>
            </div>

            <form
                onSubmit={(event) => void handleSearch(event)}
                className="space-y-5 rounded-xl border border-slate-200 bg-white p-6"
            >
                <div className="flex items-center justify-between">
                    <label
                        htmlFor="search-document"
                        className="text-sm font-medium text-slate-700"
                    >
                        Document
                    </label>

                    <button
                        type="button"
                        onClick={handleRefresh}
                        disabled={documentsLoading}
                        aria-label="Refresh documents"
                        className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 disabled:opacity-50"
                    >
                        <RefreshCw
                            size={18}
                            className={
                                documentsLoading ? "animate-spin" : ""
                            }
                        />
                    </button>
                </div>

                <select
                    id="search-document"
                    value={documentId}
                    onChange={(event) => {
                        setDocumentId(event.target.value);
                        setResponse(null);
                    }}
                    disabled={documentsLoading || documents.length === 0}
                    className="w-full rounded-lg border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 focus:border-indigo-500 focus:outline-none"
                >
                    {documents.length === 0 && (
                        <option value="">
                            {documentsLoading
                                ? "Loading documents..."
                                : "No documents available"}
                        </option>
                    )}

                    {documents.map((document) => (
                        <option key={document.id} value={document.id}>
                            {document.filename}
                        </option>
                    ))}
                </select>

                {documentsError && (
                    <p role="alert" className="text-sm text-red-600">
                        {documentsError}
                    </p>
                )}

                <div>
                    <label
                        htmlFor="search-question"
                        className="mb-2 block text-sm font-medium text-slate-700"
                    >
                        Search question
                    </label>

                    <textarea
                        id="search-question"
                        value={question}
                        onChange={(event) => setQuestion(event.target.value)}
                        rows={3}
                        maxLength={4000}
                        placeholder="How long does it take to process approved refunds?"
                        className="w-full resize-y rounded-lg border border-slate-300 px-4 py-3 text-sm text-slate-900 focus:border-indigo-500 focus:outline-none"
                    />
                </div>

                <div>
                    <label
                        htmlFor="search-top-k"
                        className="mb-2 block text-sm font-medium text-slate-700"
                    >
                        Maximum results
                    </label>

                    <select
                        id="search-top-k"
                        value={topK}
                        onChange={(event) =>
                            setTopK(Number(event.target.value))
                        }
                        className="w-full rounded-lg border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 focus:border-indigo-500 focus:outline-none"
                    >
                        {[1, 3, 5, 10, 20].map((value) => (
                            <option key={value} value={value}>
                                {value}
                            </option>
                        ))}
                    </select>
                </div>

                <button
                    type="submit"
                    disabled={
                        searching ||
                        documentsLoading ||
                        !documentId ||
                        !question.trim()
                    }
                    className="flex items-center justify-center gap-2 rounded-lg bg-indigo-600 px-5 py-3 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                    {searching ? (
                        <>
                            <Loader2 size={18} className="animate-spin" />
                            Searching...
                        </>
                    ) : (
                        <>
                            <Search size={18} />
                            Search document
                        </>
                    )}
                </button>
            </form>

            {searchError && (
                <div
                    role="alert"
                    className="flex items-center gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-red-700"
                >
                    <AlertCircle size={20} />
                    <p className="text-sm">{searchError}</p>
                </div>
            )}

            {response && (
                <section className="space-y-4">
                    <div className="flex items-center justify-between">
                        <h2 className="text-lg font-semibold text-slate-900">
                            Matching chunks
                        </h2>

                        <span className="text-sm text-slate-500">
                            {response.results.length} results
                        </span>
                    </div>

                    {response.results.length === 0 && (
                        <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-slate-500">
                            No matching chunks found.
                        </div>
                    )}

                    {response.results.map((result, index) => (
                        <article
                            key={`${result.chunk_index}-${index}`}
                            className="space-y-3 rounded-xl border border-slate-200 bg-white p-5"
                        >
                            <div className="flex items-center justify-between gap-3">
                                <h3 className="font-semibold text-slate-900">
                                    Result #{index + 1}
                                </h3>

                                <span className="rounded-full bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-700">
                                    Similarity: {result.similarity.toFixed(3)}
                                </span>
                            </div>

                            <p className="whitespace-pre-wrap text-sm leading-7 text-slate-700">
                                {result.content}
                            </p>

                            <div className="flex flex-wrap items-center gap-3 border-t border-slate-100 pt-3 text-xs text-slate-500">
                                <span className="flex items-center gap-1">
                                    <FileText size={14} />
                                    {result.filename}
                                </span>

                                {result.page_number !== null && (
                                    <span>
                                        Page {result.page_number}
                                    </span>
                                )}

                                <span>
                                    Chunk {result.chunk_index}
                                </span>

                                <span>
                                    Distance: {result.distance.toFixed(3)}
                                </span>
                            </div>
                        </article>
                    ))}
                </section>
            )}
        </div>
    );
}
