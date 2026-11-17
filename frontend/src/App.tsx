
import { BrainCircuit, Database, FileText } from "lucide-react";

function App() {
  return (
    <main className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center gap-3 px-6 py-5">
          <div className="rounded-xl bg-indigo-600 p-2 text-white">
            <BrainCircuit size={24} />
          </div>

          <div>
            <h1 className="text-xl font-semibold text-slate-900">
              Enterprise RAG
            </h1>
            <p className="text-sm text-slate-500">
              Document Intelligence Platform
            </p>
          </div>
        </div>
      </header>

      <section className="mx-auto max-w-6xl px-6 py-12">
        <h2 className="text-3xl font-bold text-slate-900">
          Welcome to Enterprise RAG
        </h2>

        <p className="mt-3 max-w-2xl text-slate-600">
          Upload documents, search their contents,
          and ask questions using locally hosted AI.
        </p>

        <div className="mt-10 grid gap-6 md:grid-cols-3">
          <FeatureCard
            title="Document Management"
            description="Upload and organize your documents."
            icon={<FileText size={28} />}
          />

          <FeatureCard
            title="Semantic Search"
            description="Find relevant evidence using vector search."
            icon={<Database size={28} />}
          />

          <FeatureCard
            title="AI Question Answering"
            description="Generate grounded answers with citations."
            icon={<BrainCircuit size={28} />}
          />
        </div>
      </section>
    </main>
  );
}

type FeatureCardProps = {
  title: string;
  description: string;
  icon: React.ReactNode;
};

function FeatureCard({
  title,
  description,
  icon,
}: FeatureCardProps) {
  return (
    <article className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-4 text-indigo-600">{icon}</div>

      <h3 className="text-lg font-semibold text-slate-900">
        {title}
      </h3>

      <p className="mt-2 text-sm text-slate-600">
        {description}
      </p>
    </article>
  );
}

export default App;
