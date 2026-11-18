# Enterprise RAG — Local Document Intelligence with Grounded Answers

**React · TypeScript · Vite · Tailwind CSS · FastAPI · PostgreSQL/pgvector · Ollama · Llama 3.2 · EmbeddingGemma · Python · uv**

> **Status (through Part 7.6):** Local RAG backend and evaluation tooling implemented. React + TypeScript frontend includes navigation, API health status, document upload, listing/deletion, and semantic search. AI chat UI and citation presentation are planned for Parts 7.7–7.8. Live generation evaluation scores must be measured locally.

> This project is an evolving engineering reference implementation, with ongoing development toward a production-ready, multi-tenant AI document intelligence platform.

The long-term vision is to build a flexible, enterprise-grade platform that supports multiple Large Language Models (LLMs), integrates with external AI applications through the Model Context Protocol (MCP), and enables a wide range of AI-powered workflows, including document intelligence, semantic search, retrieval-augmented generation (RAG), and conversational AI.

> The production version will focus on secure multi-tenant architecture, extensibility, model interoperability, and scalable deployment, allowing organizations to integrate their knowledge sources with different AI models and applications through a unified platform.

Upload PDF or TXT documents, extract and chunk their text, index embeddings in PostgreSQL, and ask questions answered by a locally hosted Llama model with traceable document citations. This repository deliberately implements the core RAG pipeline using Python services rather than hiding it behind Flowise or an orchestration framework.

## Contents

