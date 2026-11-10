
""" Live retrieval evaluation.
Run from backend/:

uv run python -m evaluation.run_retrieval_eval \
    --document-id YOUR_DOCUMENT_UUID

Requires:
- PostgreSQL running
- Ollama running
- embeddinggemma installed
- Synthetic refund policy already uploaded

We read the stored chunks directly from PostgreSQL and identify which ones contain 
the dataset's human-labeled evidence. Then we run the actual embedding and vector search 
pipeline and compare the returned chunk indices.
"""

import argparse
import json
import os
from pathlib import Path
from uuid import UUID

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.ai_service import AIService
from app.retrieval_service import search_chunks

from evaluation.retrieval_metrics import (
    hit_at_k,
    recall_at_k,
    reciprocal_rank_at_k,
    mean_reciprocal_rank_at_k,
)


DATASET_PATH = (
    Path(__file__).parent
    / "datasets"
    / "refund_policy.json"
)

EMBEDDING_DIMENSIONS = 768

CONFIGURATIONS = {
    "baseline": -1.0,
    "production": 0.45,
}


def normalize(value: str) -> str:
    """Normalize case and whitespace for evidence matching."""
    return " ".join(value.casefold().split())


def find_relevant_chunk_ids(
    document_chunks: list[tuple[int, str]],
    expected_evidence: list[str],
) -> set[str]:
    """
    Find ground-truth chunk IDs by matching human-labeled
    quotations against stored document content.

    chunk_index is unique within a document.
    """

    if not expected_evidence:
        return set()

    relevant_ids = set()

    for quote in expected_evidence:
        normalized_quote = normalize(quote)

        matches = {
            str(chunk_index)
            for chunk_index, content in document_chunks
            if normalized_quote in normalize(content)
        }

        if not matches:
            raise ValueError(
                "Golden evidence was not found in the "
                f"stored document: {quote!r}"
            )

        relevant_ids.update(matches)

    return relevant_ids


def evaluate_ranking(
    retrieved_ids: list[str],
    relevant_ids: set[str],
    k: int,
) -> dict:
    """Score one answerable question."""

    if not relevant_ids:
        raise ValueError(
            "Ranking evaluation requires relevant chunks"
        )

    return {
        "hit": hit_at_k(
            retrieved_ids, relevant_ids, k
        ),
        "recall": recall_at_k(
            retrieved_ids, relevant_ids, k
        ),
        "rr": reciprocal_rank_at_k(
            retrieved_ids, relevant_ids, k
        ),
    }


def load_document_chunks(
    db: Session,
    document_id: UUID,
) -> list[tuple[int, str]]:
    """Load stored chunks independently of vector retrieval."""

    rows = db.execute(
        text(
            """
            SELECT chunk_index, content
            FROM document_chunks
            WHERE document_id = :document_id
            ORDER BY chunk_index
            """
        ),
        {"document_id": document_id},
    ).all()

    return [
        (row.chunk_index, row.content)
        for row in rows
    ]


def run_evaluation(
    document_id: UUID,
    k: int = 5,
) -> None:

    if k < 1:
        raise ValueError("k must be positive")

    # Load backend/.env.
    backend_dir = Path(__file__).resolve().parents[1]
    load_dotenv(backend_dir / ".env")

    database_url = os.environ["DATABASE_URL"]

    with DATASET_PATH.open(
        "r", encoding="utf-8"
    ) as file:
        dataset = json.load(file)

    engine = create_engine(database_url)
    ai = AIService()

    results = {
        name: []
        for name in CONFIGURATIONS
    }

    try:
        with Session(engine) as db:

            stored_chunks = load_document_chunks(
                db, document_id
            )

            if not stored_chunks:
                raise ValueError(
                    "No document chunks found. "
                    "Check your document UUID."
                )

            print(
                f"\nDataset: {dataset['dataset_name']}"
            )
            print(f"Document ID: {document_id}")
            print(f"Stored chunks: {len(stored_chunks)}")
            print(f"K: {k}\n")

            for case in dataset["cases"]:
                question = case["question"]

                print(
                    f"\n[{case['id']}] {question}"
                )

                if case["answerable"]:
                    relevant_ids = find_relevant_chunk_ids(
                        stored_chunks,
                        case["expected_evidence"],
                    )
                else:
                    relevant_ids = set()

                vectors = ai.generate_embeddings(
                    [question]
                )

                if (
                    len(vectors) != 1
                    or len(vectors[0]) != EMBEDDING_DIMENSIONS
                ):
                    raise ValueError(
                        "Invalid question embedding"
                    )

                for name, threshold in (
                    CONFIGURATIONS.items()
                ):

                    retrieved = search_chunks(
                        db=db,
                        query_vector=vectors[0],
                        document_id=document_id,
                        limit=k,
                        min_similarity=threshold,
                    )

                    retrieved_ids = [
                        str(chunk.chunk_index)
                        for chunk in retrieved
                    ]

                    if not case["answerable"]:
                        print(
                            f"  {name}: "
                            f"{len(retrieved)} candidates "
                            "(unanswerable; no Recall/MRR)"
                        )
                        continue

                    scores = evaluate_ranking(
                        retrieved_ids,
                        relevant_ids,
                        k,
                    )

                    results[name].append(
                        {
                            "case_id": case["id"],
                            "retrieved_ids": retrieved_ids,
                            "relevant_ids": relevant_ids,
                            **scores,
                        }
                    )

                    print(
                        f"  {name}: "
                        f"Hit@{k}={scores['hit']:.2f} | "
                        f"Recall@{k}={scores['recall']:.2f} | "
                        f"RR@{k}={scores['rr']:.2f}"
                    )

            print("\n=== RETRIEVAL SUMMARY ===")

            for name, rows in results.items():
                if not rows:
                    continue

                count = len(rows)

                avg_hit = (
                    sum(r["hit"] for r in rows)
                    / count
                )

                avg_recall = (
                    sum(r["recall"] for r in rows)
                    / count
                )

                query_rankings = [
                    (
                        row["retrieved_ids"],
                        row["relevant_ids"],
                    )
                    for row in rows
                ]

                mrr = mean_reciprocal_rank_at_k(
                    query_rankings, k
                )

                print(f"\n{name.upper()}")
                print(f"Answerable cases: {count}")
                print(f"Hit@{k}:    {avg_hit:.4f}")
                print(f"Recall@{k}: {avg_recall:.4f}")
                print(f"MRR@{k}:    {mrr:.4f}")

    finally:
        engine.dispose()


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate live pgvector retrieval"
    )

    parser.add_argument(
        "--document-id",
        type=UUID,
        required=True,
    )

    parser.add_argument(
        "--k",
        type=int,
        default=5,
    )

    args = parser.parse_args()

    run_evaluation(
        document_id=args.document_id,
        k=args.k,
    )


if __name__ == "__main__":
    main()
