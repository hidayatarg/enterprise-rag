"""Offline tests for aggregates, baseline compatibility and report persistence."""
import json
import pytest
from evaluation.reporting import aggregate, compare_baseline, write_report


def row(id, answerable, status, judge=None):
    return {"id":id, "question":id, "answerable":answerable,
            "status":status,"answer":"text", "sources_count":int(status=="answered"),
            "judge":judge}


def test_metrics_exclude_errors_instead_of_counting_as_abstention():
    result = aggregate([row("a",True,"answered"),row("b",False,"abstained"),row("c",False,"error")])
    assert result["total_cases"] == 3
    assert result["evaluated_cases"] == 2
    assert result["error_cases"] == 1
    assert result["completion_rate"] == pytest.approx(2/3)
    assert result["decision_metrics"]["decision_accuracy"] == 1.0


def test_judge_metrics_only_include_judged_answerable_answers():
    result = aggregate([row("a",True,"answered", {"correct":True,"faithful":False}),
                        row("b",True,"abstained"),row("c",False,"abstained")])
    metrics = result["judge_metrics"]
    assert metrics["judged_answers"] == 1
    assert metrics["correct_rate_among_judged"] == 1.0
    assert metrics["faithful_rate_among_judged"] == 0.0


def report(rows):
    return {"dataset":"demo", "document_id":"doc", "top_k":5, "case_ids":["a","b"],
            "judge_enabled":False, "llm_model":"llama3.2", "embedding_model":"embeddinggemma",
            "generated_at":"date", "summary":aggregate(rows),
            "dataset_sha256":"same", "stored_chunks_sha256":"same", "rag_min_similarity":0.45}


def test_comparison_detects_regression():
    baseline = report([row("a",True,"answered"),row("b",False,"abstained")])
    current = report([row("a",True,"abstained"),row("b",False,"answered")])
    comparison = compare_baseline(current, baseline)
    assert comparison["deltas"]["decision_accuracy"] == -1.0
    assert comparison["regression_flags"]["decision_accuracy_decreased"]
    assert comparison["regression_flags"]["unsupported_answer_rate_increased"]


def test_comparison_rejects_changed_model():
    baseline = report([row("a",True,"answered"),row("b",False,"abstained")])
    current = report([row("a",True,"answered"),row("b",False,"abstained")])
    current["llm_model"] = "other-model"
    with pytest.raises(ValueError, match="llm_model"):
        compare_baseline(current,baseline)


def test_comparison_rejects_partial_run():
    baseline = report([row("a",True,"answered"),row("b",False,"abstained")])
    current = report([row("a",True,"answered"),row("b",False,"error")])
    with pytest.raises(ValueError, match="execution errors"):
        compare_baseline(current,baseline)


def test_report_is_valid_json(tmp_path):
    data = report([row("a",True,"answered"),row("b",False,"abstained")])
    file = write_report(data,tmp_path)
    assert file.exists()
    assert json.loads(file.read_text())["dataset"] == "demo"
