
import { useEffect, useRef, useState } from "react";
import {
    FileText,
    RefreshCw,
    Trash2,
    Loader2,
} from "lucide-react";

import { documentsApi } from "../../api/documentsApi";
import type { DocumentListItem } from "../../api/types";

type DocumentListProps = {
    refreshKey: number;
};

type DocumentsState = {
    documents: DocumentListItem[];
    error: string | null;
    loadedKey: number | null;
    loading: boolean;
};

export function DocumentList({ refreshKey }: DocumentListProps) {
    const [state, setState] = useState<DocumentsState>({
        documents: [],
        error: null,
        loadedKey: null,
        loading: true,
    });

    const [manualRefreshKey, setManualRefreshKey] = useState(0);
    const [deletingId, setDeletingId] = useState<string | null>(null);
    const requestIdRef = useRef(0);

    // A new key identifies each list request.
    const requestKey = `${refreshKey}:${manualRefreshKey}`;

    useEffect(() => {
        const requestId = ++requestIdRef.current;
        let active = true;

        async function fetchDocuments() {
            try {
                const response = await documentsApi.getAll();

                if (!active || requestId !== requestIdRef.current) {
                    return;
                }

                setState({
                    documents: response.documents,
                    error: null,
                    loadedKey: requestId,
                    loading: false,
                });
            } catch (err) {
                if (!active || requestId !== requestIdRef.current) {
                    return;
                }

                setState((previous) => ({
                    ...previous,
                    error:
                        err instanceof Error
                            ? err.message
                            : "Unable to load documents.",
                    loadedKey: requestId,
                    loading: false,
                }));
            }
        }

        void fetchDocuments();

        return () => {
            active = false;
        };
    }, [requestKey]);

    const loading =
        state.loading ||
        state.loadedKey !== requestIdRef.current;

    function handleRefresh() {
        setManualRefreshKey((current) => current + 1);
    }

    async function handleDelete(document: DocumentListItem) {
        const confirmed = window.confirm(
            `Delete "${document.filename}" and all its indexed chunks?`,
        );

        if (!confirmed) return;

        setDeletingId(document.id);

        try {
            await documentsApi.delete(document.id);

            setState((previous) => ({
                ...previous,
                documents: previous.documents.filter(
                    (item) => item.id !== document.id,
                ),
                error: null,
            }));
        } catch (err) {
            setState((previous) => ({
                ...previous,
                error:
                    err instanceof Error
                        ? err.message
                        : "Unable to delete document.",
            }));
        } finally {
            setDeletingId(null);
        }
    }

    return (
        <section className="rounded-xl border border-slate-200 bg-white">
            <div className="flex items-center justify-between border-b border-slate-200 p-5">
                <div>
                    <h2 className="text-lg font-semibold text-slate-900">
                        Indexed Documents
                    </h2>

                    <p className="text-sm text-slate-500">
                        {state.documents.length} documents
                    </p>
                </div>

                <button
                    type="button"
                    onClick={handleRefresh}
                    disabled={loading}
                    aria-label="Refresh documents"
                    className="rounded-lg p-2 text-slate-600 hover:bg-slate-100 disabled:opacity-50"
                >
                    <RefreshCw
                        size={18}
                        className={loading ? "animate-spin" : ""}
                    />
                </button>
            </div>

            {loading && (
                <div
                    role="status"
                    className="flex items-center justify-center gap-2 p-10 text-slate-500"
                >
                    <Loader2
                        className="animate-spin"
                        size={20}
                    />
                    Loading documents...
                </div>
            )}

            {state.error && (
                <p
                    role="alert"
                    className="p-5 text-sm text-red-600"
                >
                    {state.error}
                </p>
            )}

            {!loading &&
                state.documents.length === 0 &&
                !state.error && (
                    <p className="p-10 text-center text-sm text-slate-500">
                        No documents indexed yet. Upload your first document.
                    </p>
                )}

            {!loading && state.documents.length > 0 && (
                <div className="divide-y divide-slate-100">
                    {state.documents.map((document) => (
                        <div
                            key={document.id}
                            className="flex items-center justify-between gap-4 p-5"
                        >
                            <div className="flex min-w-0 items-center gap-3">
                                <FileText className="shrink-0 text-indigo-600" />

                                <div className="min-w-0">
                                    <p className="truncate font-medium text-slate-900">
                                        {document.filename}
                                    </p>

                                    <p className="text-xs text-slate-500">
                                        {document.chunk_count} chunks ·{" "}
                                        {new Date(
                                            document.created_at,
                                        ).toLocaleDateString()}
                                    </p>
                                </div>
                            </div>

                            <button
                                type="button"
                                aria-label={`Delete ${document.filename}`}
                                onClick={() =>
                                    void handleDelete(document)
                                }
                                disabled={deletingId !== null}
                                className="rounded-lg p-2 text-red-600 hover:bg-red-50 disabled:opacity-50"
                            >
                                {deletingId === document.id ? (
                                    <Loader2
                                        size={18}
                                        className="animate-spin"
                                    />
                                ) : (
                                    <Trash2 size={18} />
                                )}
                            </button>
                        </div>
                    ))}
                </div>
            )}
        </section>
    );
}
