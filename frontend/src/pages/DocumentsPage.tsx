import { DocumentUpload } from "../components/documents/DocumentUpload";

export function DocumentsPage() {
    return (
        <div className="mx-auto max-w-4xl">
            <div className="mb-8">
                <h1 className="text-2xl font-bold text-slate-900">
                    Documents
                </h1>

                <p className="mt-2 text-slate-600">
                    Upload PDF or TXT documents to make
                    their contents searchable with AI.
                </p>
            </div>

            <DocumentUpload />
        </div>
    );
}
