"""Pure report aggregation, baseline comparison and safe JSON persistence."""
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import json

from evaluation.generation_metrics import (
    GenerationEvaluationCase, calculate_generation_metrics,
)


def aggregate(rows: list[dict]) -> dict:
    """Errors are excluded from scored decisions and counted separately."""
    evaluated = [r for r in rows if r["status"] in ("answered", "abstained")]
    errors = [r for r in rows if r["status"] == "error"]
    decisions = [GenerationEvaluationCase(
        case_id=r["id"], question=r["question"], answerable=r["answerable"],
        answered=r["status"] == "answered", answer=r.get("answer", ""),
        sources_count=r.get("sources_count", 0),
    ) for r in evaluated]
    decision_metrics = asdict(calculate_generation_metrics(decisions)) if decisions else None
    judged = [r for r in evaluated if r.get("judge") is not None]
    judged_answerable = [r for r in judged if r["answerable"] and r["status"] == "answered"]
    return {
        "total_cases": len(rows),
        "evaluated_cases": len(evaluated),
        "error_cases": len(errors),
        "completion_rate": len(evaluated) / len(rows) if rows else 0.0,
        "decision_metrics": decision_metrics,
        "judge_metrics": {
            "judged_answers": len(judged_answerable),
            "correct_rate_among_judged": (
                sum(r["judge"]["correct"] for r in judged_answerable) / len(judged_answerable)
                if judged_answerable else None
            ),
            "faithful_rate_among_judged": (
                sum(r["judge"]["faithful"] for r in judged_answerable) / len(judged_answerable)
                if judged_answerable else None
            ),
        },
    }


def compare_baseline(current: dict, baseline: dict) -> dict:
    """Compare compatible evaluation runs; do not silently compare partial runs."""
    for field in ("dataset", "document_id", "top_k", "case_ids", "judge_enabled", "llm_model", "embedding_model",
                  "dataset_sha256", "stored_chunks_sha256", "rag_min_similarity"):
        if current.get(field) != baseline.get(field):
            raise ValueError(f"Baseline incompatible: {field} differs")
    a, b = current["summary"], baseline["summary"]
    if a["error_cases"] or b["error_cases"]:
        raise ValueError("Cannot compare runs containing execution errors")
    deltas = {}
    for key in ("answer_coverage", "abstention_accuracy", "unsupported_answer_rate", "decision_accuracy"):
        x = a["decision_metrics"][key]
        y = b["decision_metrics"][key]
        deltas[key] = round(x - y, 6)
    for key in ("correct_rate_among_judged", "faithful_rate_among_judged"):
        x = a["judge_metrics"][key]
        y = b["judge_metrics"][key]
        deltas[key] = None if x is None or y is None else round(x - y, 6)
    return {"baseline_generated_at": baseline.get("generated_at"), "deltas": deltas,
            "regression_flags": {
                "decision_accuracy_decreased": deltas["decision_accuracy"] < 0,
                "unsupported_answer_rate_increased": deltas["unsupported_answer_rate"] > 0,
                "judge_correctness_decreased": deltas["correct_rate_among_judged"] is not None and deltas["correct_rate_among_judged"] < 0,
                "judge_faithfulness_decreased": deltas["faithful_rate_among_judged"] is not None and deltas["faithful_rate_among_judged"] < 0,
            }}


def write_report(report: dict, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    # Timestamp + microseconds prevents collisions for back-to-back runs.
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    target = output_dir / f"generation_eval_{stamp}.json"
    with target.open("x", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return target
