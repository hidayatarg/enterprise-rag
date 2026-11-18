
import { useRef, useState } from "react";
import type { ChangeEvent, DragEvent } from "react";

import {
    UploadCloud,
    FileText,
    X,
    CheckCircle2,
    AlertCircle,
    Loader2,
} from "lucide-react";

import { documentsApi } from "../../api/documentsApi";
import type { UploadResponse } from "../../api/types";

const MAX_FILE_SIZE = 5 * 1024 * 1024;
const ALLOWED_EXTENSIONS = [".pdf", ".txt"];

type DocumentUploadProps = {
    onUploadSuccess?: () => void;
};

function validateFile(file: File): string | null {
    const name = file.name.toLowerCase();

    if (
        !ALLOWED_EXTENSIONS.some((ext) =>
            name.endsWith(ext),
        )
    ) {
        return "Only PDF and TXT files are supported.";
    }

    if (file.size === 0) {
        return "The selected file is empty.";
    }

    if (file.size > MAX_FILE_SIZE) {
        return "The maximum file size is 5 MB.";
    }

    return null;
}

function formatFileSize(bytes: number): string {
    return `${(bytes / 1024).toFixed(1)} KB`;
}

export function DocumentUpload({
    onUploadSuccess,
}: DocumentUploadProps) {
    const inputRef = useRef<HTMLInputElement>(null);

    const [file, setFile] = useState<File | null>(null);
    const [dragging, setDragging] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [result, setResult] = useState<UploadResponse | null>(null);

    function selectFile(selected: File | undefined) {
        if (!selected || uploading) return;

        const validationError = validateFile(selected);

        setError(validationError);
        setResult(null);
        setFile(validationError ? null : selected);
    }

    function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
        selectFile(event.target.files?.[0]);

        // Allow selecting the same file again.
        event.target.value = "";
    }

    function handleDrop(event: DragEvent<HTMLDivElement>) {
        event.preventDefault();
        setDragging(false);

        selectFile(event.dataTransfer.files[0]);
    }

    async function handleUpload() {
        if (!file || uploading) return;

        setUploading(true);
        setError(null);
        setResult(null);

        try {
            const response = await documentsApi.upload(file);

            // Display the successful upload response.
            setResult(response);

            // Clear the selected file.
            setFile(null);

            // Notify the parent component to refresh the document list.
            onUploadSuccess?.();
        } catch (err) {
            setError(
                err instanceof Error
                    ? err.message
                    : "Document upload failed.",
            );
        } finally {
            setUploading(false);
        }
    }

    return (
        <section className="space-y-6">
            {/* Upload area */}
            <div
                onDragOver={(event) => {
                    event.preventDefault();
                    if (!uploading) setDragging(true);
                }}
                onDragLeave={() => setDragging(false)}
                onDrop={handleDrop}
                className={[
                    "rounded-xl border-2 border-dashed p-10 text-center",
                    "transition-colors",
                    dragging
                        ? "border-indigo-500 bg-indigo-50"
                        : "border-slate-300 bg-white",
                ].join(" ")}
            >
                <UploadCloud
                    size={40}
                    className="mx-auto mb-4 text-indigo-600"
                />

                <h2 className="text-lg font-semibold text-slate-900">
                    Upload a document
                </h2>

                <p className="mt-2 text-sm text-slate-500">
                    Drag and drop a PDF or TXT file here.
                </p>

                <p className="mt-1 text-xs text-slate-400">
                    Maximum file size: 5 MB
                </p>

                <input
                    ref={inputRef}
                    type="file"
                    accept=".pdf,.txt"
                    className="hidden"
                    onChange={handleFileChange}
                    disabled={uploading}
                    aria-label="Choose a document"
                />

                <button
                    type="button"
                    disabled={uploading}
                    onClick={() => inputRef.current?.click()}
                    className="mt-5 rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
                >
                    Choose file
                </button>
            </div>

            {/* Selected file */}
            {file && (
                <div className="flex items-center justify-between rounded-xl border border-slate-200 bg-white p-4">
                    <div className="flex min-w-0 items-center gap-3">
                        <FileText className="shrink-0 text-indigo-600" />

                        <div className="min-w-0">
                            <p className="truncate font-medium text-slate-900">
                                {file.name}
                            </p>

                            <p className="text-sm text-slate-500">
                                {formatFileSize(file.size)}
                            </p>
                        </div>
                    </div>

                    <button
                        type="button"
                        aria-label="Remove selected file"
                        disabled={uploading}
                        onClick={() => setFile(null)}
                        className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 disabled:opacity-50"
                    >
                        <X size={18} />
                    </button>
                </div>
            )}

            {/* Upload button */}
            {file && (
                <button
                    type="button"
                    onClick={() => void handleUpload()}
                    disabled={uploading}
                    className="flex items-center justify-center gap-2 rounded-lg bg-indigo-600 px-5 py-3 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
                >
                    {uploading ? (
                        <>
                            <Loader2
                                size={18}
                                className="animate-spin"
                            />
                            Processing document...
                        </>
                    ) : (
                        <>
                            <UploadCloud size={18} />
                            Upload and index
                        </>
                    )}
                </button>
            )}

            {/* Error notification */}
            {error && (
                <div
                    role="alert"
                    className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-red-700"
                >
                    <AlertCircle
                        size={20}
                        className="shrink-0"
                    />
                    <p className="text-sm">{error}</p>
                </div>
            )}

            {/* Success notification */}
            {result && (
                <div
                    role="status"
                    className="relative rounded-xl border border-emerald-200 bg-emerald-50 p-5"
                >
                    {/* Close button */}
                    <button
                        type="button"
                        onClick={() => setResult(null)}
                        aria-label="Dismiss upload success"
                        title="Close"
                        className="absolute right-4 top-4 rounded-lg p-1.5 text-emerald-700 transition-colors hover:bg-emerald-100 hover:text-emerald-900 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-600"
                    >
                        <X size={20} />
                    </button>

                    <div className="flex items-center gap-2 pr-10 text-emerald-800">
                        <CheckCircle2
                            size={22}
                            className="shrink-0"
                        />

                        <h3 className="font-semibold">
                            Document indexed successfully
                        </h3>
                    </div>

                    <dl className="mt-4 space-y-2 text-sm">
                        <div>
                            <dt className="font-medium text-slate-600">
                                Filename
                            </dt>
                            <dd className="text-slate-900">
                                {result.filename}
                            </dd>
                        </div>

                        <div>
                            <dt className="font-medium text-slate-600">
                                Document ID
                            </dt>
                            <dd className="break-all font-mono text-xs text-slate-900">
                                {result.document_id}
                            </dd>
                        </div>

                        <div>
                            <dt className="font-medium text-slate-600">
                                Indexed chunks
                            </dt>
                            <dd className="text-slate-900">
                                {result.chunks_created}
                            </dd>
                        </div>

                        <div>
                            <dt className="font-medium text-slate-600">
                                Status
                            </dt>
                            <dd className="text-slate-900">
                                {result.status}
                            </dd>
                        </div>
                    </dl>
                </div>
            )}
        </section>
    );
}
