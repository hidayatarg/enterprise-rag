import { FileText } from "lucide-react";
import type { CitationSource } from "../../api/types";

interface SourceCitationsProps {
    sources: CitationSource[];
}

export function SourceCitations({
    sources,
}: SourceCitationsProps) {
    if (sources.length === 0) {
        return null;
    }

    return (
        <section
            aria-label="Answer sources"
            className="mt-4 space-y-3"
        >
            <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Sources ({sources.length})
            </h4>

            <div className="space-y-2">
                {sources.map((source) => (
                    <div
                        key={`${source.reference}-${source.chunk_index}`}
                        className="rounded-lg border border-slate-200 bg-white p-3"
                    >
                        <div className="flex items-center gap-2">
                            <FileText
                                size={16}
                                className="shrink-0 text-indigo-600"
                            />

                            <span className="break-all text-xs font-semibold text-slate-800">
                                [{source.reference}] {source.filename}
                            </span>
                        </div>

                        <dl className="mt-3 grid grid-cols-3 gap-3 text-xs">
                            <div>
                                <dt className="text-slate-500">
                                    Page
                                </dt>
                                <dd className="mt-1 font-medium text-slate-800">
                                    {source.page_number ?? "N/A"}
                                </dd>
                            </div>

                            <div>
                                <dt className="text-slate-500">
                                    Chunk
                                </dt>
                                <dd className="mt-1 font-medium text-slate-800">
                                    {source.chunk_index}
                                </dd>
                            </div>

                            <div>
                                <dt className="text-slate-500">
                                    Similarity
                                </dt>
                                <dd className="mt-1 font-medium text-slate-800">
                                    {(source.similarity * 100).toFixed(2)}%
                                </dd>
                            </div>
                        </dl>
                    </div>
                ))}
            </div>
        </section>
    );
}
