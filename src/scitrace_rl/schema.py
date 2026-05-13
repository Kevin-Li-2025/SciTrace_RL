from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .utils import compact_id, now_iso, sha256_json


@dataclass
class Artifact:
    kind: str
    uri: str
    summary: str
    metadata: dict[str, Any] = field(default_factory=dict)
    artifact_id: str = ""
    sha256: str = ""

    def finalize(self) -> "Artifact":
        payload = {
            "kind": self.kind,
            "uri": self.uri,
            "summary": self.summary,
            "metadata": self.metadata,
        }
        self.artifact_id = self.artifact_id or compact_id("artifact", payload)
        self.sha256 = self.sha256 or sha256_json(payload)
        return self


@dataclass
class ToolCall:
    name: str
    inputs: dict[str, Any]
    outputs: dict[str, Any]
    status: str
    started_at: str
    ended_at: str
    duration_ms: int
    artifacts: list[str] = field(default_factory=list)
    call_id: str = ""
    output_hash: str = ""

    def finalize(self) -> "ToolCall":
        payload = {
            "name": self.name,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "status": self.status,
            "artifacts": self.artifacts,
        }
        self.call_id = self.call_id or compact_id("call", payload)
        self.output_hash = self.output_hash or sha256_json(self.outputs)
        return self


@dataclass
class ValidationResult:
    name: str
    status: str
    score: float
    message: str
    evidence: dict[str, Any] = field(default_factory=dict)
    validation_id: str = ""

    def finalize(self) -> "ValidationResult":
        payload = {
            "name": self.name,
            "status": self.status,
            "score": self.score,
            "message": self.message,
            "evidence": self.evidence,
        }
        self.validation_id = self.validation_id or compact_id("validation", payload)
        return self


@dataclass
class Trace:
    task_id: str
    goal: str
    domain: str
    created_at: str = field(default_factory=now_iso)
    trace_id: str = ""
    tools: list[ToolCall] = field(default_factory=list)
    artifacts: list[Artifact] = field(default_factory=list)
    validations: list[ValidationResult] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    reward: dict[str, Any] = field(default_factory=dict)

    def add_artifact(self, artifact: Artifact) -> Artifact:
        artifact.finalize()
        self.artifacts.append(artifact)
        return artifact

    def add_tool_call(self, call: ToolCall) -> ToolCall:
        call.finalize()
        self.tools.append(call)
        return call

    def add_validation(self, validation: ValidationResult) -> ValidationResult:
        validation.finalize()
        self.validations.append(validation)
        return validation

    def finalize(self) -> "Trace":
        payload = {
            "task_id": self.task_id,
            "goal": self.goal,
            "domain": self.domain,
            "tools": [asdict(tool) for tool in self.tools],
            "artifacts": [asdict(artifact) for artifact in self.artifacts],
            "validations": [asdict(validation) for validation in self.validations],
            "metrics": self.metrics,
            "reward": self.reward,
        }
        self.trace_id = self.trace_id or compact_id("trace", payload)
        return self

    def to_dict(self) -> dict[str, Any]:
        self.finalize()
        return asdict(self)

