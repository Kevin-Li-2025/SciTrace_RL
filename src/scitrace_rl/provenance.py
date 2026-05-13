from __future__ import annotations

import hashlib
import json
from typing import Any


SCHEMA_VERSION = "0.2"
RO_CRATE_CONTEXT = "https://w3id.org/ro/crate/1.1/context"
WORKFLOW_RUN_PROFILE = "https://w3id.org/ro/wfrun/process/0.5"
PROV_NAMESPACE = "http://www.w3.org/ns/prov#"


def build_provenance_bundle(trace: dict[str, Any]) -> dict[str, Any]:
    """Export a trace into interoperable provenance and observability views."""
    return {
        "schema_version": SCHEMA_VERSION,
        "trace_id": trace["trace_id"],
        "standards_alignment": [
            {
                "name": "W3C PROV",
                "purpose": "Represent tasks, tool executions, validation actions, and artifacts as entities, activities, and agents.",
                "url": "https://www.w3.org/TR/prov-overview/",
            },
            {
                "name": "Workflow Run RO-Crate",
                "purpose": "Package scientific workflow execution metadata and produced artifacts for FAIR reuse.",
                "url": "https://www.researchobject.org/workflow-run-crate/",
            },
            {
                "name": "OpenTelemetry GenAI semantic conventions",
                "purpose": "Map agent and tool steps to spans that production observability systems can ingest.",
                "url": "https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-agent-spans/",
            },
        ],
        "ro_crate": _build_ro_crate(trace),
        "prov": _build_prov(trace),
        "otel": _build_otel(trace),
    }


def _build_ro_crate(trace: dict[str, Any]) -> dict[str, Any]:
    graph: list[dict[str, Any]] = [
        {
            "@id": "ro-crate-metadata.json",
            "@type": "CreativeWork",
            "conformsTo": {"@id": RO_CRATE_CONTEXT},
            "about": {"@id": "./"},
        },
        {
            "@id": "./",
            "@type": "Dataset",
            "name": f"SciTrace-RL run {trace['trace_id']}",
            "description": trace["goal"],
            "conformsTo": [{"@id": WORKFLOW_RUN_PROFILE}],
            "hasPart": [{"@id": _artifact_id(item)} for item in trace["artifacts"]],
            "mainEntity": {"@id": _trace_id(trace)},
        },
        {
            "@id": _trace_id(trace),
            "@type": "Dataset",
            "identifier": trace["trace_id"],
            "name": "SciTrace-RL execution trace",
            "dateCreated": trace["created_at"],
            "about": {"@id": _task_id(trace)},
        },
        {
            "@id": _task_id(trace),
            "@type": "Thing",
            "identifier": trace["task_id"],
            "name": trace["goal"],
            "additionalType": trace["domain"],
        },
        {
            "@id": "#agent/scitrace-rl",
            "@type": "SoftwareApplication",
            "name": "SciTrace-RL",
            "softwareVersion": SCHEMA_VERSION,
        },
    ]

    for artifact in trace["artifacts"]:
        graph.append(
            {
                "@id": _artifact_id(artifact),
                "@type": "DigitalDocument",
                "identifier": artifact["artifact_id"],
                "name": artifact["kind"],
                "description": artifact["summary"],
                "contentUrl": artifact["uri"],
                "sha256": artifact["sha256"],
                "additionalType": artifact["kind"],
                "additionalProperty": _properties(artifact.get("metadata", {})),
            }
        )

    for call in trace["tools"]:
        tool_id = f"#tool/{call['name']}"
        graph.append({"@id": tool_id, "@type": "SoftwareApplication", "name": call["name"]})
        graph.append(
            {
                "@id": _tool_call_id(call),
                "@type": "CreateAction",
                "name": call["name"],
                "agent": {"@id": "#agent/scitrace-rl"},
                "instrument": {"@id": tool_id},
                "object": {"@id": _task_id(trace)},
                "result": [{"@id": f"#artifact/{artifact_id}"} for artifact_id in call.get("artifacts", [])],
                "startTime": call["started_at"],
                "endTime": call["ended_at"],
                "actionStatus": call["status"],
                "additionalProperty": _properties(
                    {
                        "duration_ms": call["duration_ms"],
                        "input_hash": _hash_json(call["inputs"]),
                        "output_hash": call["output_hash"],
                    }
                ),
            }
        )

    for validation in trace["validations"]:
        graph.append(
            {
                "@id": _validation_id(validation),
                "@type": "AssessAction",
                "name": validation["name"],
                "agent": {"@id": "#agent/scitrace-rl"},
                "object": {"@id": _trace_id(trace)},
                "actionStatus": validation["status"],
                "result": {
                    "@type": "PropertyValue",
                    "name": "score",
                    "value": validation["score"],
                },
                "description": validation["message"],
                "additionalProperty": _properties(validation.get("evidence", {})),
            }
        )

    return {"@context": RO_CRATE_CONTEXT, "@graph": graph}


