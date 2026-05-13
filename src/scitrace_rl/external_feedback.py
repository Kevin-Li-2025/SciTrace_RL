from __future__ import annotations

from typing import Any

from .utils import compact_id, now_iso, sha256_json


SCHEMA_VERSION = "0.1"


def build_external_result_fixture(screening: dict[str, Any]) -> dict[str, Any]:
    """Create a deterministic external-result fixture that exercises feedback ingestion."""
    top = screening["top_candidate"]
    result = {
        "schema_version": SCHEMA_VERSION,
        "result_id": "",
        "created_at": now_iso(),
        "simulation_fixture": True,
        "target_system": "Bohrium/Lebesgue",
        "candidate_id": top["candidate_id"],
        "candidate_name": top["name"],
        "outcome": "contradicts_recommendation",
        "observations": [
            {
                "name": "impedance_growth_proxy",
                "value": "high",
                "interpretation": "External validation suggests the proxy screen overestimated deployment readiness.",
            },
            {
                "name": "requires_wet_lab_followup",
                "value": True,
                "interpretation": "The candidate should remain provisional until wet-lab feedback is available.",
            },
        ],
    }
    result["result_id"] = compact_id("external_result", result)
    result["sha256"] = sha256_json(result)
    return result


def ingest_external_result(
    trace: dict[str, Any],
    post_training_bundle: dict[str, Any],
    escalation_packet: dict[str, Any],
    external_result: dict[str, Any],
) -> dict[str, Any]:
    """Convert an external validation result into reward and training-data updates."""
    old_reward = float(trace["reward"]["reward"])
    contradicted = external_result["outcome"] == "contradicts_recommendation"
    reward_delta = -0.35 if contradicted else 0.1
    updated_reward = round(max(0.0, min(1.0, old_reward + reward_delta)), 3)
    closed_items = [
        item["item_id"]
        for item in escalation_packet["escalation_items"]
        if item["target_system"] == external_result["target_system"]
    ]
    update = {
        "schema_version": SCHEMA_VERSION,
        "trace_id": trace["trace_id"],
        "external_result_id": external_result["result_id"],
        "external_result_hash": external_result["sha256"],
        "simulation_fixture": bool(external_result.get("simulation_fixture", False)),
        "old_reward": old_reward,
        "reward_delta": reward_delta,
        "updated_reward": updated_reward,
        "updated_recommendation_status": "requires_revision" if contradicted else "externally_supported",
        "closed_escalation_item_ids": closed_items,
        "new_failure_tags": ["external_contradiction", "proxy_screen_overconfidence"] if contradicted else [],
        "post_training_updates": {
            "source_bundle_id": post_training_bundle["bundle_id"],
            "add_negative_preference": contradicted,
            "update_process_reward_steps": [
                {
                    "tool_name": "molecule_screening",
                    "reason": "External validation contradicted the proxy ranking confidence.",
                    "new_step_reward": 0.45 if contradicted else 1.0,
                },
                {
                    "tool_name": "report_writer",
                    "reason": "Report must keep recommendation provisional and mention external contradiction.",
                    "new_step_reward": 0.65 if contradicted else 1.0,
                },
            ],
        },
        "required_next_actions": [
            "Attach external result as a hashed trace artifact.",
            "Re-run claim support and escalation policy with external evidence.",
            "Create a revised preference pair where overconfident recommendation is rejected.",
        ],
    }
    update["ingestion_id"] = compact_id("external_ingestion", update)
    return update


def validate_external_result_ingestion(ingestion: dict[str, Any]) -> dict[str, Any]:
    issues = []
    if not ingestion.get("trace_id"):
        issues.append("missing_trace_id")
    if not ingestion.get("external_result_hash"):
        issues.append("missing_external_result_hash")
    if ingestion.get("updated_reward", 1.0) >= ingestion.get("old_reward", 0.0) and ingestion.get("reward_delta", 0) < 0:
        issues.append("negative_feedback_did_not_lower_reward")
    if not ingestion.get("closed_escalation_item_ids"):
        issues.append("no_escalation_item_closed")
    if not ingestion.get("post_training_updates", {}).get("update_process_reward_steps"):
        issues.append("missing_process_reward_update")
    return {
        "status": "pass" if not issues else "fail",
        "score": 1.0 if not issues else max(0.0, 1.0 - len(issues) * 0.25),
        "issues": issues,
    }
