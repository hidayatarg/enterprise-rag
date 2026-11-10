""" Retrieval evaluation metrics for Enterprise RAG.

Metrics:
- Hit@K
- Recall@K
- Reciprocal Rank@K
- Mean Reciprocal Rank@K

These functions are independent of FastAPI, PostgreSQL, and Ollama. """

from collections.abc import Sequence

def _validate_k(k: int) -> None:
    if isinstance(k, bool) or not isinstance(k, int) or k < 1:
        raise ValueError("k must be a positive integer")


def hit_at_k(
    retrieved_ids: Sequence[str],
    relevant_ids: set[str],
    k: int,
) -> float:
    """
    Return 1.0 if at least one relevant result occurs
    within the first k retrieved items; otherwise 0.0.
    """
    _validate_k(k)

    return float(
        any(
            chunk_id in relevant_ids
            for chunk_id in retrieved_ids[:k]
        )
    )


def recall_at_k(
    retrieved_ids: Sequence[str],
    relevant_ids: set[str],
    k: int,
) -> float:
    """
    Calculate the fraction of relevant results recovered
    within the first k retrieved items.

    Returns 0.0 if no relevant IDs are supplied.
    Such queries should be excluded from aggregate recall
    and evaluated separately as unanswerable queries.
    """
    _validate_k(k)

    if not relevant_ids:
        return 0.0

    retrieved_relevant = (
        set(retrieved_ids[:k]) & relevant_ids
    )

    return len(retrieved_relevant) / len(relevant_ids)


def reciprocal_rank_at_k(
    retrieved_ids: Sequence[str],
    relevant_ids: set[str],
    k: int,
) -> float:
    """
    Return reciprocal rank of the first relevant result.

    Rank 1 -> 1.0
    Rank 2 -> 0.5
    Rank 3 -> 0.333...
    No match -> 0.0
    """
    _validate_k(k)

    for rank, chunk_id in enumerate(
        retrieved_ids[:k],
        start=1,
    ):
        if chunk_id in relevant_ids:
            return 1.0 / rank

    return 0.0


def mean_reciprocal_rank_at_k(
    queries: Sequence[tuple[Sequence[str], set[str]]],
    k: int,
) -> float:
    """
    Calculate mean reciprocal rank across queries.

    Each query is:
        (retrieved_chunk_ids, relevant_chunk_ids)

    This implementation expects answerable queries
    with at least one known relevant chunk.
    """
    _validate_k(k)

    if not queries:
        raise ValueError("At least one query is required")

    if any(not relevant_ids for _, relevant_ids in queries):
        raise ValueError(
            "MRR requires at least one relevant ID "
            "per query; evaluate unanswerable queries "
            "separately"
        )

    scores = [
        reciprocal_rank_at_k(
            retrieved_ids,
            relevant_ids,
            k,
        )
        for retrieved_ids, relevant_ids in queries
    ]

    return sum(scores) / len(scores)
