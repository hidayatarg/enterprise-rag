import pytest

from evaluation.generation_metrics import (
    GenerationEvaluationCase,
    calculate_generation_metrics,
)


def make_case(
    case_id: str,
    answerable: bool,
    answered: bool,
) -> GenerationEvaluationCase:

    return GenerationEvaluationCase(
        case_id=case_id,
        question=f"Question {case_id}",
        answerable=answerable,
        answered=answered,
        answer=(
            "Generated answer"
            if answered
            else "I could not find this information."
        ),
        sources_count=1 if answered else 0,
    )


def test_perfect_generation_decisions():
    cases = [
        make_case("1", True, True),
        make_case("2", True, True),
        make_case("3", False, False),
    ]

    metrics = calculate_generation_metrics(cases)

    assert metrics.answer_coverage == 1.0
    assert metrics.abstention_accuracy == 1.0
    assert metrics.unsupported_answer_rate == 0.0
    assert metrics.decision_accuracy == 1.0


def test_partial_generation_success():
    cases = [
        make_case("1", True, True),
        make_case("2", True, True),
        make_case("3", True, False),
        make_case("4", True, False),
        make_case("5", False, False),
        make_case("6", False, True),
    ]

    metrics = calculate_generation_metrics(cases)

    assert metrics.answer_coverage == 0.5
    assert metrics.abstention_accuracy == 0.5
    assert metrics.unsupported_answer_rate == 0.5
    assert metrics.decision_accuracy == 0.5


def test_all_answerable_questions_abstained():
    cases = [
        make_case("1", True, False),
        make_case("2", True, False),
    ]

    metrics = calculate_generation_metrics(cases)

    assert metrics.answer_coverage == 0.0
    assert metrics.abstained_answerable == 2
    assert metrics.decision_accuracy == 0.0


def test_all_unanswerable_questions_answered():
    cases = [
        make_case("1", False, True),
        make_case("2", False, True),
    ]

    metrics = calculate_generation_metrics(cases)

    assert metrics.abstention_accuracy == 0.0
    assert metrics.unsupported_answer_rate == 1.0


def test_no_unanswerable_cases():
    cases = [
        make_case("1", True, True),
    ]

    metrics = calculate_generation_metrics(cases)

    assert metrics.answer_coverage == 1.0
    assert metrics.abstention_accuracy == 0.0
    assert metrics.unsupported_answer_rate == 0.0
    assert metrics.unanswerable_cases == 0


def test_no_answerable_cases():
    cases = [
        make_case("1", False, False),
    ]

    metrics = calculate_generation_metrics(cases)

    assert metrics.answer_coverage == 0.0
    assert metrics.abstention_accuracy == 1.0
    assert metrics.answerable_cases == 0


def test_empty_dataset_raises_error():
    with pytest.raises(
        ValueError,
        match="At least one evaluation case",
    ):
        calculate_generation_metrics([])


def test_metrics_count_all_cases():
    cases = [
        make_case("1", True, True),
        make_case("2", True, False),
        make_case("3", False, False),
        make_case("4", False, True),
    ]

    metrics = calculate_generation_metrics(cases)

    assert metrics.total_cases == 4
    assert metrics.answerable_cases == 2
    assert metrics.unanswerable_cases == 2

    assert metrics.answered_answerable == 1
    assert metrics.abstained_answerable == 1

    assert metrics.abstained_unanswerable == 1
    assert metrics.answered_unanswerable == 1
