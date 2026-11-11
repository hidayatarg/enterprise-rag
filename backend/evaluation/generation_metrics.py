
""" RAG Generation Evaluation Metrics.
Measures whether the RAG system makes the correct
decision to answer or abstain.

These metrics do NOT prove factual correctness.
Semantic answer correctness is evaluated separately."""

from dataclasses import dataclass
from collections.abc import Sequence


@dataclass(frozen=True)
class GenerationEvaluationCase:
    case_id: str
    question: str
    answerable: bool
    answered: bool
    answer: str
    sources_count: int


@dataclass(frozen=True)
class GenerationMetrics:
    total_cases: int
    answerable_cases: int
    unanswerable_cases: int

    answered_answerable: int
    abstained_answerable: int

    abstained_unanswerable: int
    answered_unanswerable: int

    answer_coverage: float
    abstention_accuracy: float
    unsupported_answer_rate: float
    decision_accuracy: float


def calculate_generation_metrics(
    cases: Sequence[GenerationEvaluationCase],
) -> GenerationMetrics:
    """
    Evaluate answer/abstain decisions.

    An answerable case is considered successful when
    the system returns an answer.

    This does not establish whether that answer is
    factually correct or faithful to its sources.
    """

    if not cases:
        raise ValueError(
            "At least one evaluation case is required"
        )

    answerable = [
        case for case in cases
        if case.answerable
    ]

    unanswerable = [
        case for case in cases
        if not case.answerable
    ]

    answered_answerable = sum(
        case.answered
        for case in answerable
    )

    abstained_answerable = (
        len(answerable) - answered_answerable
    )

    abstained_unanswerable = sum(
        not case.answered
        for case in unanswerable
    )

    answered_unanswerable = (
        len(unanswerable) - abstained_unanswerable
    )

    answer_coverage = (
        answered_answerable / len(answerable)
        if answerable
        else 0.0
    )

    abstention_accuracy = (
        abstained_unanswerable / len(unanswerable)
        if unanswerable
        else 0.0
    )

    unsupported_answer_rate = (
        answered_unanswerable / len(unanswerable)
        if unanswerable
        else 0.0
    )

    decision_accuracy = (
        answered_answerable + abstained_unanswerable
    ) / len(cases)

    return GenerationMetrics(
        total_cases=len(cases),
        answerable_cases=len(answerable),
        unanswerable_cases=len(unanswerable),

        answered_answerable=answered_answerable,
        abstained_answerable=abstained_answerable,

        abstained_unanswerable=abstained_unanswerable,
        answered_unanswerable=answered_unanswerable,

        answer_coverage=answer_coverage,
        abstention_accuracy=abstention_accuracy,
        unsupported_answer_rate=unsupported_answer_rate,
        decision_accuracy=decision_accuracy,
    )
