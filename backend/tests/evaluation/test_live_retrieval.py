import pytest

from evaluation.run_retrieval_eval import (
    evaluate_ranking,
    find_relevant_chunk_ids,
)


SAMPLE_CHUNKS = [
    (
        0,
        "Customers may request refunds within 30 days.",
    ),
    (
        1,
        "Approved refunds are processed within 5 business days.",
    ),
    (
        2,
        "Refunds above $500 require manager approval.",
    ),
]


def test_finds_correct_ground_truth_chunk():
    relevant = find_relevant_chunk_ids(
        SAMPLE_CHUNKS,
        [
            "Approved refunds are processed "
            "within 5 business days."
        ],
    )

    assert relevant == {"1"}


def test_ground_truth_normalizes_whitespace():
    relevant = find_relevant_chunk_ids(
        SAMPLE_CHUNKS,
        ["Approved refunds  are processed\nwithin 5 business days."],
    )

    assert relevant == {"1"}


def test_rejects_missing_golden_evidence():
    with pytest.raises(
        ValueError,
        match="Golden evidence was not found",
    ):
        find_relevant_chunk_ids(
            SAMPLE_CHUNKS,
            ["All refunds are automatic."],
        )


def test_multiple_evidence_passages():
    relevant = find_relevant_chunk_ids(
        SAMPLE_CHUNKS,
        [
            "Customers may request refunds within 30 days.",
            "Refunds above $500 require manager approval.",
        ],
    )

    assert relevant == {"0", "2"}


def test_ranking_when_correct_chunk_is_second():
    scores = evaluate_ranking(
        retrieved_ids=["0", "1", "2"],
        relevant_ids={"1"},
        k=3,
    )

    assert scores["hit"] == 1.0
    assert scores["recall"] == 1.0
    assert scores["rr"] == 0.5


def test_ranking_when_correct_chunk_is_missing():
    scores = evaluate_ranking(
        retrieved_ids=["0", "2"],
        relevant_ids={"1"},
        k=2,
    )

    assert scores == {
        "hit": 0.0,
        "recall": 0.0,
        "rr": 0.0,
    }


def test_ranking_with_multiple_relevant_chunks():
    scores = evaluate_ranking(
        retrieved_ids=["0", "1"],
        relevant_ids={"1", "2"},
        k=2,
    )

    assert scores["hit"] == 1.0
    assert scores["recall"] == 0.5
    assert scores["rr"] == 0.5


def test_reject_unanswerable_ranking():
    with pytest.raises(ValueError):
        evaluate_ranking(
            retrieved_ids=["0"],
            relevant_ids=set(),
            k=1,
        )
