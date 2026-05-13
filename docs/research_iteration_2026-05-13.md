# Research Iteration: 2026-05-13

## Question

What was missing from SciTrace-RL after the first demo pass?

## Finding

The project already had a useful local trace schema, validation gates, and trace-to-reward sample. The missing professional layer was interoperability: a serious scientific workflow system should not only write its own JSON log. It should be able to map runs into established provenance and observability formats.

## Sources Checked

- DP Technology / Bohrium + SciMaster: https://arxiv.org/abs/2512.20469
- W3C PROV overview: https://www.w3.org/TR/prov-overview/
- Workflow Run RO-Crate: https://www.researchobject.org/workflow-run-crate/
- Recording provenance of workflow runs with RO-Crate: https://arxiv.org/abs/2312.07852
- OpenTelemetry GenAI agent spans: https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-agent-spans/
- PaperBench: https://arxiv.org/abs/2504.01848
- FIRE-Bench: https://arxiv.org/abs/2602.02905
- SPOT benchmark: https://arxiv.org/abs/2505.11855
- MLR-Bench: https://arxiv.org/abs/2505.19955

## Decision

Add a standards-aware provenance export layer:

- `ro_crate`: packages trace artifacts in a Workflow Run RO-Crate-style graph.
- `prov`: maps task, tool calls, validations, and artifacts to W3C PROV-style entities, activities, and agents.
- `otel`: maps the workflow, tool calls, and validation gates to OpenTelemetry-style spans.

## Why This Improves the Project

This makes SciTrace-RL look less like a toy agent demo and more like infrastructure that could sit between Bohrium/SciMaster execution, scientific workflow provenance, and production agent observability. It also supports the original thesis: the valuable asset is not the final answer alone, but the inspectable and reusable execution record.
