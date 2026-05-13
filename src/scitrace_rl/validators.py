from __future__ import annotations

from typing import Any

from .ai_judge import run_ai_claim_review
from .schema import ValidationResult
from .tools import MoleculeScreeningTool
from .utils import sha256_json


def validate_citations(report: dict[str, Any], retrieved_sources: list[dict[str, Any]]) -> ValidationResult:
    available = {source["source_id"] for source in retrieved_sources}
    cited = set(report["citation_ids"])
    missing = sorted(cited - available)
    score = 1.0 if not missing else max(0.0, 1 - len(missing) / max(len(cited), 1))
    return ValidationResult(
        name="citation_integrity",
        status="pass" if not missing else "fail",
        score=round(score, 3),
        message="All report citations resolve to retrieved evidence." if not missing else "Some citations are not in retrieved evidence.",
        evidence={"cited": sorted(cited), "available": sorted(available), "missing": missing},
    ).finalize()


def validate_replay(candidates: list[dict[str, Any]], constraints: dict[str, Any], original_screening: dict[str, Any]) -> ValidationResult:
    replay = MoleculeScreeningTool().execute(candidates=candidates, constraints=constraints).result
    original_hash = sha256_json(original_screening)
    replay_hash = sha256_json(replay)
    matched = original_hash == replay_hash
    return ValidationResult(
        name="artifact_replay",
        status="pass" if matched else "fail",
        score=1.0 if matched else 0.0,
        message="Screening output is deterministic and replayable." if matched else "Replay produced a different screening output.",
        evidence={"original_hash": original_hash, "replay_hash": replay_hash},
    ).finalize()


def validate_constraints(screening: dict[str, Any]) -> ValidationResult:
    constraints = screening["constraints"]
    top = screening["top_candidate"]
    mw = top["computed"]["molecular_weight"]
    within_mw = constraints["molecular_weight"]["min"] <= mw <= constraints["molecular_weight"]["max"]
    above_score = top["screening_score"] >= constraints["minimum_screening_score"]
    passed = within_mw and above_score
    score = (0.5 if within_mw else 0.0) + (0.5 if above_score else 0.0)
    return ValidationResult(
        name="constraint_satisfaction",
        status="pass" if passed else "warn",
        score=round(score, 3),
        message="Top candidate satisfies lightweight design constraints." if passed else "Top candidate needs manual review against design constraints.",
        evidence={
            "candidate_id": top["candidate_id"],
            "molecular_weight": mw,
            "screening_score": top["screening_score"],
            "constraints": constraints,
        },
    ).finalize()


def validate_claim_alignment(report: dict[str, Any], screening: dict[str, Any]) -> ValidationResult:
    top = screening["top_candidate"]
    top_claims = [claim for claim in report["claims"] if claim["claim_id"] == "claim_top_candidate"]
    top_markers = {top["candidate_id"].lower(), top["name"].lower()}
    claim_texts = " ".join(claim.get("text", "") for claim in top_claims).lower()
    markdown = report["markdown"].lower()
    claim_mentions_top = any(marker in claim_texts for marker in top_markers)
    report_mentions_top = any(marker in markdown for marker in top_markers)
    aligned = bool(top_claims and claim_mentions_top and report_mentions_top)
    return ValidationResult(
        name="claim_evidence_alignment",
        status="pass" if aligned else "fail",
        score=1.0 if aligned else 0.0,
        message="The top-candidate claim is grounded in the ranked artifact." if aligned else "The top-candidate claim is not grounded in the ranked artifact.",
        evidence={
            "top_candidate": top["candidate_id"],
            "top_candidate_name": top["name"],
            "claim_mentions_top": claim_mentions_top,
            "report_mentions_top": report_mentions_top,
            "matching_claims": top_claims,
        },
    ).finalize()


def validate_claim_metadata(report: dict[str, Any]) -> ValidationResult:
    missing_source_ids = [
        claim.get("claim_id", "<unknown>")
        for claim in report.get("claims", [])
        if not claim.get("evidence_source_ids")
    ]
    missing_artifact_keys = [
        claim.get("claim_id", "<unknown>")
        for claim in report.get("claims", [])
        if not claim.get("artifact_keys")
    ]
    passed = not missing_source_ids and not missing_artifact_keys
    total_claims = max(len(report.get("claims", [])), 1)
    issue_count = len(set(missing_source_ids + missing_artifact_keys))
    score = 1.0 - issue_count / total_claims
    return ValidationResult(
        name="claim_metadata_completeness",
        status="pass" if passed else "fail",
        score=round(max(0.0, score), 3),
        message="All claims include source ids and artifact keys." if passed else "Some claims are missing source ids or artifact keys.",
        evidence={
            "missing_source_ids": missing_source_ids,
            "missing_artifact_keys": missing_artifact_keys,
            "claim_count": total_claims,
        },
    ).finalize()


def validate_ai_claim_review(
    report: dict[str, Any],
    retrieved_sources: list[dict[str, Any]],
    artifacts: dict[str, Any] | None = None,
) -> ValidationResult:
    review = run_ai_claim_review(report, retrieved_sources, artifacts)
    status = str(review.get("status", "warn")).lower()
    if status not in {"pass", "warn", "fail", "skip"}:
        status = "warn"
    score = float(review.get("score", 0.5))
    return ValidationResult(
        name="ai_claim_review",
        status=status,
        score=round(max(0.0, min(score, 1.0)), 3),
        message=str(review.get("rationale", "AI claim review completed.")),
        evidence={
            "configured": bool(review.get("configured", False)),
            "provider": review.get("provider"),
            "model": review.get("model"),
            "unsupported_claim_ids": review.get("unsupported_claim_ids", []),
            "reviewed_claim_ids": review.get("reviewed_claim_ids", []),
            "raw_response_hash": review.get("raw_response_hash"),
        },
    ).finalize()


def aggregate_reward(validations: list[ValidationResult], metrics: dict[str, Any]) -> dict[str, Any]:
    weights = {
        "citation_integrity": 0.25,
        "artifact_replay": 0.3,
        "constraint_satisfaction": 0.2,
        "claim_evidence_alignment": 0.2,
        "claim_metadata_completeness": 0.1,
        "ai_claim_review": 0.2,
    }
    weighted = 0.0
    used_weight = 0.0
    for validation in validations:
        if validation.status == "skip":
            continue
        weight = weights.get(validation.name, 0.0)
        weighted += weight * validation.score
        used_weight += weight
    quality = weighted / used_weight if used_weight else 0.0
    cost_penalty = min(float(metrics.get("total_tool_calls", 0)) * 0.01, 0.08)
    reward = max(0.0, quality - cost_penalty)
    return {
        "reward": round(reward, 3),
        "quality_score": round(quality, 3),
        "cost_penalty": round(cost_penalty, 3),
        "interpretation": "Reward combines validation quality with a small execution-cost penalty.",
        "training_use": "Can supervise planner/tool-router choices or serve as an offline RL preference label.",
    }
