from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any

from .chemistry import formula_stats
from .schema import ToolCall
from .utils import now_iso, read_json, sha256_json


@dataclass
class ToolExecution:
    call: ToolCall
    result: dict[str, Any]


class BaseTool:
    name = "base_tool"

    def execute(self, **kwargs: Any) -> ToolExecution:
        started_at = now_iso()
        started = perf_counter()
        try:
            result = self._run(**kwargs)
            status = "success"
        except Exception as exc:  # pragma: no cover - surfaced in trace for debugging.
            result = {"error": str(exc)}
            status = "error"
        ended_at = now_iso()
        duration_ms = int((perf_counter() - started) * 1000)
        call = ToolCall(
            name=self.name,
            inputs=kwargs,
            outputs=result,
            status=status,
            started_at=started_at,
            ended_at=ended_at,
            duration_ms=duration_ms,
        ).finalize()
        return ToolExecution(call=call, result=result)

    def _run(self, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError


class LiteratureSearchTool(BaseTool):
    name = "literature_search"

    def __init__(self, corpus_path: Path) -> None:
        self.corpus_path = corpus_path
        self.corpus = read_json(corpus_path)

    def _run(self, query: str, top_k: int = 5) -> dict[str, Any]:
        query_terms = {term.lower() for term in query.replace("-", " ").split() if len(term) > 2}
        scored: list[tuple[int, dict[str, Any]]] = []
        for item in self.corpus:
            haystack = " ".join(
                [
                    item["title"],
                    item["summary"],
                    " ".join(item.get("keywords", [])),
                ]
            ).lower()
            score = sum(1 for term in query_terms if term in haystack)
            if score:
                scored.append((score, item))
        scored.sort(key=lambda pair: (-pair[0], pair[1]["source_id"]))
        selected = [item for _, item in scored[:top_k]]
        return {
            "query": query,
            "source_ids": [item["source_id"] for item in selected],
            "sources": selected,
            "coverage": {
                "matched_terms": sorted(query_terms),
                "num_sources": len(selected),
                "corpus_sha256": sha256_json(self.corpus),
            },
        }


class MoleculeScreeningTool(BaseTool):
    name = "molecule_screening"

    def _run(self, candidates: list[dict[str, Any]], constraints: dict[str, Any]) -> dict[str, Any]:
        scored_candidates = []
        for candidate in candidates:
            stats = formula_stats(candidate["formula"])
            source_support = len(candidate.get("evidence_source_ids", []))
            hetero_bonus = min(stats.hetero_atom_count, 7) * 0.04
            fluoro_bonus = 0.12 if "F" in stats.atoms else 0.0
            sulfur_bonus = 0.05 if "S" in stats.atoms else 0.0
            mw_penalty = 0.0
            if stats.molecular_weight < constraints["molecular_weight"]["min"]:
                mw_penalty += 0.18
            if stats.molecular_weight > constraints["molecular_weight"]["max"]:
                mw_penalty += 0.18
            hazard_penalty = 0.1 * len(candidate.get("risk_flags", []))
            score = 0.45 + source_support * 0.08 + hetero_bonus + fluoro_bonus + sulfur_bonus - mw_penalty - hazard_penalty
            scored_candidates.append(
                {
                    **candidate,
                    "computed": {
                        "atoms": stats.atoms,
                        "molecular_weight": stats.molecular_weight,
                        "hetero_atom_count": stats.hetero_atom_count,
                    },
                    "screening_score": round(max(0.0, min(score, 1.0)), 3),
                    "score_rationale": [
                        "literature support",
                        "hetero atoms can participate in interphase chemistry",
                        "fluorine/sulfur bonuses are proxy features for SEI-forming additives",
                        "penalize candidates outside molecular-weight or safety constraints",
                    ],
                }
            )
        scored_candidates.sort(key=lambda item: (-item["screening_score"], item["candidate_id"]))
        return {
            "ranked_candidates": scored_candidates,
            "top_candidate": scored_candidates[0] if scored_candidates else None,
            "constraints": constraints,
        }


class ReportWriterTool(BaseTool):
    name = "report_writer"

    def _run(
        self,
        task: dict[str, Any],
        sources: list[dict[str, Any]],
        screening: dict[str, Any],
    ) -> dict[str, Any]:
        top = screening["top_candidate"]
        source_by_id = {source["source_id"]: source for source in sources}
        source_lines = []
        for source_id in top["evidence_source_ids"]:
            source = source_by_id.get(source_id)
            if source:
                source_lines.append(f"- [{source_id}] {source['title']} ({source['url']})")

        candidates_table = [
            "| Rank | Candidate | Formula | Score | Key evidence |",
            "|---:|---|---|---:|---|",
        ]
        for rank, candidate in enumerate(screening["ranked_candidates"], start=1):
            candidates_table.append(
                "| {rank} | {name} | {formula} | {score:.3f} | {evidence} |".format(
                    rank=rank,
                    name=candidate["name"],
                    formula=candidate["formula"],
                    score=candidate["screening_score"],
                    evidence=", ".join(candidate["evidence_source_ids"]),
                )
            )

        report = f"""# Agent-Grounded Candidate Report

## Task
{task["goal"]}

## Recommendation
Prioritize **{top["name"]}** (`{top["candidate_id"]}`) for the next dry-lab or wet-lab validation loop. The recommendation is provisional: it is based on a lightweight, reproducible proxy screen, not on high-fidelity quantum chemistry or real battery cycling data.

## Evidence Chain
{chr(10).join(source_lines)}

## Candidate Ranking
{chr(10).join(candidates_table)}

## Validation Hooks
- Re-run `molecule_screening` with the same candidates and constraints; the output hash should match.
- Check every cited source id in the report against the retrieval results.
- Promote the top candidate only if the molecular-weight constraint, evidence coverage, and claim-evidence alignment gates pass.

## Next Step
Replace the proxy screening tool with a Bohrium/Lebesgue job adapter for molecular simulation, then feed validated results back into the trace-to-reward dataset.
"""
        claims = [
            {
                "claim_id": "claim_top_candidate",
                "text": f"{top['name']} is the top-ranked candidate in this run.",
                "evidence_source_ids": top["evidence_source_ids"],
                "artifact_keys": ["ranked_candidates", "top_candidate"],
            },
            {
                "claim_id": "claim_reproducibility",
                "text": "The recommendation must be treated as provisional until higher-fidelity validation is executed.",
                "evidence_source_ids": ["agentic_science_infra"],
                "artifact_keys": ["validation_policy"],
            },
        ]
        return {
            "markdown": report,
            "claims": claims,
            "citation_ids": sorted({source_id for candidate in screening["ranked_candidates"] for source_id in candidate["evidence_source_ids"]}),
        }
