# Enterprise RAG — Local Document Intelligence with Grounded Answers

**FastAPI · PostgreSQL/pgvector · Ollama · Llama 3.2 · EmbeddingGemma · Python · uv**

> **Status:** Working local RAG backend through **Part 5 (retrieval, grounded generation, citation validation, initial hardening)**. **Part 6 (quantitative evaluation) is planned next.** React + TypeScript is the planned frontend, **not an implemented UI in this release**.
>
> This is an engineering reference implementation, **not a production-ready multi-tenant document platform**.

Upload PDF or TXT documents, extract and chunk their text, index embeddings in PostgreSQL, and ask questions answered by a locally hosted Llama model with traceable document citations. This repository deliberately implements the core RAG pipeline using Python services rather than hiding it behind Flowise or an orchestration framework.

## Contents

- [What it does](#what-it-does)
- [Architecture](#architecture)
- [Part 1 — Database and vector storage](#part-1--database-and-vector-storage)
- [Part 2 — FastAPI and persistence](#part-2--fastapi-and-persistence)
- [Part 3 — Local models and embeddings](#part-3--local-models-and-embeddings)
- [Part 4 — Document ingestion](#part-4--document-ingestion)
- [Part 5 — Retrieval, grounded answers and safeguards](#part-5--retrieval-grounded-answers-and-safeguards)
- [Part 6 — Evaluation (next)](#part-6--evaluation-next)
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
| Retrieval/answer evaluation metrics | **Part 6 — next** | Golden dataset, Recall@K, MRR, abstention, answer quality |
| React + TypeScript UI | Planned | Backend currently exercised through Swagger/curl |
| Authentication / tenant authorization | **Not implemented** | Do not expose this API publicly with sensitive data |

## Architecture

![High-level architecture of Enterprise RAG](docs/images/architecture.svg)

**Design boundaries:** FastAPI handles HTTP and validation; the ingestion service performs document-to-vector transformation; the retrieval service owns pgvector search; the RAG orchestrator coordinates retrieval, model generation and verification. Ollama serves two different model roles: **EmbeddingGemma** for embedding and **Llama 3.2** for answering.

```mermaid
flowchart LR
    U[API consumer / Swagger] --> API[FastAPI]
    API --> ING[Document processing & ingestion]
    API --> RAG[RAG orchestration]
    ING --> EMB[Ollama: EmbeddingGemma]
    ING --> DB[(PostgreSQL + pgvector)]
    RAG --> EMB
    RAG --> DB
    RAG --> LLM[Ollama: Llama 3.2]
    RAG --> VAL[Relevance, injection & citation checks]
    VAL --> API
```

### Data model

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
        vector_768 embedding
    }
```

Each document can produce many chunks. `document_chunks.document_id` references `documents.id`; `(document_id, chunk_index)` is unique. Original uploaded file bytes are **not stored** by the current ingestion implementation. A 768-dimensional vector is tied to the configured embedding model; changing embedding dimensions requires a coordinated schema/index update and re-embedding.

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

![Document ingestion sequence](docs/images/sequence-ingestion.svg)

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
    P-->>API: Indexed chunks + page numbers
    loop Batches of up to 16 chunks
        API->>O: Embed batch
        O-->>API: 768-D vectors
    end
    API->>DB: Insert document and chunks
    DB-->>API: Commit
    API-->>Client: 201 Created + document_id
```

**Current local limits:** file size 5 MiB, up to 100 chunks, chunk size 1,000 characters with 200-character overlap, 16 chunks per embedding batch. PDF page boundaries are retained. Scanned/image-only PDFs need OCR (not implemented). Ingestion is synchronous; for bigger files use a queue and background worker, and avoid long-running write transactions while waiting for embedding inference.

## Part 5 — Retrieval, grounded answers and safeguards

**Objective:** answer only with available document evidence, while making unsupported outputs rejectable.

![Question answering sequence](docs/images/sequence-rag.svg)

```mermaid
sequenceDiagram
    autonumber
    actor Client
    participant API as FastAPI
    participant R as RAG orchestrator
    participant E as Ollama EmbeddingGemma
    participant DB as PostgreSQL / pgvector
    participant L as Ollama Llama 3.2
    Client->>API: POST /api/v1/documents/ask
    API->>R: document_id, question, top_k
    R->>E: Embed question
    E-->>R: Query vector (768-D)
    R->>DB: Filter document, rank by cosine distance
    DB-->>R: Ranked chunks + source metadata
    R->>R: Check minimum similarity; screen obvious injections
    alt No accepted chunks
        R-->>API: Abstain
    else Context available
        R->>L: Question + numbered untrusted evidence
        L-->>R: Structured answer, sufficiency, citations, exact quotes
        R->>R: Validate source IDs and quoted substrings
        alt Validation succeeds
            R-->>API: Grounded answer + cited source metadata
        else Insufficient evidence / invalid citation
            R-->>API: Abstain
        end
    end
    API-->>Client: answer, context_found, sources
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

Example of why **citation integrity ≠ answer faithfulness**: the source says *“Refunds above $500 require manager approval”*. A generated answer saying *“Every refund requires manager approval”* could quote that sentence exactly but still be logically wrong. Part 6 will evaluate this failure mode.

**Safety:** the app does not currently implement sign-in, document ownership, tenant scoping, authorization, rate limiting, or secure upload scanning. Don't deploy it as a public multi-tenant service or upload confidential documents. Debug logging of document text should be disabled (`DEBUG_RAG = False`).

---

## Part 6 — Evaluation (next)

**Planned, not yet claimed as implemented:** move from ad-hoc examples to reproducible quality measurements.

```mermaid
flowchart LR
    G[Golden question set] --> RET[Retrieval runner]
    G --> GEN[Answer runner]
    RET --> M1[Recall@K / MRR]
    GEN --> M2[Answer correctness / abstention]
    GEN --> M3[Citation integrity / claim faithfulness]
    M1 --> REPORT[Versioned evaluation report]
    M2 --> REPORT
    M3 --> REPORT
```

Planned deliverables: labeled questions (positive, negative, numeric policy reasoning, adversarial), Recall@K and mean reciprocal rank, citation coverage and invalid-citation rate, abstention accuracy, and grounded-claim review. Compare a baseline against threshold filtering and other retrieval configurations. Publish **measured** results and failure examples; don't infer accuracy from a handful of passing prompts.

## Run locally

**Prerequisites:** Docker + Docker Compose, Python 3.12+, [`uv`](https://docs.astral.sh/uv/), [Ollama](https://ollama.com/download), and enough local memory to run the selected models.

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

If the tables have **not** already been created manually using the schema SQL, run:

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

## API reference

| Method | Route | Function |
|---|---|---|
| `GET` | `/api/v1/health` | API liveness |
| `GET` | `/api/v1/database/status` | PostgreSQL and extension check |
| `GET` | `/api/v1/vectors` | Three-dimensional learning-vector demo (if table populated) |
| `POST` | `/api/v1/ai/chat` | Basic Llama chat demo (not grounded) |
| `POST` | `/api/v1/ai/embed` | Embedding length and preview |
| `POST` | `/api/v1/documents/upload` | Extract, chunk, embed and store |
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

The test suite covers FastAPI behavior, document chunking, ingestion flow, vector-query construction, model mocking, schema validation, citation integrity and simple injection patterns. Mock-based tests don't prove live retrieval performance or end-to-end answer faithfulness; Part 6 will add reproducible evals. The test count is intentionally not hard-coded here: run the suite in your checkout for the current total.

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
| **Part 6** | Golden datasets, Recall@K, MRR, faithfulness and regression evaluation | **Next** |
| **Part 7** | React + TypeScript document and chat UI | Planned |
| **Part 8** | Authorization, background processing, observability and deployment | Planned |

### Contribution and history

Review the real [commit history](https://github.com/hidayatarg/enterprise-rag/commits/main) for implementation evolution. Keep commits small and descriptive (e.g., `feat(rag): validate cited source quotes` or `test(rag): cover invalid evidence paths`); these are **recommendations**, not quotations of existing commits.

The architecture diagrams under [`docs/images/`](docs/images/) are versioned alongside this README and can be updated as new Parts are delivered. Mermaid sequences above also render directly in GitHub and remain easy to edit.

---

**Maintainer:** [hidayatarg](https://github.com/hidayatarg) · **Repository:** [enterprise-rag](https://github.com/hidayatarg/enterprise-rag)
