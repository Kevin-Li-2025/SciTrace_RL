# Research Basis

This project direction is grounded in public signals from DP Technology and the broader agentic-science ecosystem.

## DP Technology / Deep Potential

- DP Technology describes itself as an AI for Science company building AI Scientists and autonomous scientific discovery systems.
- Its product matrix covers reading, computing, and experimenting through Bohrium, Lebesgue, Hermite, Piloteye, Uni-Lab, SciMaster, and broader infrastructure services.
- Source: https://www.dp.tech/about

## Bohrium + SciMaster

- `arXiv:2512.20469` frames the central bottleneck as agentic science at scale.
- It emphasizes that scientific workflows must become observable, reproducible, governable, executable, and continuously improvable.
- It explicitly discusses execution traces, stable tool interfaces, validation, agent-ready infrastructure, and feedback loops.
- Source: https://arxiv.org/abs/2512.20469

## SciMaster / X-Master

- `arXiv:2507.05241` introduces X-Master as a tool-augmented reasoning agent and uses inference-time workflow scaling.
- It reinforces the importance of tool use, code execution, web search, and structured multi-agent workflows.
- Source: https://arxiv.org/abs/2507.05241

## Uni-Parser / OmniScience

- OmniScience is a large-scale scientific image-text-context dataset built using Uni-Parser.
- It demonstrates DP Technology's interest in converting scientific documents into structured, reusable evidence for downstream AI systems.
- Source: https://huggingface.co/datasets/UniParser/OmniScience

## Broader Industry Direction

- OpenAI Deep Research focuses on multi-step research with citations and source traceability.
- OpenAI o-series reasoning models can use tools such as web browsing, Python, file analysis, and visual inputs.
- Google AI co-scientist explores multi-agent hypothesis generation, debate, ranking, and evolution for scientific discovery.
- PaperBench reports that the best tested agent reached only a 21.0% average replication score on state-of-the-art AI research replication tasks.
- FIRE-Bench frames full-cycle discovery as constrained rediscovery and reports that even strong agents remain below 50 F1, with recurring failures in experimental design, execution, and evidence-based reasoning.
- SPOT evaluates AI-assisted manuscript verification and reports that no tested model exceeds 21.1% recall or 6.1% precision on significant paper errors.
- Sources:
  - https://help.openai.com/en/articles/10500283-deep-research
  - https://openai.com/index/introducing-o3-and-o4-mini/
  - https://research.google/blog/accelerating-scientific-breakthroughs-with-an-ai-co-scientist
  - https://arxiv.org/abs/2504.01848
  - https://arxiv.org/abs/2602.02905
  - https://arxiv.org/abs/2505.11855

## Provenance and Observability Standards

- W3C PROV defines provenance as information about entities, activities, and people involved in producing a data object or thing, so that quality, reliability, and trustworthiness can be assessed.
- Workflow Run RO-Crate packages the provenance of computational workflow executions and their associated inputs, outputs, code, and metadata.
- OpenTelemetry GenAI semantic conventions are defining span shapes for agent workflows and tool execution, which makes agent traces easier to ingest into production observability systems.
- SciTrace-RL now exports `provenance_bundle.json` with three views of the same run: `ro_crate`, `prov`, and `otel`.
- Sources:
  - https://www.w3.org/TR/prov-overview/
  - https://www.researchobject.org/workflow-run-crate/
  - https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-agent-spans/

## DeepSeek API Validation Layer

- DeepSeek's official API documentation states that its API is OpenAI-compatible.
- The current official docs list `https://api.deepseek.com` as the OpenAI-compatible base URL.
- The current V4 model identifiers include `deepseek-v4-flash` and `deepseek-v4-pro`; legacy `deepseek-chat` and `deepseek-reasoner` are scheduled for deprecation on 2026-07-24.
- Sources:
  - https://api-docs.deepseek.com/
  - https://api-docs.deepseek.com/api/create-chat-completion
  - https://api-docs.deepseek.com/updates

## Directional Conclusion

The durable opportunity is not another narrow scientific chatbot. The durable opportunity is infrastructure that turns agent execution into:

1. traceable evidence,
2. replayable artifacts,
3. validation scores,
4. reward labels,
5. training data for future agents.

That is why SciTrace-RL is positioned as AI4S Infra rather than a single chemistry model, document parser, or vertical assistant.
