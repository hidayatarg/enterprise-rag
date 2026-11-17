import { Files, Search, MessageSquare } from "lucide-react";

const features = [
    {
        title: "Documents",
        description: "Upload and manage knowledge sources.",
        icon: Files,
    },
    {
        title: "Semantic Search",
        description: "Retrieve relevant document evidence.",
        icon: Search,
    },
    {
        title: "AI Chat",
        description: "Ask questions with grounded citations.",
        icon: MessageSquare,
    },
];

export function DashboardPage() {
    return (
        <div className="mx-auto max-w-6xl">
            <div className="mb-8">
                <h1 className="text-2xl font-bold text-slate-900">
                    Welcome to Enterprise RAG
                </h1>

                <p className="mt-2 text-slate-600">
                    Your AI-powered document intelligence workspace.
                </p>
            </div>

            <div className="grid gap-5 md:grid-cols-3">
                {features.map((feature) => {
                    const Icon = feature.icon;

                    return (
                        <article
                            key={feature.title}
                            className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
                        >
                            <Icon
                                size={28}
                                className="mb-4 text-indigo-600"
                            />

                            <h2 className="text-lg font-semibold text-slate-900">
                                {feature.title}
                            </h2>

                            <p className="mt-2 text-sm text-slate-600">
                                {feature.description}
                            </p>
                        </article>
                    );
                })}
            </div>
        </div>
    );
}
