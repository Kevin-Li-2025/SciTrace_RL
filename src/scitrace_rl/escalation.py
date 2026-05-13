from __future__ import annotations

from typing import Any

from .utils import compact_id


SCHEMA_VERSION = "0.1"


def build_escalation_packet(
    trace: dict[str, Any],
    task: dict[str, Any],
    report: dict[str, Any],
    screening: dict[str, Any],
) -> dict[str, Any]:
    """Create the handoff packet for simulation, lab, or expert validation."""
    top_candidate = screening["top_candidate"]
    packet = {
        "schema_version": SCHEMA_VERSION,
        "trace_id": trace["trace_id"],
        "task_id": trace["task_id"],
        "recommendation_status": "provisional",
        "why_not_final": [
            "Current screening uses deterministic proxy features, not high-fidelity electrochemical simulation.",
            "No wet-lab protocol, cell format, cycling condition, or safety result has been executed.",
            "The validation gates can check trace consistency, but cannot replace physical feedback.",
        ],
        "candidate_under_review": {
            "candidate_id": top_candidate["candidate_id"],
            "name": top_candidate["name"],
            "formula": top_candidate["formula"],
            "screening_score": top_candidate["screening_score"],
        },
        "linked_artifacts": [
            artifact["artifact_id"]
            for artifact in trace["artifacts"]
            if artifact["kind"] != "escalation_packet"
        ],
        "validation_snapshot": {
            validation["name"]: {
                "status": validation["status"],
                "score": validation["score"],
            }
            for validation in trace["validations"]
        },
        "escalation_items": [
            _computational_validation_item(task, top_candidate),
            _wet_lab_validation_item(task, top_candidate),
            _expert_boundary_review_item(task, report),
            _feedback_ingestion_item(trace),
        ],
    }
    for item in packet["escalation_items"]:
        item["item_id"] = compact_id("escalation", item)
    packet["packet_id"] = compact_id("escalation_packet", packet)
    return packet


def _computational_validation_item(task: dict[str, Any], top_candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": "computational_validation",
        "target_system": "Bohrium/Lebesgue",
        "priority": "blocking",
        "question": "Does the top additive remain favorable under higher-fidelity electrochemical and interfacial checks?",
        "inputs": {
            "candidate_id": top_candidate["candidate_id"],
            "name": top_candidate["name"],
            "formula": top_candidate["formula"],
            "constraints": task.get("constraints", {}),
        },
        "suggested_checks": [
            "oxidation and reduction stability window",
            "solvation and Li+ coordination impact",
            "SEI-forming decomposition pathway plausibility",
            "gas-generation or impedance-risk screen",
        ],
        "acceptance_criteria": [
            "No hard violation of task constraints after high-fidelity computation.",
            "Top-ranked candidate keeps a defensible advantage over alternatives.",
            "Failure modes are written back as structured validation evidence.",
        ],
    }


def _wet_lab_validation_item(task: dict[str, Any], top_candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": "wet_lab_validation",
        "target_system": "Uni-Lab-OS",
        "priority": "blocking_before_deployment",
        "question": "Can the recommendation survive a controlled electrolyte formulation and cell-testing loop?",
        "inputs": {
            "candidate_id": top_candidate["candidate_id"],
            "name": top_candidate["name"],
            "constraints": task.get("constraints", {}),
        },
        "suggested_checks": [
            "protocol completeness and safety pre-check",
            "baseline electrolyte comparison",
            "formation-cycle Coulombic efficiency",
            "impedance growth after cycling",
            "gas or swelling observation when relevant",
        ],
        "acceptance_criteria": [
            "Protocol, reagent, and instrument metadata are captured.",
            "Raw measurements are linked back to the trace as artifacts.",
            "The result can update the post-training bundle as positive or negative feedback.",
        ],
    }


def _expert_boundary_review_item(task: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": "expert_boundary_review",
        "target_system": "domain_expert",
        "priority": "required_for_claim_promotion",
        "question": "Which claims can be promoted, which must stay provisional, and which require new evidence?",
        "inputs": {
            "goal": task["goal"],
            "claim_ids": [claim["claim_id"] for claim in report.get("claims", [])],
            "constraints": task.get("constraints", {}),
        },
        "suggested_checks": [
            "claim scope and applicability",
            "missing operating conditions",
            "candidate-specific risks not represented in the proxy screen",
            "whether the next action should be simulation, experiment, or literature expansion",
        ],
        "acceptance_criteria": [
            "Each promoted claim has an explicit evidence or artifact key.",
            "Each rejected claim has a failure tag.",
            "Each unresolved claim has a next validation route.",
        ],
    }


def _feedback_ingestion_item(trace: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": "feedback_ingestion",
        "target_system": "SciTrace-RL trace store",
        "priority": "after_external_validation",
        "question": "How should external simulation, lab, or expert results be converted back into learning signal?",
        "inputs": {
            "trace_id": trace["trace_id"],
            "reward": trace["reward"],
        },
        "suggested_checks": [
            "attach external result artifacts with hashes",
            "recompute validation gates with external evidence",
            "update SFT/DPO/process-reward records",
            "record whether the escalation confirmed, weakened, or overturned the recommendation",
        ],
        "acceptance_criteria": [
            "External results become trace-linked artifacts, not free-text notes.",
            "Reward and credit assignment are updated from observed outcomes.",
            "The next run can replay the changed evidence state.",
        ],
    }
