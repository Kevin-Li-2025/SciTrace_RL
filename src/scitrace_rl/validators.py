from __future__ import annotations

from typing import Any

from .ai_judge import run_ai_claim_review
from .schema import ValidationResult
from .tools import MoleculeScreeningTool
from .utils import sha256_json


EXPECTED_TOOL_SEQUENCE = ["literature_search", "molecule_screening", "report_writer"]
STOPWORDS = {
    "about",
    "additional",
    "after",
    "again",
    "against",
    "based",
    "battery",
    "because",
    "before",
    "candidate",
    "candidates",
    "claim",
    "cycle",
    "data",
    "evidence",
    "executed",
    "fidelity",
    "from",
    "higher",
    "high",
    "into",
    "lithium",
    "must",
    "next",
    "percent",
    "provisional",
    "ranked",
    "recommendation",
    "recommended",
    "requires",
    "should",
    "single",
    "source",
    "this",
    "treated",
    "trace",
    "until",
    "validation",
    "without",
}
ARTIFACT_SUPPORTED_TERMS = {
    "ranked_candidates": {"top", "rank", "ranked", "score", "screening", "run"},
    "top_candidate": {"top", "rank", "ranked", "candidate", "screening", "run"},
    "validation_policy": {"provisional", "higher", "fidelity", "validation", "executed", "deployment"},
}
UNSUPPORTED_CLAIM_PATTERNS = {
    "quantified_outcome": ["50 percent", "at least", "all lithium-ion batteries"],
    "cross_domain_transfer": ["sodium-ion", "equally well"],
    "invented_computation": ["dft", "ev", "computed"],
    "wrong_mechanism": ["sulfur-rich"],
    "deployment_overclaim": ["ready for deployment", "universally safe", "without additional"],
}


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


def validate_trajectory(tool_calls: list[Any], artifacts: list[Any]) -> ValidationResult:
    calls = [_asdict(item) for item in tool_calls]
    artifact_items = [_asdict(item) for item in artifacts]
    artifact_ids = {item.get("artifact_id") for item in artifact_items}
    sequence = [call.get("name") for call in calls]
    issues: list[str] = []
    if sequence != EXPECTED_TOOL_SEQUENCE:
        issues.append("unexpected_tool_sequence")
    if len({call.get("call_id") for call in calls}) != len(calls):
        issues.append("duplicate_call_ids")
    for call in calls:
        if call.get("status") != "success":
            issues.append(f"{call.get('name')}:non_success_status")
        if int(call.get("duration_ms", -1)) < 0:
            issues.append(f"{call.get('name')}:negative_duration")
        if not call.get("output_hash"):
            issues.append(f"{call.get('name')}:missing_output_hash")
        linked = call.get("artifacts", [])
        if not linked:
            issues.append(f"{call.get('name')}:no_linked_artifact")
        for artifact_id in linked:
            if artifact_id not in artifact_ids:
                issues.append(f"{call.get('name')}:missing_artifact:{artifact_id}")
    required_outputs = {
        "literature_search": {"sources", "source_ids", "coverage"},
        "molecule_screening": {"ranked_candidates", "top_candidate", "constraints"},
        "report_writer": {"markdown", "claims", "citation_ids"},
    }
    for call in calls:
        missing = sorted(required_outputs.get(call.get("name"), set()) - set(call.get("outputs", {})))
        if missing:
            issues.append(f"{call.get('name')}:missing_outputs:{','.join(missing)}")
    score = max(0.0, 1.0 - len(issues) / 8)
    return ValidationResult(
        name="trajectory_quality",
        status="pass" if not issues else "fail",
        score=round(score, 3),
        message="Tool sequence, outputs, durations, and artifact links are valid." if not issues else "Tool trajectory has structural issues.",
        evidence={
            "expected_sequence": EXPECTED_TOOL_SEQUENCE,
            "actual_sequence": sequence,
            "issues": issues,
            "artifact_ids": sorted(item for item in artifact_ids if item),
        },
    ).finalize()


def validate_citation_support(report: dict[str, Any], retrieved_sources: list[dict[str, Any]]) -> ValidationResult:
    source_by_id = {source["source_id"]: source for source in retrieved_sources}
    unsupported_claims: list[dict[str, Any]] = []
    checked_claims = []
    for claim in report.get("claims", []):
        claim_id = claim.get("claim_id", "<unknown>")
        claim_text = claim.get("text", "")
        evidence_ids = claim.get("evidence_source_ids", [])
        artifact_keys = claim.get("artifact_keys", [])
        missing_sources = [source_id for source_id in evidence_ids if source_id not in source_by_id]
        pattern_hits = _unsupported_pattern_hits(claim_text)
        unsupported_terms = _unsupported_terms(claim_text, evidence_ids, artifact_keys, source_by_id)
        checked_claims.append(claim_id)
        if missing_sources or pattern_hits or unsupported_terms:
            unsupported_claims.append(
                {
                    "claim_id": claim_id,
                    "missing_sources": missing_sources,
                    "unsupported_patterns": pattern_hits,
                    "unsupported_terms": unsupported_terms,
                }
            )
    total_claims = max(len(report.get("claims", [])), 1)
    score = 1.0 - len(unsupported_claims) / total_claims
    return ValidationResult(
        name="citation_support_precision",
        status="pass" if not unsupported_claims else "fail",
        score=round(max(0.0, score), 3),
        message="Claim citations are supported by retrieved evidence and linked artifacts." if not unsupported_claims else "Some claim citations do not support the claim text.",
        evidence={
            "checked_claim_ids": checked_claims,
            "unsupported_claims": unsupported_claims,
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
        "citation_support_precision": 0.2,
        "artifact_replay": 0.3,
        "constraint_satisfaction": 0.2,
        "claim_evidence_alignment": 0.2,
        "claim_metadata_completeness": 0.1,
        "trajectory_quality": 0.2,
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


def _asdict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return value.__dict__


def _source_text(source: dict[str, Any]) -> str:
    return " ".join(
        [
            source.get("title", ""),
            source.get("summary", ""),
            " ".join(source.get("keywords", [])),
        ]
    ).lower()


def _tokens(text: str) -> set[str]:
    clean = "".join(ch.lower() if ch.isalnum() else " " for ch in text)
    return {token for token in clean.split() if len(token) > 3 and token not in STOPWORDS}


def _unsupported_pattern_hits(claim_text: str) -> list[str]:
    lower = claim_text.lower()
    hits = []
    for pattern_name, phrases in UNSUPPORTED_CLAIM_PATTERNS.items():
        if any(phrase in lower for phrase in phrases):
            hits.append(pattern_name)
    return hits


def _unsupported_terms(
    claim_text: str,
    evidence_ids: list[str],
    artifact_keys: list[str],
    source_by_id: dict[str, dict[str, Any]],
) -> list[str]:
    source_text = " ".join(_source_text(source_by_id[source_id]) for source_id in evidence_ids if source_id in source_by_id)
    source_tokens = _tokens(source_text)
    artifact_tokens: set[str] = set()
    for artifact_key in artifact_keys:
        artifact_tokens.update(ARTIFACT_SUPPORTED_TERMS.get(artifact_key, set()))
    claim_tokens = _tokens(claim_text)
    unsupported = sorted(token for token in claim_tokens if token not in source_tokens and token not in artifact_tokens)
    return unsupported[:8]
