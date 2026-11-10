import pytest

from evaluation.retrieval_metrics import (
    hit_at_k,
    recall_at_k,
    reciprocal_rank_at_k,
    mean_reciprocal_rank_at_k,
)


def test_hit_at_k_when_relevant_result_exists():
    retrieved = ["a", "b", "c"]
    relevant = {"b"}

    assert hit_at_k(retrieved, relevant, k=2) == 1.0


def test_hit_at_k_when_relevant_result_is_outside_k():
    retrieved = ["a", "b", "c"]
    relevant = {"c"}

    assert hit_at_k(retrieved, relevant, k=2) == 0.0


def test_recall_at_k_with_multiple_relevant_chunks():
    retrieved = ["a", "b", "c", "d"]
    relevant = {"b", "d"}

    assert recall_at_k(retrieved, relevant, k=2) == 0.5
    assert recall_at_k(retrieved, relevant, k=4) == 1.0


def test_recall_at_k_ignores_duplicate_ids():
    retrieved = ["b", "b", "a"]
    relevant = {"b", "c"}

    assert recall_at_k(retrieved, relevant, k=2) == 0.5


def test_reciprocal_rank_at_k():
    retrieved = ["a", "b", "c"]
    relevant = {"b"}

    assert reciprocal_rank_at_k(
        retrieved, relevant, k=3
    ) == 0.5


def test_reciprocal_rank_at_k_no_match():
    retrieved = ["a", "b", "c"]
    relevant = {"x"}

    assert reciprocal_rank_at_k(
        retrieved, relevant, k=3
    ) == 0.0


def test_mean_reciprocal_rank_at_k():
    queries = [
        (["a", "b"], {"a"}),     # RR = 1
        (["c", "d"], {"d"}),     # RR = 0.5
        (["e", "f"], {"x"}),     # RR = 0
    ]

    score = mean_reciprocal_rank_at_k(
        queries,
        k=2,
    )

    assert score == pytest.approx(0.5)


def test_unanswerable_query_has_zero_recall():
    assert recall_at_k(
        retrieved_ids=["a", "b"],
        relevant_ids=set(),
        k=2,
    ) == 0.0


@pytest.mark.parametrize(
    "k",
    [0, -1, 1.5, True],
)
def test_invalid_k_raises_value_error(k):
    with pytest.raises(ValueError):
        hit_at_k(["a"], {"a"}, k)


def test_empty_query_collection_raises_error():
    with pytest.raises(ValueError):
        mean_reciprocal_rank_at_k([], k=2)


def test_mrr_rejects_unanswerable_queries():
    queries = [
        (["a", "b"], {"a"}),
        (["c", "d"], set()),
    ]

    with pytest.raises(ValueError):
        mean_reciprocal_rank_at_k(queries, k=2)
