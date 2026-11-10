
import json
from pathlib import Path

import pytest


DATASET_PATH = (
    Path(__file__).resolve().parents[2]
    / "evaluation"
    / "datasets"
    / "refund_policy.json"
)


@pytest.fixture
def dataset():
    with DATASET_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def test_dataset_contains_cases(dataset):
    assert dataset["dataset_name"] == "refund_policy_v1"
    assert len(dataset["cases"]) >= 8


def test_case_ids_are_unique(dataset):
    ids = [
        case["id"]
        for case in dataset["cases"]
    ]

    assert len(ids) == len(set(ids))


def test_required_fields_exist(dataset):
    required_fields = {
        "id",
        "question",
        "answerable",
        "expected_answer",
        "expected_evidence",
        "category",
    }

    for case in dataset["cases"]:
        assert required_fields.issubset(case.keys())


def test_answerable_cases_have_evidence(dataset):
    for case in dataset["cases"]:
        if case["answerable"]:
            assert case["expected_answer"]
            assert case["expected_evidence"]


def test_unanswerable_cases_have_no_expected_answer(dataset):
    for case in dataset["cases"]:
        if not case["answerable"]:
            assert case["expected_answer"] is None
            assert case["expected_evidence"] == []


def test_dataset_has_positive_and_negative_cases(dataset):
    answerable = [
        case for case in dataset["cases"]
        if case["answerable"]
    ]

    unanswerable = [
        case for case in dataset["cases"]
        if not case["answerable"]
    ]

    assert len(answerable) > 0
    assert len(unanswerable) > 0


def test_questions_are_not_empty(dataset):
    for case in dataset["cases"]:
        assert case["question"].strip()


def test_categories_include_reasoning(dataset):
    categories = {
        case["category"]
        for case in dataset["cases"]
    }

    assert "direct_fact" in categories
    assert "policy_reasoning" in categories
    assert "unanswerable" in categories
