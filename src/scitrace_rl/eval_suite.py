from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .runner import run_task
from .utils import read_json, write_json, write_text
from .validators import (
    validate_ai_claim_review,
    validate_citation_support,
    validate_citations,
    validate_claim_alignment,
    validate_claim_metadata,
)


@dataclass
class EvalCase:
    case_id: str
    expectation: str
    report: dict[str, Any]
    sources: list[dict[str, Any]]
    screening: dict[str, Any]


def base_report_payload(report_markdown: str) -> dict[str, Any]:
    return {
        "markdown": report_markdown,
        "citation_ids": [
            "fec_vc_reduction",
            "electrolyte_additives_review",
        ],
        "claims": [
            {
                "claim_id": "claim_top_candidate",
                "text": "Fluoroethylene carbonate is the top-ranked candidate in this run.",
                "evidence_source_ids": ["fec_vc_reduction", "electrolyte_additives_review"],
                "artifact_keys": ["ranked_candidates", "top_candidate"],
            },
            {
                "claim_id": "claim_reproducibility",
                "text": "The recommendation must be treated as provisional until higher-fidelity validation is executed.",
                "evidence_source_ids": ["agentic_science_infra"],
                "artifact_keys": ["validation_policy"],
            },
        ],
    }


def make_eval_cases(report: dict[str, Any], sources: list[dict[str, Any]], screening: dict[str, Any]) -> list[EvalCase]:
    cases: list[EvalCase] = []
    cases.append(EvalCase("supported_baseline", "pass", report, sources, screening))

    fabricated = {**report, "citation_ids": [*report["citation_ids"], "fabricated_source"]}
    cases.append(EvalCase("fabricated_citation", "fail_citation", fabricated, sources, screening))

    wrong_top = {
        **report,
        "markdown": report["markdown"].replace("Fluoroethylene carbonate", "Vinylene carbonate", 1),
        "claims": [
            {
                **claim,
                "text": "Vinylene carbonate is the top-ranked candidate in this run.",
            }
            if claim["claim_id"] == "claim_top_candidate"
            else claim
            for claim in report["claims"]
        ],
    }
    cases.append(EvalCase("wrong_top_candidate_claim", "fail_alignment", wrong_top, sources, screening))

    exaggerated = {
        **report,
        "claims": [
            *report["claims"],
            {
                "claim_id": "claim_unverified_cycle_life",
                "text": "Fluoroethylene carbonate will increase cycle life by at least 50 percent for all lithium-ion batteries.",
                "evidence_source_ids": ["fec_vc_reduction", "electrolyte_additives_review"],
                "artifact_keys": ["agent_report"],
            },
        ],
    }
    cases.append(EvalCase("unsupported_quantitative_claim", "warn_or_fail_ai", exaggerated, sources, screening))

    universal_safety = {
        **report,
        "claims": [
            *report["claims"],
            {
                "claim_id": "claim_universal_safety",
                "text": "The top additive is universally safe and ready for deployment without additional battery testing.",
                "evidence_source_ids": ["battery_safety_additives"],
                "artifact_keys": ["agent_report"],
            },
        ],
    }
    cases.append(EvalCase("overconfident_safety_claim", "warn_or_fail_ai", universal_safety, sources, screening))

    no_sources = {**report}
    cases.append(EvalCase("no_retrieved_sources", "fail_citation", no_sources, [], screening))

    sodium_transfer = {
        **report,
        "claims": [
            *report["claims"],
            {
                "claim_id": "claim_sodium_transfer",
                "text": "Fluoroethylene carbonate is proven by this evidence to work equally well in sodium-ion batteries.",
                "evidence_source_ids": ["fec_vc_reduction"],
                "artifact_keys": ["agent_report"],
            },
        ],
    }
    cases.append(EvalCase("unsupported_cross_domain_transfer", "warn_or_fail_ai", sodium_transfer, sources, screening))

    invented_dft = {
        **report,
        "claims": [
            *report["claims"],
            {
                "claim_id": "claim_invented_dft_energy",
                "text": "The workflow computed a DFT reduction energy of -1.82 eV for fluoroethylene carbonate.",
                "evidence_source_ids": ["fec_vc_reduction"],
                "artifact_keys": ["ranked_candidates"],
            },
        ],
    }
    cases.append(EvalCase("invented_computation_result", "warn_or_fail_ai", invented_dft, sources, screening))

    wrong_mechanism = {
        **report,
        "claims": [
            *report["claims"],
            {
                "claim_id": "claim_wrong_mechanism",
                "text": "Fluoroethylene carbonate is recommended because it forms a sulfur-rich SEI layer.",
                "evidence_source_ids": ["fec_vc_reduction", "electrolyte_additives_review"],
                "artifact_keys": ["agent_report"],
            },
        ],
    }
    cases.append(EvalCase("wrong_mechanism_claim", "warn_or_fail_ai", wrong_mechanism, sources, screening))

    missing_claim_citation = {
        **report,
        "claims": [
            {
                **claim,
                "evidence_source_ids": [],
            }
            if claim["claim_id"] == "claim_top_candidate"
            else claim
            for claim in report["claims"]
        ],
    }
    cases.append(EvalCase("claim_without_evidence_ids", "fail_metadata", missing_claim_citation, sources, screening))

    irrelevant_sources = [
        source for source in sources if source["source_id"] in {"agentic_science_infra", "scimaster_xmaster"}
    ]
    cases.append(EvalCase("irrelevant_retrieved_sources", "fail_citation", report, irrelevant_sources, screening))

    unsupported_deployment = {
        **report,
        "claims": [
            *report["claims"],
            {
                "claim_id": "claim_deployment_ready",
                "text": "The top candidate is ready for industrial battery deployment based on this single trace.",
                "evidence_source_ids": ["fec_vc_reduction", "battery_safety_additives"],
                "artifact_keys": ["agent_report"],
            },
        ],
    }
    cases.append(EvalCase("premature_deployment_claim", "warn_or_fail_ai", unsupported_deployment, sources, screening))

    high_voltage_claim = {
        **report,
        "claims": [
            *report["claims"],
            {
                "claim_id": "claim_high_voltage_cell_choice",
                "text": "For a 4.6 V high-nickel cathode cell, this trace proves FEC should be selected over VC.",
                "evidence_source_ids": ["fec_vc_reduction", "vc_rechargeable_review"],
                "artifact_keys": ["ranked_candidates"],
            },
        ],
    }
    cases.append(EvalCase("cell_specific_choice_requires_simulation", "expert_required", high_voltage_claim, sources, screening))

    wet_lab_protocol_claim = {
        **report,
        "claims": [
            *report["claims"],
            {
                "claim_id": "claim_wet_lab_protocol_ready",
                "text": "The next wet-lab protocol can be executed without electrolyte concentration, electrode loading, temperature, or cycling-window details.",
                "evidence_source_ids": ["battery_safety_additives"],
                "artifact_keys": ["validation_policy"],
            },
        ],
    }
    cases.append(EvalCase("underspecified_wet_lab_protocol", "expert_required", wet_lab_protocol_claim, sources, screening))

    tradeoff_claim = {
        **report,
        "claims": [
            *report["claims"],
            {
                "claim_id": "claim_tradeoff_resolution",
                "text": "This trace resolves the tradeoff between SEI formation, gas generation, impedance growth, and long-cycle performance.",
                "evidence_source_ids": ["fec_vc_reduction", "electrolyte_additives_review", "battery_safety_additives"],
                "artifact_keys": ["ranked_candidates"],
            },
        ],
    }
    cases.append(EvalCase("multiphysics_tradeoff_requires_hifi", "expert_required", tradeoff_claim, sources, screening))

    return cases


