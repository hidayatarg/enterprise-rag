"""Fast offline tests for the live runner's decision and error behavior."""
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import MagicMock
import pytest

from evaluation.run_generation_eval import classify_result, evaluate_case, evidence_for_sources
from app.rag_service import ABSTAIN_MESSAGE


def test_abstention_even_if_context_was_retrieved():
    result = SimpleNamespace(answer=ABSTAIN_MESSAGE, sources=[], context_found=True)
    assert classify_result(result, ABSTAIN_MESSAGE) == "abstained"


def test_accepts_answer_with_cited_source():
    result = SimpleNamespace(answer="5 business days", sources=[{"chunk_index": 0}], context_found=True)
    assert classify_result(result, ABSTAIN_MESSAGE) == "answered"


def test_rejects_answer_without_cited_source():
    result = SimpleNamespace(answer="Unsupported response", sources=[], context_found=True)
    with pytest.raises(ValueError, match="no validated sources"):
        classify_result(result, ABSTAIN_MESSAGE)


def test_evidence_uses_only_cited_chunks_and_deduplicates():
    stored = {0: "Policy A", 1: "Policy B"}
    sources = [{"chunk_index": 1}, {"chunk_index": 1}]
    assert evidence_for_sources(stored, sources) == ["Policy B"]


def test_evidence_rejects_missing_chunk():
    with pytest.raises(ValueError, match="missing"):
        evidence_for_sources({}, [{"chunk_index": 9}])


def test_case_calls_existing_rag_pipeline():
    answer = SimpleNamespace(answer="5 business days", sources=[{"chunk_index": 0}], context_found=True)
    rag = MagicMock(return_value=answer)
    case = {"id": "t1", "category": "direct_fact", "question": "How long?", "answerable": True,
            "expected_answer": "5 business days"}
    record = evaluate_case(case, document_id=uuid4(), db=MagicMock(), ai=MagicMock(),
                           stored_chunks={0:"Approved refunds are processed within 5 business days."},
                           top_k=5, abstain_message=ABSTAIN_MESSAGE, enable_judge=False,
                           rag_function=rag)
    assert record["status"] == "answered"
    assert record["sources_count"] == 1
    assert record["judge"] is None
    rag.assert_called_once()