def _build_prov(trace: dict[str, Any]) -> dict[str, Any]:
    entities: dict[str, dict[str, Any]] = {
        _trace_id(trace): {
            "prov:type": "scitrace:Trace",
            "scitrace:task_id": trace["task_id"],
            "scitrace:domain": trace["domain"],
        },
        _task_id(trace): {
            "prov:type": "scitrace:Task",
            "scitrace:goal": trace["goal"],
        },
    }
    activities: dict[str, dict[str, Any]] = {}
    agents = {
        "#agent/scitrace-rl": {
            "prov:type": "prov:SoftwareAgent",
            "prov:label": "SciTrace-RL",
        }
    }
    used: list[dict[str, str]] = []
    generated: list[dict[str, str]] = []
    associated: list[dict[str, str]] = []

    for artifact in trace["artifacts"]:
        artifact_key = _artifact_id(artifact)
        entities[artifact_key] = {
            "prov:type": "scitrace:Artifact",
            "scitrace:kind": artifact["kind"],
            "scitrace:uri": artifact["uri"],
            "scitrace:sha256": artifact["sha256"],
        }

    for call in trace["tools"]:
        activity_key = _tool_call_id(call)
        activities[activity_key] = {
            "prov:type": "scitrace:ToolCall",
            "prov:startedAtTime": call["started_at"],
            "prov:endedAtTime": call["ended_at"],
            "scitrace:tool": call["name"],
            "scitrace:status": call["status"],
            "scitrace:output_hash": call["output_hash"],
        }
        used.append({"prov:activity": activity_key, "prov:entity": _task_id(trace)})
        associated.append({"prov:activity": activity_key, "prov:agent": "#agent/scitrace-rl"})
        for artifact_id in call.get("artifacts", []):
            generated.append({"prov:entity": f"#artifact/{artifact_id}", "prov:activity": activity_key})

    for validation in trace["validations"]:
        activity_key = _validation_id(validation)
        activities[activity_key] = {
            "prov:type": "scitrace:ValidationGate",
            "scitrace:status": validation["status"],
            "scitrace:score": validation["score"],
            "scitrace:message": validation["message"],
        }
        used.append({"prov:activity": activity_key, "prov:entity": _trace_id(trace)})
        associated.append({"prov:activity": activity_key, "prov:agent": "#agent/scitrace-rl"})

    return {
        "prefix": {
            "prov": PROV_NAMESPACE,
            "scitrace": "https://example.org/scitrace#",
        },
        "entity": entities,
        "activity": activities,
        "agent": agents,
        "used": used,
        "wasGeneratedBy": generated,
        "wasAssociatedWith": associated,
    }


def _build_otel(trace: dict[str, Any]) -> dict[str, Any]:
    otel_trace_id = _trace_id_hex(trace["trace_id"])
    root_span_id = _span_id(trace["trace_id"])
    spans = [
        {
            "trace_id": otel_trace_id,
            "span_id": root_span_id,
            "parent_span_id": None,
            "name": "scitrace.workflow",
            "kind": "internal",
            "start_time": trace["created_at"],
            "end_time": _workflow_end_time(trace),
            "attributes": {
                "gen_ai.operation.name": "invoke_agent",
                "scitrace.trace_id": trace["trace_id"],
                "scitrace.task_id": trace["task_id"],
                "scitrace.domain": trace["domain"],
                "scitrace.reward": trace.get("reward", {}).get("reward"),
            },
        }
    ]

    for call in trace["tools"]:
        spans.append(
            {
                "trace_id": otel_trace_id,
                "span_id": _span_id(call["call_id"]),
                "parent_span_id": root_span_id,
                "name": f"execute_tool {call['name']}",
                "kind": "internal",
                "start_time": call["started_at"],
                "end_time": call["ended_at"],
                "attributes": {
                    "gen_ai.operation.name": "execute_tool",
                    "gen_ai.tool.name": call["name"],
                    "scitrace.call_id": call["call_id"],
                    "scitrace.status": call["status"],
                    "scitrace.duration_ms": call["duration_ms"],
                    "scitrace.input_hash": _hash_json(call["inputs"]),
                    "scitrace.output_hash": call["output_hash"],
                    "scitrace.artifact_ids": ",".join(call.get("artifacts", [])),
                },
            }
        )

    for validation in trace["validations"]:
        spans.append(
            {
                "trace_id": otel_trace_id,
                "span_id": _span_id(validation["validation_id"]),
                "parent_span_id": root_span_id,
                "name": f"validate {validation['name']}",
                "kind": "internal",
                "start_time": trace["created_at"],
                "end_time": _workflow_end_time(trace),
                "attributes": {
                    "scitrace.operation.name": "validation_gate",
                    "scitrace.validation.name": validation["name"],
                    "scitrace.status": validation["status"],
                    "scitrace.score": validation["score"],
                },
            }
        )

    return {"trace_id": otel_trace_id, "spans": spans}


def _artifact_id(artifact: dict[str, Any]) -> str:
    return f"#artifact/{artifact['artifact_id']}"


def _tool_call_id(call: dict[str, Any]) -> str:
    return f"#tool-call/{call['call_id']}"


def _validation_id(validation: dict[str, Any]) -> str:
    return f"#validation/{validation['validation_id']}"


def _task_id(trace: dict[str, Any]) -> str:
    return f"#task/{trace['task_id']}"


def _trace_id(trace: dict[str, Any]) -> str:
    return f"#trace/{trace['trace_id']}"


def _properties(values: dict[str, Any]) -> list[dict[str, Any]]:
    return [{"@type": "PropertyValue", "name": key, "value": value} for key, value in sorted(values.items())]


def _workflow_end_time(trace: dict[str, Any]) -> str:
    tool_end_times = [call["ended_at"] for call in trace["tools"] if call.get("ended_at")]
    return max(tool_end_times) if tool_end_times else trace["created_at"]


def _hash_json(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _trace_id_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:32]


def _span_id(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
