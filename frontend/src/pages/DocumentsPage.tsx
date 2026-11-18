import { useState } from "react";

import { DocumentUpload } from "../components/documents/DocumentUpload";
import { DocumentList } from "../components/documents/DocumentList";

export function DocumentsPage() {
    const [refreshKey, setRefreshKey] = useState(0);

    function handleUploadSuccess() {
        setRefreshKey((current) => current + 1);
    }

    return (
        <div className="mx-auto max-w-5xl space-y-8">
            <div>
                <h1 className="text-2xl font-bold text-slate-900">
                    Documents
                </h1>

                <p className="mt-2 text-slate-600">
                    Upload, index, and manage your knowledge sources.
                </p>
            </div>

            <DocumentUpload onUploadSuccess={handleUploadSuccess}/>

            <DocumentList refreshKey={refreshKey} />
        </div>
    );
}
