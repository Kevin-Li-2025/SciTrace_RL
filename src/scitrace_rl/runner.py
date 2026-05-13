from __future__ import annotations

from pathlib import Path
from typing import Any

from .dashboard import render_dashboard
from .escalation import build_escalation_packet
from .learning_signal import build_post_training_bundle
from .provenance import build_provenance_bundle
from .schema import Artifact, Trace
from .tools import LiteratureSearchTool, MoleculeScreeningTool, ReportWriterTool
from .utils import read_json, sha256_json, write_json, write_text
from .validators import (
    aggregate_reward,
    validate_ai_claim_review,
    validate_citation_support,
    validate_citations,
    validate_claim_alignment,
    validate_claim_metadata,
    validate_constraints,
    validate_replay,
    validate_trajectory,
)


def run_task(task_path: Path, corpus_path: Path, output_dir: Path) -> dict[str, Any]:
    task = read_json(task_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    trace = Trace(task_id=task["task_id"], goal=task["goal"], domain=task["domain"])

    literature = LiteratureSearchTool(corpus_path).execute(query=task["retrieval_query"], top_k=task["top_k_sources"])
    trace.add_tool_call(literature.call)
    literature_artifact = trace.add_artifact(
        Artifact(
            kind="retrieved_evidence",
            uri=str(output_dir / "retrieved_sources.json"),
            summary=f"{len(literature.result['sources'])} retrieved sources for the task query.",
            metadata={"source_ids": literature.result["source_ids"]},
        )
    )
    literature.call.artifacts.append(literature_artifact.artifact_id)

    screening = MoleculeScreeningTool().execute(candidates=task["candidates"], constraints=task["constraints"])
    trace.add_tool_call(screening.call)
    screening_artifact = trace.add_artifact(
        Artifact(
            kind="ranked_candidates",
            uri=str(output_dir / "ranked_candidates.json"),
            summary="Candidate ranking with deterministic proxy chemistry features.",
            metadata={"top_candidate_id": screening.result["top_candidate"]["candidate_id"]},
        )
    )
    screening.call.artifacts.append(screening_artifact.artifact_id)

    report = ReportWriterTool().execute(
        task=task,
        sources=literature.result["sources"],
        screening=screening.result,
    )
    trace.add_tool_call(report.call)
    report_artifact = trace.add_artifact(
        Artifact(
            kind="agent_report",
            uri=str(output_dir / "demo_report.md"),
            summary="Citation-grounded candidate report generated from trace artifacts.",
            metadata={"claim_count": len(report.result["claims"])},
        )
    )
    report.call.artifacts.append(report_artifact.artifact_id)

    validations = [
        validate_trajectory(trace.tools, trace.artifacts),
        validate_citations(report.result, literature.result["sources"]),
        validate_citation_support(report.result, literature.result["sources"]),
        validate_replay(task["candidates"], task["constraints"], screening.result),
        validate_constraints(screening.result),
        validate_claim_alignment(report.result, screening.result),
        validate_claim_metadata(report.result),
        validate_ai_claim_review(
            report.result,
            literature.result["sources"],
            artifacts={
                "ranked_candidates": screening.result["ranked_candidates"],
                "top_candidate": screening.result["top_candidate"],
                "validation_policy": {
                    "recommendation_status": "provisional",
                    "promotion_rule": "Promote only after citation integrity, artifact replay, constraint satisfaction, and claim-evidence alignment pass.",
                    "next_step": "Replace proxy screen with higher-fidelity simulation or wet-lab validation before deployment.",
                },
            },
        ),
    ]
    for validation in validations:
        trace.add_validation(validation)

    validation_artifact = trace.add_artifact(
        Artifact(
            kind="validation_scorecard",
            uri=str(output_dir / "validation_scorecard.json"),
            summary="Machine-readable validation gates for the scientific-agent run.",
            metadata={"validation_names": [validation.name for validation in trace.validations]},
        )
    )
    trace.reward = aggregate_reward(
        trace.validations,
        {
            "total_tool_calls": len(trace.tools),
            "successful_tool_calls": sum(1 for call in trace.tools if call.status == "success"),
        },
    )
    reward_artifact = trace.add_artifact(
        Artifact(
            kind="trace_to_reward_sample",
            uri=str(output_dir / "trace_to_reward_sample.json"),
            summary="Reward-labeled training sample derived from the validated execution trace.",
            metadata={"reward": trace.reward["reward"]},
        )
    )
    provenance_artifact = trace.add_artifact(
        Artifact(
            kind="provenance_bundle",
            uri=str(output_dir / "provenance_bundle.json"),
            summary="Interoperability export aligned with W3C PROV, Workflow Run RO-Crate, and OpenTelemetry spans.",
            metadata={
                "profiles": [
                    "W3C PROV",
                    "Workflow Run RO-Crate",
                    "OpenTelemetry GenAI semantic conventions",
                ]
            },
        )
    )
    post_training_artifact = trace.add_artifact(
        Artifact(
            kind="post_training_bundle",
            uri=str(output_dir / "post_training_bundle.json"),
            summary="SFT, DPO, process-reward, credit-assignment, and tool-router records derived from the run.",
            metadata={
                "formats": [
                    "sft_chat_record",
                    "dpo_preference_pair",
                    "process_reward_steps",
                    "tool_router_records",
                    "credit_assignment",
                ]
            },
        )
    )
    escalation_artifact = trace.add_artifact(
        Artifact(
            kind="escalation_packet",
            uri=str(output_dir / "escalation_packet.json"),
            summary="Handoff packet for high-fidelity computation, wet-lab validation, expert review, and feedback ingestion.",
            metadata={
                "target_systems": [
                    "Bohrium/Lebesgue",
                    "Uni-Lab-OS",
                    "domain_expert",
                    "SciTrace-RL trace store",
                ]
            },
        )
    )

    trace.metrics = {
        "total_tool_calls": len(trace.tools),
        "successful_tool_calls": sum(1 for call in trace.tools if call.status == "success"),
        "total_duration_ms": sum(call.duration_ms for call in trace.tools),
        "max_tool_duration_ms": max((call.duration_ms for call in trace.tools), default=0),
        "avg_tool_duration_ms": round(sum(call.duration_ms for call in trace.tools) / max(len(trace.tools), 1), 3),
        "tool_duration_ms": {call.name: call.duration_ms for call in trace.tools},
        "estimated_cost_units": round(len(trace.tools) + len(trace.artifacts) * 0.2, 3),
        "artifact_count": len(trace.artifacts),
        "validation_count": len(trace.validations),
        "screening_output_hash": sha256_json(screening.result),
    }
    trace_dict = trace.to_dict()

    write_json(output_dir / "retrieved_sources.json", literature.result)
    write_json(output_dir / "ranked_candidates.json", screening.result)
    write_text(output_dir / "demo_report.md", report.result["markdown"])
    write_json(output_dir / "validation_scorecard.json", [validation.__dict__ for validation in trace.validations])
    write_json(output_dir / "demo_trace.json", trace_dict)
    write_json(output_dir / "provenance_bundle.json", build_provenance_bundle(trace_dict))
    write_json(output_dir / "post_training_bundle.json", build_post_training_bundle(trace_dict, task, report.result, screening.result))
    write_json(output_dir / "escalation_packet.json", build_escalation_packet(trace_dict, task, report.result, screening.result))
    render_dashboard(trace_dict, report.result["markdown"], output_dir / "demo_dashboard.html")
    write_json(
        output_dir / "trace_to_reward_sample.json",
        {
            "trace_id": trace_dict["trace_id"],
            "task_id": trace_dict["task_id"],
            "inputs": {
                "goal": task["goal"],
                "candidate_ids": [candidate["candidate_id"] for candidate in task["candidates"]],
            },
            "tool_sequence": [call["name"] for call in trace_dict["tools"]],
            "validation_scores": {item["name"]: item["score"] for item in trace_dict["validations"]},
            "reward": trace_dict["reward"],
            "label_semantics": "One offline training sample for planner/tool-router reward modeling.",
            "source_artifacts": [
                literature_artifact.artifact_id,
                screening_artifact.artifact_id,
                report_artifact.artifact_id,
                validation_artifact.artifact_id,
                reward_artifact.artifact_id,
                provenance_artifact.artifact_id,
                post_training_artifact.artifact_id,
                escalation_artifact.artifact_id,
            ],
        },
    )
    return trace_dict
