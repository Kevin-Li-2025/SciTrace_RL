from __future__ import annotations

from typing import Any

from .utils import compact_id, sha256_json


SCHEMA_VERSION = "0.2"


TOOL_GATE_MAP = {
    "literature_search": ["citation_integrity"],
    "molecule_screening": ["artifact_replay", "constraint_satisfaction"],
    "report_writer": ["claim_evidence_alignment", "claim_metadata_completeness", "ai_claim_review"],
}


def build_post_training_bundle(
    trace: dict[str, Any],
    task: dict[str, Any],
    report: dict[str, Any],
    screening: dict[str, Any],
) -> dict[str, Any]:
    """Turn a validated scientific-agent run into concrete post-training records."""
    validations = {item["name"]: item for item in trace["validations"]}
    bundle = {
        "schema_version": SCHEMA_VERSION,
        "trace_id": trace["trace_id"],
        "task_id": trace["task_id"],
        "reward": trace["reward"],
        "formats": [
            "sft_chat_record",
            "dpo_preference_pair",
            "process_reward_steps",
            "tool_router_records",
            "credit_assignment",
        ],
        "sft_chat_record": _build_sft_record(trace, task, report),
        "dpo_preference_pair": _build_preference_pair(trace, task, report, screening),
        "process_reward_steps": _build_process_rewards(trace, validations),
        "tool_router_records": _build_tool_router_records(trace, task, validations),
        "credit_assignment": _build_credit_assignment(trace, validations),
    }
    bundle["bundle_id"] = compact_id("ptbundle", bundle)
    return bundle


def _build_sft_record(trace: dict[str, Any], task: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "trace_id": trace["trace_id"],
        "task_id": trace["task_id"],
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a scientific workflow agent. Use tools, cite retrieved evidence, "
                    "state validation boundaries, and avoid deployment claims without simulation or experiment."
                ),
            },
            {
                "role": "user",
                "content": task["goal"],
            },
            {
                "role": "assistant",
                "content": report["markdown"],
            },
        ],
        "labels": {
            "reward": trace["reward"]["reward"],
            "all_required_gates_passed": _all_required_gates_passed(trace),
            "source_trace": trace["trace_id"],
        },
    }
    payload["record_id"] = compact_id("sft", payload)
    return payload


def _build_preference_pair(
    trace: dict[str, Any],
    task: dict[str, Any],
    report: dict[str, Any],
    screening: dict[str, Any],
) -> dict[str, Any]:
    top_candidate = screening["top_candidate"]
    rejected = (
        f"Deploy {top_candidate['name']} immediately as the final electrolyte additive. "
        "The screening score alone is sufficient and no further simulation, wet-lab validation, "
        "or expert review is needed."
    )
    payload = {
        "prompt": task["goal"],
        "chosen": report["markdown"],
        "rejected": rejected,
        "preference_reason": (
            "The chosen answer is citation-grounded, trace-backed, and keeps the recommendation provisional. "
            "The rejected answer overclaims beyond the evidence and skips required escalation."
        ),
        "source_trace": trace["trace_id"],
        "reward_margin": trace["reward"]["reward"],
        "failure_tags_for_rejected": ["overclaim", "missing_escalation", "unsupported_deployment"],
    }
    payload["pair_id"] = compact_id("dpo", payload)
    return payload


def _build_process_rewards(trace: dict[str, Any], validations: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for step_index, call in enumerate(trace["tools"]):
        gate_names = TOOL_GATE_MAP.get(call["name"], [])
        gate_scores = [
            validations[name]["score"]
            for name in gate_names
            if name in validations and validations[name]["status"] != "skip"
        ]
        step_reward = sum(gate_scores) / len(gate_scores) if gate_scores else (1.0 if call["status"] == "success" else 0.0)
        record = {
            "step_index": step_index,
            "tool_name": call["name"],
            "call_id": call["call_id"],
            "status": call["status"],
            "input_hash": sha256_json(call["inputs"]),
            "output_hash": call["output_hash"],
            "linked_artifacts": call.get("artifacts", []),
            "linked_validation_gates": gate_names,
            "step_reward": round(step_reward, 4),
        }
        record["record_id"] = compact_id("prm", record)
        records.append(record)
    return records


def _build_tool_router_records(
    trace: dict[str, Any],
    task: dict[str, Any],
    validations: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for call in trace["tools"]:
        route_label = _route_label(call["name"])
        gate_names = TOOL_GATE_MAP.get(call["name"], [])
        required_gates = [validations[name] for name in gate_names if name in validations]
        successful_route = call["status"] == "success" and all(item["status"] in {"pass", "skip"} for item in required_gates)
        record = {
            "task_id": trace["task_id"],
            "domain": trace["domain"],
            "route_label": route_label,
            "tool_name": call["name"],
            "decision_context": {
                "goal": task["goal"],
                "constraints": task.get("constraints", {}),
                "step_inputs_hash": sha256_json(call["inputs"]),
            },
            "accepted": successful_route,
            "reward": 1.0 if successful_route else 0.0,
            "source_trace": trace["trace_id"],
        }
        record["record_id"] = compact_id("router", record)
        records.append(record)
    return records


def _build_credit_assignment(
    trace: dict[str, Any],
    validations: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for gate_name, validation in validations.items():
        record = {
            "validation_gate": gate_name,
            "status": validation["status"],
            "score": validation["score"],
            "target_tools": _target_tools_for_gate(gate_name),
            "failure_type": _failure_type(validation),
            "source_trace": trace["trace_id"],
        }
        record["record_id"] = compact_id("credit", record)
        records.append(record)
    return records


def _all_required_gates_passed(trace: dict[str, Any]) -> bool:
    for validation in trace["validations"]:
        if validation["status"] == "fail":
            return False
    return True


def _route_label(tool_name: str) -> str:
    if tool_name == "literature_search":
        return "retrieve_evidence"
    if tool_name == "molecule_screening":
        return "screen_candidates"
    if tool_name == "report_writer":
        return "write_grounded_report"
    return "unknown"


def _target_tools_for_gate(gate_name: str) -> list[str]:
    return [tool for tool, gates in TOOL_GATE_MAP.items() if gate_name in gates]


def _failure_type(validation: dict[str, Any]) -> str:
    if validation["status"] == "pass":
        return "none"
    if validation["status"] == "skip":
        return "not_applicable_or_not_enabled"
    evidence = validation.get("evidence", {})
    if "unsupported_claim_ids" in evidence:
        return "unsupported_claim"
    if "fabricated_citations" in evidence:
        return "fabricated_citation"
    return validation["name"]
