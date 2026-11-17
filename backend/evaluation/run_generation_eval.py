"""Parts 6.4-6.6: live Llama 3.2 RAG evaluation and JSON reporting.

Usage from backend/:
 uv run python -m evaluation.run_generation_eval --document-id UUID
 uv run python -m evaluation.run_generation_eval --document-id UUID --baseline evaluation/reports/OLD.json
 uv run python -m evaluation.run_generation_eval --document-id UUID --skip-judge

This runs the ACTUAL answer_document_question() service against local PostgreSQL/Ollama.
"""
import argparse
import hashlib
from datetime import datetime, timezone
import json
from pathlib import Path
from uuid import UUID

from evaluation.answer_judge import judge_answer
from evaluation.reporting import aggregate, compare_baseline, write_report

BACKEND_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = BACKEND_DIR / "evaluation/datasets/refund_policy.json"
DEFAULT_REPORT_DIR = BACKEND_DIR / "evaluation/reports"


def classify_result(result, abstain_message: str) -> str:
    """Use final RAG decision, NOT context_found (retrieval may have succeeded)."""
    if result.answer.strip() == abstain_message.strip():
        return "abstained"
    if not result.sources:
        # Fail loudly rather than count an unverified answer as successful.
        raise ValueError("Non-abstention response has no validated sources")
    return "answered"


def evidence_for_sources(stored_chunks: dict[int, str], sources: list[dict]) -> list[str]:
    """Read only the document's chunks cited by accepted RAG response."""
    evidence = []
    seen = set()
    for item in sources:
        index = item["chunk_index"]
        if index not in stored_chunks:
            raise ValueError(f"Cited chunk missing from document: {index}")
        if index not in seen:
            evidence.append(stored_chunks[index])
            seen.add(index)
    return evidence


def evaluate_case(case: dict, *, document_id: UUID, db, ai,
                  stored_chunks: dict[int, str], top_k: int,
                  abstain_message: str, enable_judge: bool,
                  rag_function=None) -> dict:
    """Execute one live end-to-end RAG request. Exceptions bubble up to runner."""
    if rag_function is None:
        from app.rag_service import answer_document_question
        rag_function = answer_document_question
    result = rag_function(db=db, ai=ai, document_id=document_id,
                          question=case["question"], top_k=top_k)
    status = classify_result(result, abstain_message)
    row = {
        "id": case["id"], "category": case["category"], "question": case["question"],
        "answerable": case["answerable"], "status": status,
        "answer": result.answer, "context_found": result.context_found,
        "sources_count": len(result.sources), "sources": result.sources,
        "judge": None,
    }
    if enable_judge and status == "answered" and case["answerable"]:
        # The same Llama model grades its own answer: useful diagnostic, NOT objective truth.
        evidence = evidence_for_sources(stored_chunks, result.sources)
        verdict = judge_answer(
            ai, question=case["question"],
            reference_answer=case["expected_answer"],
            candidate_answer=result.answer, evidence=evidence,
        )
        row["judge"] = verdict.model_dump()
    return row


def run(*, document_id: UUID, dataset_path: Path, output_dir: Path,
        top_k: int, enable_judge: bool, baseline_path: Path | None = None) -> Path:
    if not 1 <= top_k <= 20:
        raise ValueError("top_k must be between 1 and 20")
    # app.database reads DATABASE_URL on import: read .env first.
    from dotenv import load_dotenv
    load_dotenv(BACKEND_DIR / ".env")
    from sqlalchemy import select
    from app.ai_service import AIService
    from app.database import SessionLocal
    from app.models import Document, DocumentChunk
    from app.rag_service import ABSTAIN_MESSAGE, MIN_SIMILARITY

    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    if not dataset["cases"]:
        raise ValueError("Dataset contains no questions")
    ids = [c["id"] for c in dataset["cases"]]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate dataset case IDs")

    dataset_digest = hashlib.sha256(dataset_path.read_bytes()).hexdigest()
    ai = AIService()
    rows = []
    with SessionLocal() as db:
        document = db.get(Document, document_id)
        if document is None:
            raise ValueError("Document UUID not found")
        if document.filename != dataset["document_filename"]:
            raise ValueError(
                f"Wrong document: expected {dataset['document_filename']}, got {document.filename}"
            )
        stored_chunks = dict(db.execute(
            select(DocumentChunk.chunk_index, DocumentChunk.content)
            .where(DocumentChunk.document_id == document_id)
        ).all())
        if not stored_chunks:
            raise ValueError("Document contains no chunks")
        chunk_digest = hashlib.sha256(
            json.dumps(sorted(stored_chunks.items()), ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        # Validate golden labels against indexed document before scoring.
        from evaluation.run_retrieval_eval import find_relevant_chunk_ids
        for case in dataset["cases"]:
            if case["answerable"]:
                find_relevant_chunk_ids(
                    list(stored_chunks.items()), case["expected_evidence"]
                )
        for case in dataset["cases"]:
            try:
                row = evaluate_case(
                    case, document_id=document_id, db=db, ai=ai,
                    stored_chunks=stored_chunks, top_k=top_k,
                    abstain_message=ABSTAIN_MESSAGE,
                    enable_judge=enable_judge,
                )
                print(f"{case['id']}: {row['status']}  sources={row['sources_count']}"
                      + (f" judge={row['judge']}" if row["judge"] else ""))
            except Exception as exc:
                # IMPORTANT: record failures separately; never count as model abstentions.
                db.rollback()
                row = {
                    "id": case["id"], "category": case["category"],
                    "question": case["question"], "answerable": case["answerable"],
                    "status": "error", "error_type": type(exc).__name__,
                    "error": str(exc)[:300], "judge": None,
                }
                print(f"{case['id']}: ERROR ({type(exc).__name__})")
            rows.append(row)

    report = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": dataset["dataset_name"],
        "dataset_sha256": dataset_digest,
        "stored_chunks_sha256": chunk_digest,
        "rag_min_similarity": MIN_SIMILARITY,
        "document_id": str(document_id),
        "document_filename": dataset["document_filename"],
        "top_k": top_k,
        "llm_model": ai.chat_model,
        "embedding_model": ai.embedding_model,
        "judge_enabled": enable_judge,
        "dataset_case_count": len(ids),
        "judge_note": "Same local Llama is judging its own answers; human review required." if enable_judge else "LLM judge disabled",
        "case_ids": ids,
        "cases": rows,
        "summary": aggregate(rows),
    }
    if baseline_path is not None:
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        report["baseline_comparison"] = compare_baseline(report, baseline)
    target = write_report(report, output_dir)
    print("\nSummary:")
    print(json.dumps(report["summary"], indent=2))
    print(f"\nReport: {target}")
    return target


def main():
    parser = argparse.ArgumentParser(description="Run real RAG generation evaluation")
    parser.add_argument("--document-id", type=UUID, required=True)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--skip-judge", action="store_true")
    parser.add_argument("--baseline", type=Path)
    args = parser.parse_args()
    run(document_id=args.document_id, dataset_path=args.dataset,
        output_dir=args.output_dir, top_k=args.top_k,
        enable_judge=not args.skip_judge, baseline_path=args.baseline)


if __name__ == "__main__":
    main()