- [What it does](#what-it-does)
- [Architecture](#architecture)
- [Part 1 — Database and vector storage](#part-1--database-and-vector-storage)
- [Part 2 — FastAPI and persistence](#part-2--fastapi-and-persistence)
- [Part 3 — Local models and embeddings](#part-3--local-models-and-embeddings)
- [Part 4 — Document ingestion](#part-4--document-ingestion)
- [Part 5 — Retrieval, grounded answers and safeguards](#part-5--retrieval-grounded-answers-and-safeguards)
- [Part 6 — Evaluation Engineering](#part-6--evaluation-engineering)
- [Part 7 — React frontend through semantic search](#part-7--react-frontend-through-semantic-search)
- [End-to-end sequence diagrams](#end-to-end-sequence-diagrams)
- [Run locally](#run-locally)
- [API reference](#api-reference)
- [Reproducible scenarios](#reproducible-scenarios)
- [Tests and engineering trade-offs](#tests-and-engineering-trade-offs)
- [Roadmap](#roadmap)

## What it does

| Capability | Status | Notes |
|---|---|---|
| PostgreSQL + `pgvector` | Implemented | Persistent vectors (`VECTOR(768)`), cosine search, optional HNSW index |
| FastAPI + SQLAlchemy | Implemented | API routes, dependency-injected sessions, pooling |
| Local Llama generation | Implemented | Ollama serves `llama3.2` |
| Local embedding generation | Implemented | Ollama serves `embeddinggemma` |
| PDF/TXT upload and chunking | Implemented | PyMuPDF for text-based PDFs; character chunks with page metadata |
| Document-scoped semantic search | Implemented | Filters by document UUID; experimental similarity threshold |
| Grounded Q&A | Implemented | Structured response, cited source IDs and exact quote checks |
| Basic prompt-injection screening | Implemented, limited | Known-pattern detection; not a security guarantee |
| Retrieval/answer evaluation metrics | **Part 6 — tooling available** | Golden dataset, Recall@K, MRR, abstention, answer quality |
| React + TypeScript UI | Implemented through Part 7.6 | App shell, health indicator, upload, document list/delete, semantic search; AI chat UI pending |
| Authentication / tenant authorization | **Not implemented** | Do not expose this API publicly with sensitive data |

## Architecture

**High-level architecture (current implementation through Part 7.6)**

**Design boundaries:** FastAPI handles HTTP and validation; the ingestion service performs document-to-vector transformation; the retrieval service owns pgvector search; the RAG orchestrator coordinates retrieval, model generation and verification. Ollama serves two different model roles: **EmbeddingGemma** for embedding and **Llama 3.2** for answering.

```mermaid
flowchart TB
    User["User / Browser"] --> UI["React + TypeScript / Vite / Tailwind"]
    UI --> Client["Typed API client / Vite dev proxy"]
    Client --> API["FastAPI /api/v1 (main.py)"]
    API --> DOC["Document processing / ingestion service"]
    API --> RET["Retrieval service"]
    API --> RAG["RAG service / grounding & citation checks"]
    API --> MGMT["Document list / delete SQL"]
    DOC --> EMB["Ollama: EmbeddingGemma"]
    RET --> EMB
    RAG --> RET
    RAG --> LLM["Ollama: Llama 3.2"]
    DOC --> DB[("PostgreSQL + pgvector")]
    RET --> DB
    MGMT --> DB
```

**Frontend scope:** Dashboard/layout, document upload and management, and semantic search are wired to FastAPI. The RAG `/documents/ask` backend exists, but the dedicated React chat interface is a Part 7.7 task. The Vite proxy is a development convenience, not a production ingress design.

### Backend layout

| Path | Responsibility |
|---|---|
| [`backend/app/main.py`](backend/app/main.py) | FastAPI routes, including document listing and deletion |
| [`backend/app/database.py`](backend/app/database.py) | Database engine and session dependency |
| [`backend/app/models/models.py`](backend/app/models/models.py) | SQLAlchemy mappings for `Document` and `DocumentChunk` |
| [`backend/app/models/requests.py`](backend/app/models/requests.py) | Pydantic request models for chat, embeddings and document search |
| [`backend/app/models/responses.py`](backend/app/models/responses.py) | Pydantic response models for upload, listing, deletion, chat and embeddings |
| [`backend/app/schemas/rag_schemas.py`](backend/app/schemas/rag_schemas.py) | Structured answer and citation schemas |
| [`backend/app/services/`](backend/app/services/) | Ollama client, ingestion, retrieval and grounded-answer services |
| [`backend/evaluation/`](backend/evaluation/) | Retrieval and generation evaluators, datasets and reporting |

### Data model

The [SQLAlchemy models](backend/app/models/models.py) and [PostgreSQL schema](backend/sql/2.table_creation.sql) define the document and chunk tables.

```mermaid
erDiagram
    documents ||--o{ document_chunks : contains
    documents {
        uuid id PK
        varchar filename
        varchar content_type
        timestamptz created_at
    }
    document_chunks {
        uuid id PK
        uuid document_id FK
        int chunk_index
        int page_number
        text content
        vector embedding "768 dimensions"
    }
```

Each document can produce many chunks. `document_chunks.document_id` references `documents.id`; `(document_id, chunk_index)` is unique. The foreign key uses `ON DELETE CASCADE`. Original uploaded file bytes are **not stored** by the current ingestion implementation. A 768-dimensional vector is tied to the configured embedding model; changing embedding dimensions requires a coordinated schema/index update and re-embedding.

---

## Part 1 — Database and vector storage

**Objective:** understand vector representations and the `<=>` cosine-distance operator directly in PostgreSQL.

- PostgreSQL 17 + pgvector 0.8.7 via Docker Compose.
- `documents` / `document_chunks` relational schema; vector indexing with `vector_cosine_ops`.
- A small three-dimensional learning table was used for first similarity queries; the actual application uses 768 dimensions.

> PostgreSQL ranks by **cosine distance** (smaller is nearer). The API reports `similarity = 1 - distance`. Similarity is not a calibrated probability of correctness.

## Part 2 — FastAPI and persistence

**Objective:** expose HTTP endpoints backed by managed database sessions.

- FastAPI routing and Pydantic request validation.
- SQLAlchemy + Psycopg 3, connection pooling, dependency injection and explicit session cleanup.
- `/health` and `/database/status` endpoint checks; mocked tests independent of running Postgres.

## Part 3 — Local models and embeddings

**Objective:** separate language generation from vector representation.

- Ollama local service, usually at `http://localhost:11434`.
- `llama3.2` for chat; `embeddinggemma` for embeddings.
- A cosine similarity experiment compares semantically related and unrelated sentences.
- `AIService` is an abstraction so HTTP handlers don't call Ollama directly.

## Part 4 — Document ingestion

**Objective:** turn uploaded PDF/TXT bytes into searchable, source-attributed chunks.

### Ingestion sequence (existing backend flow)

```mermaid
sequenceDiagram
    autonumber
    actor Client
    participant API as FastAPI
    participant P as Document processor
    participant O as Ollama EmbeddingGemma
    participant DB as PostgreSQL / pgvector
    Client->>API: POST /api/v1/documents/upload (PDF/TXT)
    API->>API: Validate extension, size, empty input
    API->>P: Extract pages and split text
    P-->>API: Text chunks and page numbers
    API->>API: Validate chunk count
    API->>DB: Insert document within transaction
    loop Batches of up to 16 chunks
        API->>O: Embed batch
        O-->>API: 768-dimensional vectors
    end
    API->>DB: Persist chunks and commit
    DB-->>API: Commit confirmed
    API-->>Client: 201 Created + document_id
```

**Current local limits:** file size 5 MiB, up to 100 chunks, chunk size 1,000 characters with 200-character overlap, 16 chunks per embedding batch. PDF page boundaries are retained. Scanned/image-only PDFs need OCR (not implemented). Ingestion is synchronous; for bigger files use a queue and background worker, and avoid long-running write transactions while waiting for embedding inference.

## Part 5 — Retrieval, grounded answers and safeguards

**Objective:** answer only with available document evidence, while making unsupported outputs rejectable.

### Grounded answer sequence (existing backend flow)

```mermaid
sequenceDiagram
    autonumber
    actor Client
    participant API as FastAPI
    participant R as RAG Orchestrator
    participant O as Ollama
    participant DB as PostgreSQL pgvector
    Client->>API: POST /api/v1/documents/ask
    API->>R: Send document ID and question
    R->>O: Embed question with EmbeddingGemma
    O-->>R: Return 768-dimensional vector
    R->>DB: Search document chunks with similarity threshold
    DB-->>R: Return matching document chunks
    R->>R: Screen for prompt injection
    alt No accepted chunks
        R-->>API: Return abstention
    else Relevant context available
        R->>R: Build numbered document context
        R->>O: Send question and evidence to Llama
        O-->>R: Return structured answer and citations
        R->>R: Check evidence sufficiency
        R->>R: Validate citation references
        R->>R: Validate exact quotations
        alt Answer passes validation
            R-->>API: Return answer with sources
        else Answer fails validation
            R-->>API: Return abstention
        end
    end
    API-->>Client: Return JSON response
```

### Safeguards and their limits

![RAG safeguards](docs/images/security-controls.svg)

| Control | What it does | What it does **not** do |
|---|---|---|
| Document UUID filter | Restricts retrieval to the requested document | Authenticate the user or authorize access to that document |
| Experimental `min_similarity=0.45` | Rejects chunks below a provisional score | Guarantee relevance; threshold must be calibrated |
| Suspicious-instruction patterns | Screens some obvious injected instructions | Detect sophisticated, encoded or indirect attacks |
| Numbered untrusted context | Makes source boundaries explicit to Llama | Enforce a security boundary by itself |
| Pydantic structured output | Validates fields and evidence/citation consistency | Ensure generated conclusions are true |
| Citation reference + exact quote checks | Rejects nonexistent references and invented quotes | Prove that the **claim** follows from the quoted text |

Example of why **citation integrity ≠ answer faithfulness**: the source says **“Refunds above $500 require manager approval”**. A generated answer saying **“Every refund requires manager approval”** could quote that sentence exactly but still be logically wrong. Part 6 evaluation tooling is intended to measure this failure mode.

**Safety:** the app does not currently implement sign-in, document ownership, tenant scoping, authorization, rate limiting, or secure upload scanning. Don't deploy it as a public multi-tenant service or upload confidential documents. Debug logging of document text should be disabled (`DEBUG_RAG = False`).

---

## Part 6 — Evaluation Engineering

**Implemented evaluation tooling; live generation scores are produced only when you run the evaluator locally.**

The evaluation suite covers a synthetic golden dataset, Hit@K/Recall@K/MRR retrieval metrics, real PostgreSQL retrieval checks, Llama 3.2 answerability decisions, an optional Llama-based semantic correctness and faithfulness judge, and timestamped JSON reports with baseline regression comparisons.

```mermaid
flowchart TD
    A["Golden evaluation questions"] --> B["Vector retrieval evaluation"]
    A --> C["Real RAG and Llama evaluation"]
    B --> D["Hit, Recall and MRR"]
    C --> E["Answer and abstention metrics"]
    C --> F["Optional correctness and faithfulness judge"]
    D --> I["Retrieval summary in terminal"]
    E --> G["Timestamped generation JSON report"]
    F --> G
    G --> H["Optional baseline comparison"]
```

From `backend/`:

```bash
uv run pytest tests/evaluation/ -v
uv run python -m evaluation.run_retrieval_eval --document-id YOUR_DOCUMENT_UUID --k 5
uv run python -m evaluation.run_generation_eval --document-id YOUR_DOCUMENT_UUID --skip-judge
uv run python -m evaluation.run_generation_eval --document-id YOUR_DOCUMENT_UUID
```

The last command also asks Llama to evaluate its own accepted answers. **Judge verdicts are provisional**, not independent ground truth; cite integrity alone does not prove semantic faithfulness. The current single-chunk synthetic policy cannot substantiate production-level accuracy.

See the detailed [Part 6 Evaluation Guide](docs/part-6-evaluation.md) for sequence diagrams, metric definitions, commands, report comparisons, and limitations.

## Part 7 — React frontend through semantic search

**Objective:** provide a usable browser interface over the existing FastAPI RAG backend without replacing the Python services or vector retrieval logic.

| Step | Capability | Status |
|---|---|---|
| 7.1 | React + TypeScript + Vite, Tailwind CSS v4, Vitest | Implemented |
| 7.2 | App layout, sidebar, navigation, dashboard and placeholder pages | Implemented |
| 7.3 | Typed API client, Vite `/api` proxy, backend health status | Implemented |
| 7.4 | PDF/TXT upload with validation, progress state and indexing result | Implemented |
| 7.5 | List indexed documents, show chunk counts, delete, refresh after upload | Implemented |
| 7.6 | Select document, ask search question, choose `top_k`, inspect ranked chunks | Implemented (verify locally) |
| 7.7 | Grounded AI chat interface using `/documents/ask` | Next |
| 7.8 | Source citation display and verification UX | Planned |
| 7.9–7.10 | Expanded frontend tests, integration and documentation | Planned |

### Frontend layout

```text
frontend/
├── src/
│   ├── api/
│   │   ├── client.ts
│   │   ├── types.ts
│   │   ├── healthApi.ts
│   │   ├── documentsApi.ts
│   │   └── searchApi.ts
│   ├── components/
│   │   ├── layout/          # AppLayout, Header, Sidebar
│   │   ├── documents/       # DocumentUpload, DocumentList
│   │   └── BackendStatus.tsx
│   ├── pages/               # Dashboard, Documents, Search, Chat, Settings
│   └── App.tsx
├── .env.development
└── vite.config.ts
```

The API client uses `VITE_API_BASE_URL=/api/v1`; Vite proxies `/api` to `http://127.0.0.1:8000` during development. The browser does not call Ollama or PostgreSQL directly.

### Document management API

- `GET /api/v1/documents` returns `{documents: [{id, filename, content_type, created_at, chunk_count}], total}`.
- `DELETE /api/v1/documents/{document_id}` removes the document and its indexed chunks in one transaction; returns `{document_id, deleted}` or HTTP 404.
- Both endpoints execute their SQL in [`backend/app/main.py`](backend/app/main.py) and use the DTOs in [`backend/app/models/responses.py`](backend/app/models/responses.py).
- Upload success calls `onUploadSuccess` to refresh the document list. The upload success message can be dismissed without deleting the indexed document.

### Semantic search

`POST /api/v1/documents/search` accepts:

```json
{
  "document_id": "YOUR_DOCUMENT_UUID",
  "question": "How long does it take to process approved refunds?",
  "top_k": 5
}
```

The response contains `question` and `results`. Each result includes `content`, `filename`, `page_number`, `chunk_index`, `distance`, and `similarity`. The UI displays raw similarity values; they are **not calibrated probabilities of correctness**. TXT documents may have no page number. Search retrieves evidence; it does **not** generate a final answer.

## End-to-end sequence diagrams

### A. Upload and index a document (React to pgvector)

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant UI as React documents workspace
    participant API as FastAPI
    participant Embed as Ollama EmbeddingGemma
    participant DB as PostgreSQL pgvector
    User->>UI: Select PDF/TXT and upload
    UI->>API: POST /api/v1/documents/upload (multipart)
    API->>API: Validate file and extract chunks with page metadata
    API->>DB: Insert document within transaction
    API->>Embed: Embed chunks (batches)
    Embed-->>API: 768-dimensional vectors
    API->>DB: Persist chunks and commit
    DB-->>API: Commit confirmed
    API-->>UI: 201 indexed, document_id, chunks_created
    UI-->>User: Show dismissible success message
    UI->>UI: Upload success triggers a list refresh
    UI->>API: GET /api/v1/documents
    API->>DB: Query documents and chunk counts
    DB-->>API: Document rows
    API-->>UI: Document list
    UI-->>User: Show new indexed document
```

### B. Semantic search (Part 7.6)

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant UI as React SearchPage
    participant API as FastAPI
    participant Embed as Ollama EmbeddingGemma
    participant DB as PostgreSQL pgvector
    UI->>API: GET /api/v1/documents
    API-->>UI: Document IDs and filenames
    User->>UI: Select document, enter question, set top_k
    UI->>API: POST /api/v1/documents/search
    API->>Embed: Generate question embedding
    Embed-->>API: Query vector (768 dimensions)
    API->>DB: Retrieve ranked chunks for the document UUID
    DB-->>API: Chunk content, source metadata and distances
    API-->>UI: question and results[]
    UI-->>User: Show ranked evidence and metadata
```

### C. Grounded answer backend (UI integration planned for Part 7.7)

```mermaid
sequenceDiagram
    autonumber
    actor Client as API consumer (future React ChatPage)
    participant API as FastAPI
    participant RAG as RAG service
    participant O as Ollama
    participant DB as PostgreSQL pgvector
    Client->>API: POST /api/v1/documents/ask
    API->>RAG: Question, document_id, top_k
    RAG->>O: O question
    O-->>RAG: Query vector
    RAG->>DB: Retrieve document-scoped chunks
    DB-->>RAG: Ranked evidence
    RAG->>RAG: Relevance and prompt-injection checks
    alt No accepted chunks
        RAG-->>API: Abstain
    else Evidence available
        RAG->>O: Generate structured answer with Llama 3.2
        O-->>RAG: Answer and citations
        RAG->>RAG: Validate references and exact quotes
        RAG-->>API: Validated answer or abstention
    end
    API-->>Client: answer, context_found, sources
```

### D. Delete a document and its vectors

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant UI as React DocumentList
    participant API as FastAPI
    participant DB as PostgreSQL
    User->>UI: Click Delete
    UI->>User: Confirm deletion
    alt Confirmed
        UI->>API: DELETE /api/v1/documents/{document_id}
        API->>DB: Delete matching document_chunks
        API->>DB: Delete parent document
        alt Document found
            API->>DB: COMMIT transaction
            API-->>UI: 200 deleted=true
            UI-->>User: Remove row from list
        else Document not found
            API->>DB: ROLLBACK
            API-->>UI: 404 Not Found
            UI-->>User: Show error
        end
    else Cancelled
        UI-->>User: Keep document
    end
```

---

## Run locally

**Prerequisites:** Docker + Docker Compose, Python 3.12+, [`uv`](https://docs.astral.sh/uv/), [Ollama](https://ollama.com/download), Node.js compatible with the installed Vite version, npm, and enough local memory to run the selected models.

### 1. Clone and start PostgreSQL

```bash
git clone https://github.com/hidayatarg/enterprise-rag.git
cd enterprise-rag
docker compose up -d
```

Docker Compose maps the container's `5432` to host **`127.0.0.1:5433`**. The repository's current Compose configuration uses local development credentials; **replace them for any nonlocal deployment**.

### 2. Download and run local models

```bash
ollama pull llama3.2
ollama pull embeddinggemma
ollama list
```

Ensure the Ollama application/server is running. Confirm connectivity with `curl http://localhost:11434/api/tags`.

### 3. Configure and install the Python backend

```bash
cd backend
uv sync
```

Create `backend/.env` (do not commit it):

```dotenv
DATABASE_URL=postgresql+psycopg://raguser:ragpassword@localhost:5433/ragdb
```

### 4. Initialize schema and run API

Enable the extension in `ragdb` through pgAdmin or `psql` if needed:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

To create the tables from the ORM models, run the command below. The repository also provides a [SQL setup script](backend/sql/2.table_creation.sql) with an HNSW index.

```bash
uv run python -m app.init_db
```

Start the API:

```bash
uv run python -m uvicorn app.main:app --reload --port 8000
```

Go to **http://localhost:8000/docs** for interactive Swagger docs. This is a **local development** setup. `create_all()` is a learning convenience, not a schema migration system; use Alembic for later schema changes.

### 5. Index sample policy and ask a question

From any terminal, create a synthetic text file:

```bash
cat > sample-policy.txt <<'POLICY'
Payment Refund Policy
Customers may request refunds within 30 days of the original payment date.
Refund requests require a valid transaction ID.
Refunds above $500 require manager approval.
Approved refunds are processed within 5 business days.
Duplicate refund requests must be reviewed before another refund is initiated.
POLICY
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F 'file=@sample-policy.txt'
```

Copy `document_id` from the upload result and replace `YOUR_DOCUMENT_UUID` below:

```bash
curl -X POST http://localhost:8000/api/v1/documents/ask \
  -H 'Content-Type: application/json' \
  -d '{
    "document_id":"YOUR_DOCUMENT_UUID",
    "question":"How long does it take to process approved refunds?",
    "top_k":5
  }'
```

The correct policy answer is **5 business days** with an evidence reference to `sample-policy.txt`, page 1. The model's response wording and retrieval similarity vary.

### 6. Start the React frontend

Keep the backend running on port 8000. In another terminal, from the repository root:

```bash
cd frontend
npm install
npm run dev
```

In `frontend/.env.development`:

```dotenv
VITE_API_BASE_URL=/api/v1
```

The Vite development server typically prints a local URL such as `http://localhost:5173`; use the actual URL printed by your terminal. The Vite proxy forwards `/api` requests to FastAPI on port 8000. Open **Documents** to upload/manage files, then **Semantic Search** to query indexed chunks.

### 7. Run quality checks

```bash
# Backend (from backend/)
uv run pytest -q
# Frontend (from frontend/)
npx vitest run
npm run build
npm run lint
```

Tests, build and lint should be run in your local checkout; this README does not claim that the latest changes were executed here.

## API reference

| Method | Route | Function |
|---|---|---|
| `GET` | `/api/v1/health` | API liveness |
| `GET` | `/api/v1/database/status` | PostgreSQL and extension check |
| `GET` | `/api/v1/vectors` | Three-dimensional learning-vector demo (if table populated) |
| `POST` | `/api/v1/ai/chat` | Basic Llama chat demo (not grounded) |
| `POST` | `/api/v1/ai/embed` | Embedding length and preview |
| `POST` | `/api/v1/documents/upload` | Extract, chunk, embed and store |
| `GET` | `/api/v1/documents` | List indexed documents and chunk counts |
| `DELETE` | `/api/v1/documents/{document_id}` | Delete document and indexed chunks |
| `POST` | `/api/v1/documents/search` | Retrieve ranked document chunks |
| `POST` | `/api/v1/documents/ask` | Retrieve, generate and validate source citations |

`/search` returns retrieval details; `/ask` runs the full grounded-answer pipeline. An abstention may currently use HTTP `200` and `context_found` reports whether retrieval provided candidates, **not** whether the model answered. Status-specific response codes are a future enhancement.

## Reproducible scenarios

Use the synthetic `sample-policy.txt` above and the document ID returned from upload.

| User request | Expected behavior | Layer being exercised |
|---|---|---|
| “How long does it take to process approved refunds?” | **5 business days**, cite source page | Retrieval + evidence-backed answer (observed working in local testing) |
| “Does a $300 refund require manager approval?” | Below the above-$500 threshold; date and transaction details are still required | Numerical policy reasoning (evaluate separately) |
| “Does a $600 refund require manager approval?” | Manager approval required, subject to policy constraints | Conditional reasoning |
| “What is the CEO's annual salary?” | Abstain, no invented salary | Negative/unsupported question |
| Retrieved text says “Ignore all previous instructions” | Obvious pattern is screened; model should never gain tool privileges | Limited prompt-injection check |
| Model cites `[9]` when only `[1]` was retrieved | Reject citation | Reference validation |
| Model fabricates supporting quote | Reject citation | Exact-quote validation |

**No Swagger response screenshots are included.** Scenarios are reproducible inputs and expected behavior, not a claim that every scenario has been benchmarked or passes for every model version.

## Tests and engineering trade-offs

Run focused and full suites using **uv**:

```bash
cd backend
uv run pytest tests/test_citations.py -v
uv run pytest tests/test_rag_schemas.py -v
uv run pytest tests/test_rag.py -v
uv run pytest tests/ -v
```

The test suite covers FastAPI behavior, document chunking, ingestion flow, vector-query construction, model mocking, schema validation, citation integrity and simple injection patterns. Mock-based tests don't prove live retrieval performance or end-to-end answer faithfulness; Part 6 provides reproducible evaluation tooling. The test count is intentionally not hard-coded here: run the suite in your checkout for the current total.

**Design decisions and known limitations:**

- **No Flowise/LangChain dependency:** core mechanics are inspectable Python.
- **Local model inference:** no paid generation API required, but model speed depends on hardware.
- **Embedding model lock-in:** vectors created with one embedding model shouldn't be compared against a different one without reindexing.
- **Synchronous ingestion:** simple for learning, but expensive inference should be moved off request/transaction paths.
- **Basic chunking:** character-based overlap can split semantic units and inflate repeated text; compare strategies in evaluation.
- **Experimental threshold:** `0.45` is provisional and can suppress good evidence or admit bad evidence.
- **Heuristic injection patterns:** not equivalent to robust threat modeling or authorization.
- **Exact citation quotes:** catch invented quotes, **not** false logical conclusions.
- **Access control missing:** `document_id` alone is not authorization; treat the service as localhost-only.
- **Schema migrations missing:** add Alembic before changing persistence models broadly.

## Roadmap

| Part | Subject | Status |
|---|---|---|
| **Part 1** | PostgreSQL + pgvector | Implemented |
| **Part 2** | FastAPI, SQLAlchemy, dependency injection | Implemented |
| **Part 3** | Ollama, Llama and embeddings | Implemented |
| **Part 4** | Ingestion, PDF/TXT, chunking and persistence | Implemented |
| **Part 5** | Vector retrieval, grounded answer, citations and hardening | Implemented; limitations documented |
| **Part 6** | Golden datasets, Recall@K, MRR, faithfulness and regression evaluation | Evaluation tooling implemented; live generation run pending |
| **Part 7** | React + TypeScript document and chat UI | Implemented through Part 7.6. Chat and citations are planned for Parts 7.7–7.8. |
| **Part 8** | Authorization, background processing, observability and deployment | Planned |

### Contribution and history

Review the real [commit history](https://github.com/hidayatarg/enterprise-rag/commits/main) for implementation evolution. Keep commits small and descriptive (e.g., `feat(rag): validate cited source quotes` or `test(rag): cover invalid evidence paths`); these are **recommendations**, not quotations of existing commits.

The architecture diagrams under [`docs/images/`](docs/images/) are versioned alongside this README and can be updated as new Parts are delivered. Mermaid sequences above also render directly in GitHub and remain easy to edit.

---

**Maintainer:** [hidayatarg](https://github.com/hidayatarg) · **Repository:** [enterprise-rag](https://github.com/hidayatarg/enterprise-rag)
