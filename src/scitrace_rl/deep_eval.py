from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .eval_suite import run_eval_suite
from .external_feedback import (
    build_external_result_fixture,
    ingest_external_result,
    validate_external_result_ingestion,
)
from .runner import run_task
from .utils import read_json, sha256_json, write_json, write_text


def run_deep_eval(task_path: Path, corpus_path: Path, output_dir: Path, stability_runs: int = 5) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    adversarial = run_eval_suite(task_path, corpus_path, output_dir / "adversarial")
    stability = run_stability_eval(task_path, corpus_path, output_dir / "stability", stability_runs)
    external = run_external_ingestion_eval(task_path, corpus_path, output_dir / "external_ingestion")
    summary = {
        "adversarial": adversarial["metrics"],
        "stability": stability,
        "external_ingestion": external["validation"],
        "overall_status": "pass"
        if stability["status"] == "pass" and external["validation"]["status"] == "pass"
        else "fail",
    }
    write_json(output_dir / "deep_eval_results.json", summary)
    write_text(output_dir / "deep_eval_report.md", render_deep_eval_report(summary))
    return summary


def run_stability_eval(task_path: Path, corpus_path: Path, output_dir: Path, runs: int) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    records = []
    for index in range(runs):
        run_dir = output_dir / f"run_{index + 1:02d}"
        trace = run_task(task_path, corpus_path, run_dir)
        screening = read_json(run_dir / "ranked_candidates.json")
        report = (run_dir / "demo_report.md").read_text(encoding="utf-8")
        records.append(
            {
                "run_id": index + 1,
                "trace_id": trace["trace_id"],
                "top_candidate_id": screening["top_candidate"]["candidate_id"],
                "screening_output_hash": trace["metrics"]["screening_output_hash"],
                "validation_statuses": {item["name"]: item["status"] for item in trace["validations"]},
                "reward": trace["reward"]["reward"],
                "tool_sequence": [call["name"] for call in trace["tools"]],
                "report_hash": sha256_json(report),
            }
        )
    reference = records[0]
    drift = []
    for record in records[1:]:
        for key in ["top_candidate_id", "screening_output_hash", "validation_statuses", "reward", "tool_sequence", "report_hash"]:
            if record[key] != reference[key]:
                drift.append({"run_id": record["run_id"], "field": key, "expected": reference[key], "actual": record[key]})
    result = {
        "status": "pass" if not drift else "fail",
        "runs": runs,
        "drift_count": len(drift),
        "drift": drift,
        "reference": reference,
    }
    write_json(output_dir / "stability_results.json", result)
    return result


def run_external_ingestion_eval(task_path: Path, corpus_path: Path, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    trace = run_task(task_path, corpus_path, output_dir / "base_run")
    screening = read_json(output_dir / "base_run/ranked_candidates.json")
    post_training = read_json(output_dir / "base_run/post_training_bundle.json")
    escalation = read_json(output_dir / "base_run/escalation_packet.json")
    external_result = build_external_result_fixture(screening)
    ingestion = ingest_external_result(trace, post_training, escalation, external_result)
    validation = validate_external_result_ingestion(ingestion)
    result = {
        "external_result": external_result,
        "ingestion": ingestion,
        "validation": validation,
    }
    write_json(output_dir / "external_ingestion_results.json", result)
    return result


def render_deep_eval_report(summary: dict[str, Any]) -> str:
    lines = [
        "# SciTrace-RL Deep Evaluation Report",
        "",
        f"Overall status: `{summary['overall_status']}`",
        "",
        "## Adversarial Eval",
        "",
    ]
    for key, value in summary["adversarial"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Multi-Run Stability",
            "",
            f"- status: {summary['stability']['status']}",
            f"- runs: {summary['stability']['runs']}",
            f"- drift_count: {summary['stability']['drift_count']}",
            "",
            "## External Result Ingestion",
            "",
            f"- status: {summary['external_ingestion']['status']}",
            f"- score: {summary['external_ingestion']['score']}",
            f"- issues: {summary['external_ingestion']['issues']}",
            "",
        ]
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run deep SciTrace-RL evaluation: adversarial, stability, and external feedback.")
    parser.add_argument("--task", type=Path, default=Path("data/tasks/electrolyte_additive_screen.json"))
    parser.add_argument("--corpus", type=Path, default=Path("data/corpus/scientific_sources.json"))
    parser.add_argument("--out", type=Path, default=Path("outputs/deep_eval"))
    parser.add_argument("--stability-runs", type=int, default=5)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    summary = run_deep_eval(args.task, args.corpus, args.out, args.stability_runs)
    print(f"overall_status={summary['overall_status']}")
    print(f"report={args.out / 'deep_eval_report.md'}")


if __name__ == "__main__":
    main()