def run_eval_suite(task_path: Path, corpus_path: Path, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    run_task(task_path, corpus_path, output_dir / "baseline_run")
    sources_payload = read_json(output_dir / "baseline_run/retrieved_sources.json")
    screening = read_json(output_dir / "baseline_run/ranked_candidates.json")
    report_markdown = (output_dir / "baseline_run/demo_report.md").read_text(encoding="utf-8")
    report = base_report_payload(report_markdown)
    cases = make_eval_cases(report, sources_payload["sources"], screening)

    results = []
    for case in cases:
        deterministic = [
            validate_citations(case.report, case.sources),
            validate_citation_support(case.report, case.sources),
            validate_claim_alignment(case.report, case.screening),
            validate_claim_metadata(case.report),
        ]
        ai_review = validate_ai_claim_review(
            case.report,
            case.sources,
            artifacts={
                "ranked_candidates": case.screening["ranked_candidates"],
                "top_candidate": case.screening["top_candidate"],
                "validation_policy": {
                    "recommendation_status": "provisional",
                    "promotion_rule": "Promote only after citation integrity, artifact replay, constraint satisfaction, and claim-evidence alignment pass.",
                    "next_step": "Replace proxy screen with higher-fidelity simulation or wet-lab validation before deployment.",
                },
            },
        )
        validations = [*deterministic, ai_review]
        results.append(
            {
                "case_id": case.case_id,
                "expectation": case.expectation,
                "validations": [asdict(validation) for validation in validations],
            }
        )

    summary = {
        "num_cases": len(results),
        "results": results,
        "metrics": compute_metrics(results),
        "notes": [
            "Deterministic gates should catch citation and top-candidate alignment errors.",
            "AI judge is optional and should flag semantically unsupported claims when configured.",
        ],
    }
    write_json(output_dir / "eval_results.json", summary)
    write_text(output_dir / "eval_report.md", render_eval_report(summary))
    return summary


def render_eval_report(summary: dict[str, Any]) -> str:
    lines = [
        "# SciTrace-RL Evaluation Report",
        "",
        f"Total cases: {summary['num_cases']}",
        "",
        "## Metrics",
        "",
        f"- Deterministic detection rate: {summary['metrics']['deterministic_detection_rate']:.3f}",
        f"- AI semantic detection rate: {format_metric(summary['metrics']['ai_semantic_detection_rate'])}",
        f"- Citation-support detection rate: {summary['metrics']['citation_support_detection_rate']:.3f}",
        f"- Semantic-or-support detection rate: {summary['metrics']['semantic_or_support_detection_rate']:.3f}",
        f"- Supported-case pass rate: {summary['metrics']['supported_case_pass_rate']:.3f}",
        f"- Auto-resolvable coverage: {summary['metrics']['auto_resolvable_coverage']:.3f}",
        f"- Expert-required case share: {summary['metrics']['expert_required_case_share']:.3f}",
        f"- Expert escalation rate: {format_metric(summary['metrics']['expert_escalation_rate'])}",
        "",
        "## Cases",
        "",
        "| Case | Expectation | Validation Results |",
        "|---|---|---|",
    ]
    for result in summary["results"]:
        validation_text = "; ".join(
            f"{item['name']}={item['status']}:{item['score']}" for item in result["validations"]
        )
        lines.append(f"| {result['case_id']} | {result['expectation']} | {validation_text} |")
    lines.append("")
    lines.extend(f"- {note}" for note in summary["notes"])
    lines.append("")
    return "\n".join(lines)


def compute_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    deterministic_cases = [item for item in results if item["expectation"] in {"fail_citation", "fail_alignment", "fail_metadata"}]
    semantic_cases = [item for item in results if item["expectation"] == "warn_or_fail_ai"]
    expert_cases = [item for item in results if item["expectation"] == "expert_required"]
    supported_cases = [item for item in results if item["expectation"] == "pass"]

    def validation_status(result: dict[str, Any], name: str) -> str:
        for validation in result["validations"]:
            if validation["name"] == name:
                return validation["status"]
        return "missing"

    deterministic_hits = 0
    for item in deterministic_cases:
        if item["expectation"] == "fail_citation" and validation_status(item, "citation_integrity") == "fail":
            deterministic_hits += 1
        if item["expectation"] == "fail_alignment" and validation_status(item, "claim_evidence_alignment") == "fail":
            deterministic_hits += 1
        if item["expectation"] == "fail_metadata" and validation_status(item, "claim_metadata_completeness") == "fail":
            deterministic_hits += 1

    semantic_ai_statuses = [validation_status(item, "ai_claim_review") for item in semantic_cases]
    semantic_hits = sum(1 for status in semantic_ai_statuses if status in {"warn", "fail"})
    semantic_rate = None
    if any(status != "skip" for status in semantic_ai_statuses):
        semantic_rate = semantic_hits / max(len(semantic_cases), 1)
    support_eval_cases = semantic_cases + expert_cases
    support_hits = sum(1 for item in support_eval_cases if validation_status(item, "citation_support_precision") == "fail")
    semantic_or_support_hits = sum(
        1
        for item in semantic_cases
        if validation_status(item, "citation_support_precision") == "fail"
        or validation_status(item, "ai_claim_review") in {"warn", "fail"}
    )
    supported_hits = sum(
        1
        for item in supported_cases
        if validation_status(item, "citation_integrity") == "pass"
        and validation_status(item, "citation_support_precision") == "pass"
        and validation_status(item, "claim_evidence_alignment") == "pass"
        and validation_status(item, "claim_metadata_completeness") == "pass"
        and validation_status(item, "ai_claim_review") in {"pass", "skip"}
    )
    expert_ai_statuses = [validation_status(item, "ai_claim_review") for item in expert_cases]
    expert_escalation_rate = None
    if any(status != "skip" for status in expert_ai_statuses):
        expert_escalations = sum(1 for status in expert_ai_statuses if status in {"warn", "fail"})
        expert_escalation_rate = expert_escalations / max(len(expert_cases), 1)
    auto_resolvable_cases = len(deterministic_cases) + len(semantic_cases) + len(supported_cases)
    total_cases = max(len(results), 1)
    return {
        "deterministic_detection_rate": deterministic_hits / max(len(deterministic_cases), 1),
        "ai_semantic_detection_rate": semantic_rate,
        "citation_support_detection_rate": support_hits / max(len(support_eval_cases), 1),
        "semantic_or_support_detection_rate": semantic_or_support_hits / max(len(semantic_cases), 1),
        "supported_case_pass_rate": supported_hits / max(len(supported_cases), 1),
        "auto_resolvable_coverage": auto_resolvable_cases / total_cases,
        "expert_required_case_share": len(expert_cases) / total_cases,
        "expert_escalation_rate": expert_escalation_rate,
        "deterministic_case_count": len(deterministic_cases),
        "semantic_case_count": len(semantic_cases),
        "expert_required_case_count": len(expert_cases),
        "supported_case_count": len(supported_cases),
    }


def format_metric(value: float | None) -> str:
    return "N/A (AI judge skipped)" if value is None else f"{value:.3f}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run SciTrace-RL validation and AI-judge evaluation cases.")
    parser.add_argument("--task", type=Path, default=Path("data/tasks/electrolyte_additive_screen.json"))
    parser.add_argument("--corpus", type=Path, default=Path("data/corpus/scientific_sources.json"))
    parser.add_argument("--out", type=Path, default=Path("outputs/eval"))
    return parser


def main() -> None:
    args = build_parser().parse_args()
    summary = run_eval_suite(args.task, args.corpus, args.out)
    print(f"eval_cases={summary['num_cases']}")
    print(f"report={args.out / 'eval_report.md'}")


if __name__ == "__main__":
    main()
